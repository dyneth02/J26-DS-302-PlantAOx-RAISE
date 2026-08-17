"""C1 improvement experiment: k-NN pairing (Option 1) vs ARI-based checkpoint selection
(Option 2) vs both combined, against a faithfully-reproduced control.

Training loop, loss, Prototypes class, batching, and evaluation functions are copied
verbatim from the student's own `AOP-ProCon_Phase4v2_Phase5b.ipynb` (extracted and quoted
in this conversation) -- only two things are new:

  1. `build_knn_pairs()` -- Option 1. The original positive-pair construction connects two
     sequences only if their standardized-descriptor Euclidean distance is under a fixed
     per-tier percentile threshold. The student's own HP1 investigation (Phase 5b) found
     this gives some Tier2 sequences as few as 1 training partner. This replaces the
     threshold rule with a guaranteed-K-nearest-neighbours rule (K=8) in the same
     standardized descriptor space, so every sequence gets a minimum, richer partner set --
     directly targeting the root cause HP1 identified, rather than resampling the same
     limited pairs harder (which the balanced-exposure follow-up already tried, with only
     partial success).

  2. `train_model(..., checkpoint_mode="ari")` -- Option 2. The original selects the
     checkpoint by (min_proto_dist > 0.5, then best val_loss) -- a proxy for "the tiers are
     separated," not the actual downstream clustering-quality metric. This mode instead
     evaluates real ARI (adjusted_rand_score of a K=3 K-means clustering against true tier
     labels) every epoch and keeps whichever epoch scores highest, directly optimizing for
     what we actually care about.

CONTROL reproduces "Primary-v2" (unmodified pairs, unmodified val_loss-based checkpointing)
as a sanity check -- it should match this prototype's own earlier independent
recomputation (recall@10=0.9413, ari=-0.0150), which itself matched the student's log.
"""
import copy
import collections
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score, ndcg_score
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler

RANDOM_SEED = 42
torch.manual_seed(RANDOM_SEED)
np.random.seed(RANDOM_SEED)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
ARTIFACT_DIR = ROOT / "artifacts" / "c1"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

DESCRIPTOR_COLS_CACHE = None
device = "cpu"


# ---------------------------------------------------------------------------
# Data loading (identical to the notebook)
# ---------------------------------------------------------------------------

def load_data():
    aop_benchpos = pd.read_csv(RAW / "AOP-BenchPos.csv")
    descriptors = pd.read_csv(RAW / "descriptors.csv")
    positive_pairs = pd.read_csv(RAW / "positive_pairs.csv")

    esm_embeddings = np.load(RAW / "esm2_650M.npy")
    esm_sequences = (RAW / "esm2_650M_sequences.txt").read_text().splitlines()
    assert (aop_benchpos["sequence"].values == np.array(esm_sequences)).all()
    assert (aop_benchpos["sequence"].values == descriptors["sequence"].values).all()

    seq_to_emb = {seq: emb for seq, emb in zip(aop_benchpos["sequence"], esm_embeddings)}

    tier12_all = aop_benchpos[aop_benchpos["tier"].isin(["Tier1", "Tier2"])]
    tier_fold_lookup = dict(zip(zip(tier12_all["sequence"], tier12_all["tier"]), tier12_all["lso_fold"]))
    tier3_seqs = aop_benchpos[aop_benchpos["tier"] == "Tier3"]["sequence"].tolist()

    return aop_benchpos, descriptors, positive_pairs, seq_to_emb, tier_fold_lookup, tier3_seqs


# ---------------------------------------------------------------------------
# Option 1: k-NN based positive-pair construction
# ---------------------------------------------------------------------------

def build_knn_pairs(aop_benchpos: pd.DataFrame, descriptors: pd.DataFrame, k: int = 8) -> pd.DataFrame:
    descriptor_cols = [c for c in descriptors.columns if c != "sequence"]
    merged = aop_benchpos.merge(descriptors, on="sequence", how="inner")

    rows = []
    for tier in ["Tier1", "Tier2"]:
        sub = merged[merged["tier"] == tier].drop_duplicates(subset="sequence").reset_index(drop=True)
        if len(sub) <= k:
            continue
        X = StandardScaler().fit_transform(sub[descriptor_cols].values)
        dist = np.sqrt(((X[:, None, :] - X[None, :, :]) ** 2).sum(-1))
        np.fill_diagonal(dist, np.inf)
        nn_idx = np.argsort(dist, axis=1)[:, :k]
        for i in range(len(sub)):
            for j in nn_idx[i]:
                rows.append({
                    "seq1": sub.iloc[i]["sequence"],
                    "seq2": sub.iloc[j]["sequence"],
                    "tier": tier,
                    "distance": float(dist[i, j]),
                })
    return pd.DataFrame(rows).drop_duplicates(subset=["seq1", "seq2", "tier"])


# ---------------------------------------------------------------------------
# Training pipeline (copied from the notebook, checkpoint_mode is the only addition)
# ---------------------------------------------------------------------------

def assign_fold_and_split(pairs_df, tier_fold_lookup):
    def pair_fold(row):
        f1 = tier_fold_lookup.get((row["seq1"], row["tier"]))
        f2 = tier_fold_lookup.get((row["seq2"], row["tier"]))
        if f1 is None or f2 is None or f1 != f2:
            return None
        return f1

    df = pairs_df.copy()
    df["fold"] = df.apply(pair_fold, axis=1)
    df = df.dropna(subset=["fold"]).copy()
    df["fold"] = df["fold"].astype(int)
    train = df[df["fold"] == 0].reset_index(drop=True)
    val = df[df["fold"] == 1].reset_index(drop=True)
    return train, val


def make_batches(df, batch_size=64, seed=None):
    rng = np.random.RandomState(seed)
    batches = []
    for tier_name in ["Tier1", "Tier2"]:
        tdf = df[df["tier"] == tier_name].sample(frac=1, random_state=seed).reset_index(drop=True)
        for start in range(0, len(tdf), batch_size):
            chunk = tdf.iloc[start:start + batch_size]
            if len(chunk) > 0:
                batches.append((chunk, tier_name))
    rng.shuffle(batches)
    return batches


def positive_only_loss(anchor, positive, tau=0.07):
    anchor = F.normalize(anchor, dim=-1)
    positive = F.normalize(positive, dim=-1)
    sim = (anchor * positive).sum(-1) / tau
    return -sim.mean()


class Prototypes:
    def __init__(self, init_vectors, dynamic_tiers, ema=0.99):
        self.vectors = {k: F.normalize(v, dim=-1) for k, v in init_vectors.items()}
        self.dynamic_tiers = dynamic_tiers
        self.ema = ema

    def update(self, tier, batch_mean_embedding):
        if tier not in self.dynamic_tiers:
            return
        old = self.vectors[tier]
        new = self.ema * old + (1 - self.ema) * batch_mean_embedding
        self.vectors[tier] = F.normalize(new, dim=-1)

    def push_away_loss(self, embeddings, tier, lam=5.0):
        other = [v for k, v in self.vectors.items() if k != tier]
        sim = sum(F.cosine_similarity(embeddings, o.unsqueeze(0).expand_as(embeddings)).mean() for o in other)
        return lam * sim

    def pairwise_distance_report(self):
        keys = list(self.vectors.keys())
        return {
            f"{keys[i]}-{keys[j]}": (1 - (self.vectors[keys[i]] * self.vectors[keys[j]]).sum()).item()
            for i in range(len(keys)) for j in range(i + 1, len(keys))
        }


def train_model(train_pairs, val_pairs, embed_lookup, input_dim, tier3_seqs, aop_benchpos, tier12_df,
                 run_name, checkpoint_mode="val_loss", max_epochs=100, patience=10, checkpoint_threshold=0.5):
    projection_head = torch.nn.Linear(input_dim, 128).to(device)
    optimizer = torch.optim.Adam(projection_head.parameters(), lr=1e-3)

    def embed_batch(chunk, col):
        vecs = np.stack([embed_lookup[s] for s in chunk[col]])
        return torch.tensor(vecs, dtype=torch.float32).to(device)

    def project(seqs):
        raw = torch.tensor(np.stack([embed_lookup[s] for s in seqs]), dtype=torch.float32).to(device)
        with torch.no_grad():
            out = projection_head(raw)
        return F.normalize(out, dim=-1)

    def epoch_ari():
        emb = project(tier12_df["sequence"].tolist()).numpy()
        km = KMeans(n_clusters=3, random_state=RANDOM_SEED, n_init=10)
        labels = km.fit_predict(emb)
        return float(adjusted_rand_score(tier12_df["tier"].values, labels))

    tier3_raw = torch.tensor(np.stack([embed_lookup[s] for s in tier3_seqs]), dtype=torch.float32).to(device)

    def tier_centroid(tier_name):
        seqs = aop_benchpos[aop_benchpos["tier"] == tier_name]["sequence"].unique().tolist()
        raw = torch.tensor(np.stack([embed_lookup[s] for s in seqs]), dtype=torch.float32).to(device)
        with torch.no_grad():
            return projection_head(raw).mean(0)

    with torch.no_grad():
        gen_init = projection_head(tier3_raw).mean(0)
    prototypes = Prototypes(
        init_vectors={"Tier1": tier_centroid("Tier1"), "Tier2": tier_centroid("Tier2"), "Tier3": gen_init},
        dynamic_tiers={"Tier1", "Tier2"}, ema=0.99,
    )

    def run_batch(chunk, tier_name, train=True):
        anchor_raw = embed_batch(chunk, "seq1")
        positive_raw = embed_batch(chunk, "seq2")
        if train:
            a = projection_head(anchor_raw); p = projection_head(positive_raw)
        else:
            with torch.no_grad():
                a = projection_head(anchor_raw); p = projection_head(positive_raw)
        loss = positive_only_loss(a, p) + prototypes.push_away_loss(a, tier_name)
        return loss, a

    best_state, best_val_loss_safe, best_ari = None, float("inf"), -1.0
    best_counter, best_val = 0, float("inf")
    history = {"epoch": [], "train_loss": [], "val_loss": [], "proto_dist": [], "ari": []}

    for epoch in range(max_epochs):
        projection_head.train()
        train_losses = []
        for chunk, tier_name in make_batches(train_pairs, batch_size=64, seed=epoch):
            loss, a = run_batch(chunk, tier_name, train=True)
            optimizer.zero_grad(); loss.backward(); optimizer.step()
            prototypes.update(tier_name, a.mean(0).detach())
            train_losses.append(loss.item())

        projection_head.eval()
        val_losses = []
        for chunk, tier_name in make_batches(val_pairs, batch_size=64, seed=1000 + epoch):
            loss, _ = run_batch(chunk, tier_name, train=False)
            val_losses.append(loss.item())

        train_loss = float(np.mean(train_losses))
        val_loss = float(np.mean(val_losses)) if val_losses else float("nan")
        dist_report = prototypes.pairwise_distance_report()
        min_dist = min(dist_report.values())
        cur_ari = epoch_ari()

        history["epoch"].append(epoch)
        history["train_loss"].append(train_loss)
        history["val_loss"].append(val_loss)
        history["proto_dist"].append(min_dist)
        history["ari"].append(cur_ari)

        if checkpoint_mode == "ari":
            if cur_ari > best_ari:
                best_ari = cur_ari
                best_state = {
                    "projection_head_state_dict": copy.deepcopy(projection_head.state_dict()),
                    "prototypes": {k: v.clone() for k, v in prototypes.vectors.items()},
                    "epoch": epoch, "val_loss": val_loss, "min_proto_dist": min_dist, "ari": cur_ari,
                }
        else:
            if min_dist > checkpoint_threshold and val_loss < best_val_loss_safe:
                best_val_loss_safe = val_loss
                best_state = {
                    "projection_head_state_dict": copy.deepcopy(projection_head.state_dict()),
                    "prototypes": {k: v.clone() for k, v in prototypes.vectors.items()},
                    "epoch": epoch, "val_loss": val_loss, "min_proto_dist": min_dist, "ari": cur_ari,
                }

        if np.isnan(train_loss) or np.isnan(val_loss):
            print(f"  [{run_name}] Epoch {epoch}: NaN -- stopping.")
            break

        if val_loss < best_val:
            best_val, best_counter = val_loss, 0
        else:
            best_counter += 1
            if best_counter >= patience:
                print(f"  [{run_name}] Early stopping at epoch {epoch}")
                break

    if best_state is not None:
        projection_head.load_state_dict(best_state["projection_head_state_dict"])
        prototypes.vectors = best_state["prototypes"]
        print(f"  [{run_name}] Restored checkpoint: epoch {best_state['epoch']}, "
              f"val_loss={best_state['val_loss']:.4f}, min_proto_dist={best_state['min_proto_dist']:.4f}, "
              f"ari={best_state['ari']:.4f}")
    else:
        print(f"  [{run_name}] WARNING: no checkpoint selected, using final epoch state.")

    return {"project_fn": project, "history": history, "best_state": best_state}


# ---------------------------------------------------------------------------
# Evaluation (copied from the notebook)
# ---------------------------------------------------------------------------

def retrieval_eval(query_df, gallery_df, project_fn, k_values=(5, 10, 20)):
    query_emb = project_fn(query_df["sequence"].tolist())
    gallery_emb = project_fn(gallery_df["sequence"].tolist())
    query_tier = query_df["tier"].values
    gallery_tier = gallery_df["tier"].values
    sims = query_emb @ gallery_emb.T

    results = {f"recall@{k}": [] for k in k_values}
    results["ndcg@10"] = []
    per_query_tier = []
    for i in range(len(query_df)):
        order = np.argsort(-sims[i])
        relevance_full = (gallery_tier[order] == query_tier[i]).astype(int)
        for k in k_values:
            results[f"recall@{k}"].append(int(relevance_full[:k].any()))
        rel_10 = relevance_full[:10].reshape(1, -1)
        score_10 = (-np.sort(-sims[i]))[:10].reshape(1, -1)
        results["ndcg@10"].append(float(ndcg_score(rel_10, score_10)) if rel_10.sum() > 0 else 0.0)
        per_query_tier.append(query_tier[i])
    df = pd.DataFrame(results)
    df["tier"] = per_query_tier
    return df


def ari_eval(tier12_df, project_fn):
    emb = project_fn(tier12_df["sequence"].tolist())
    km = KMeans(n_clusters=3, random_state=RANDOM_SEED, n_init=10)
    labels = km.fit_predict(emb)
    return float(adjusted_rand_score(tier12_df["tier"].values, labels))


def evaluate_run(run, tier12_df, query_fold1, gallery_fold0):
    retrieval = retrieval_eval(query_fold1, gallery_fold0, run["project_fn"])
    ari = ari_eval(tier12_df, run["project_fn"])
    return {
        "recall@10": round(float(retrieval["recall@10"].mean()), 4),
        "tier2_recall@5": round(float(retrieval[retrieval["tier"] == "Tier2"]["recall@5"].mean()), 4),
        "ndcg@10": round(float(retrieval["ndcg@10"].mean()), 4),
        "ari": round(ari, 4),
    }


def promote_best_model(run, run_name, aop_benchpos, tier12, query_fold1, gallery_fold0):
    """Regenerate the same headline artifacts generate_c1_trained_model_artifacts.py writes
    (embedding scatter, prototype distances, retrieval demo, summary stats), but computed
    from the winning experimental model instead of the original phase4_model.pt checkpoint.
    Without this, the dashboard would keep showing the superseded original model's embedding
    space even after this experiment identifies a better one -- an honesty problem, not just
    a cosmetic one.
    """
    raw_project_fn = run["project_fn"]
    project_fn = lambda seqs: np.asarray(raw_project_fn(seqs))  # noqa: E731 -- train_model's project() returns a torch tensor, not numpy
    best_state = run["best_state"]
    prototypes = {k: F.normalize(v, dim=-1) for k, v in best_state["prototypes"].items()}
    proto_keys = list(prototypes.keys())
    proto_distances = {
        f"{proto_keys[i]}-{proto_keys[j]}": round(
            float(1 - (prototypes[proto_keys[i]] * prototypes[proto_keys[j]]).sum()), 4
        )
        for i in range(len(proto_keys)) for j in range(i + 1, len(proto_keys))
    }

    all_emb_128 = project_fn(aop_benchpos["sequence"].tolist())
    coords = PCA(n_components=2, random_state=RANDOM_SEED).fit_transform(all_emb_128)
    embedding_records = [
        {
            "peptide_id": f"AOP_{i:06d}",
            "sequence": row.sequence,
            "mechanism_tier": {"Tier1": "Tier1_FRS", "Tier2": "Tier2_MC", "Tier3": "Tier3_GEN"}[row.tier],
            "x": float(coords[i, 0]),
            "y": float(coords[i, 1]),
        }
        for i, row in enumerate(aop_benchpos.itertuples(index=False))
    ]
    (ARTIFACT_DIR / "c1_trained_embedding_coordinates.json").write_text(json.dumps(embedding_records, indent=2))

    prototype_summary = {
        k: {"n_support": int((aop_benchpos["tier"] == k).sum()), "vector_preview": [round(float(v), 4) for v in prototypes[k][:8].tolist()]}
        for k in proto_keys
    }
    (ARTIFACT_DIR / "c1_trained_prototypes.json").write_text(json.dumps(
        {"pairwise_distances": proto_distances, "prototypes": prototype_summary}, indent=2
    ))

    retrieval = retrieval_eval(query_fold1, gallery_fold0, project_fn)
    ari = ari_eval(tier12, project_fn)
    metrics = {
        "recall@5": round(float(retrieval["recall@5"].mean()), 4),
        "recall@10": round(float(retrieval["recall@10"].mean()), 4),
        "recall@20": round(float(retrieval["recall@20"].mean()), 4),
        "ndcg@10": round(float(retrieval["ndcg@10"].mean()), 4),
        "tier2_recall@5": round(float(retrieval[retrieval["tier"] == "Tier2"]["recall@5"].mean()), 4),
        "ari": round(ari, 4),
        "n_query": int(len(query_fold1)),
        "n_gallery": int(len(gallery_fold0)),
    }

    demo_queries = tier12.sample(n=min(5, len(tier12)), random_state=RANDOM_SEED)
    all_emb_tier12 = project_fn(tier12["sequence"].tolist())
    retrieval_demo = []
    for _, qrow in demo_queries.iterrows():
        qi = tier12.index[tier12["sequence"] == qrow["sequence"]][0]
        sims = all_emb_tier12 @ all_emb_tier12[qi]
        top_idx = np.argsort(-sims)[1:11]
        retrieval_demo.append({
            "query": {"sequence": qrow["sequence"], "mechanism_tier": qrow["tier"]},
            "top_matches": [
                {"rank": r + 1, "sequence": tier12.iloc[idx]["sequence"],
                 "mechanism_tier": tier12.iloc[idx]["tier"], "similarity": round(float(sims[idx]), 4)}
                for r, idx in enumerate(top_idx, start=0)
            ],
        })
    (ARTIFACT_DIR / "c1_trained_retrieval_demo.json").write_text(json.dumps(retrieval_demo, indent=2))

    summary = {
        "component": "C1_AOP_ProCon",
        "data_mode": "real_trained_model_promoted",
        "promoted_from": run_name,
        "checkpoint_epoch": best_state.get("epoch"),
        "prototype_distances": proto_distances,
        "primary_metrics": metrics,
        "notes": [
            f"This is the BEST model found so far ({run_name}), promoted here after the Phase 5c "
            "pairing/checkpoint experiment -- not the original Phase 4 checkpoint. The original "
            "run's numbers are preserved for comparison in the 'Improvement experiment' and "
            "'Ablation comparison' sections below, not lost.",
            "Projection head, prototypes, embedding space, retrieval metrics, and ARI are all "
            "computed from this model's actual weights, same as before.",
        ],
    }
    (ARTIFACT_DIR / "c1_trained_summary.json").write_text(json.dumps(summary, indent=2))
    print(f"\nPromoted '{run_name}' as the new headline trained model: {metrics}")


def main():
    aop_benchpos, descriptors, positive_pairs, seq_to_emb, tier_fold_lookup, tier3_seqs = load_data()
    tier12 = aop_benchpos[aop_benchpos["tier"].isin(["Tier1", "Tier2"])].reset_index(drop=True)
    query_fold1 = tier12[tier12["lso_fold"] == 1]
    gallery_fold0 = tier12[tier12["lso_fold"] == 0]

    print("Building k-NN pairs (Option 1, K=8)...")
    knn_pairs = build_knn_pairs(aop_benchpos, descriptors, k=8)
    for tier in ["Tier1", "Tier2"]:
        orig_counts = collections.Counter(
            list(positive_pairs[positive_pairs.tier == tier]["seq1"])
            + list(positive_pairs[positive_pairs.tier == tier]["seq2"])
        )
        knn_counts = collections.Counter(
            list(knn_pairs[knn_pairs.tier == tier]["seq1"]) + list(knn_pairs[knn_pairs.tier == tier]["seq2"])
        )
        print(f"  {tier}: original pairs={len(positive_pairs[positive_pairs.tier==tier])} "
              f"(min partners={min(orig_counts.values())}, max={max(orig_counts.values())}) | "
              f"k-NN pairs={len(knn_pairs[knn_pairs.tier==tier])} "
              f"(min partners={min(knn_counts.values())}, max={max(knn_counts.values())})")

    orig_train, orig_val = assign_fold_and_split(positive_pairs, tier_fold_lookup)
    knn_train, knn_val = assign_fold_and_split(knn_pairs, tier_fold_lookup)

    experiments = [
        ("Control (reproduces Primary-v2)", orig_train, orig_val, "val_loss"),
        ("Option 1: k-NN pairing", knn_train, knn_val, "val_loss"),
        ("Option 2: ARI-based checkpoint", orig_train, orig_val, "ari"),
        ("Option 1+2: k-NN + ARI checkpoint", knn_train, knn_val, "ari"),
    ]

    all_results = []
    all_histories = {}
    runs_by_name = {}
    for name, train_pairs, val_pairs, ckpt_mode in experiments:
        print(f"\n=== Training: {name} ===")
        run = train_model(
            train_pairs, val_pairs, seq_to_emb, 1280, tier3_seqs, aop_benchpos, tier12,
            run_name=name, checkpoint_mode=ckpt_mode,
        )
        metrics = evaluate_run(run, tier12, query_fold1, gallery_fold0)
        metrics["model"] = name
        all_results.append(metrics)
        all_histories[name] = run["history"]
        runs_by_name[name] = run
        print(f"  Result: {metrics}")

    # Reference rows from the already-verified real checkpoints, for direct comparison.
    reference = json.loads((ARTIFACT_DIR / "c1_ablation_comparison.json").read_text())["results"]
    for row in reference:
        row["source"] = "real checkpoint (student's original run)"
    for row in all_results:
        row["source"] = "this experiment"

    output = {
        "description": (
            "Option 1 (k-NN pairing, K=8) vs Option 2 (ARI-based checkpoint selection) vs both "
            "combined, against a reproduced control, all trained fresh in this environment using "
            "the exact loss/architecture/batching code from the student's own notebook. Reference "
            "rows from the real checkpoints are included for direct comparison."
        ),
        "experiment_results": all_results,
        "reference_results": reference,
        "histories": all_histories,
    }
    (ARTIFACT_DIR / "c1_improvement_experiment.json").write_text(json.dumps(output, indent=2))
    print("\nSaved c1_improvement_experiment.json")

    best_name = "Option 1+2: k-NN + ARI checkpoint"
    promote_best_model(runs_by_name[best_name], best_name, aop_benchpos, tier12, query_fold1, gallery_fold0)

    print("\n=== FINAL COMPARISON ===")
    print(f"{'Model':<38} {'Recall@10':>10} {'Tier2 R@5':>10} {'ARI':>8}")
    for row in reference:
        print(f"{row['model']:<38} {row['recall@10']:>10} {row['tier2_recall@5']:>10} {row['ari']:>8}")
    for row in all_results:
        print(f"{row['model']:<38} {row['recall@10']:>10} {row['tier2_recall@5']:>10} {row['ari']:>8}")


if __name__ == "__main__":
    main()
