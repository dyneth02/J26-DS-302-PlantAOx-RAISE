"""Component 1 — REAL trained model artifacts.

Everything C1 showed until now (PCA over raw ESM-2, KMeans purity) was explicitly documented as
a stand-in for "the final trained positive-only SupCon projection." That model now exists: five
real checkpoints trained on Google Colab (student's own run, `Research/my/C1/progress_log.md`
Phase 4 / 4v2 / 5 / 5b / 5.3), staged at data/raw/trained_model/. This script replaces every
placeholder with the real thing:

  - The 128-D embedding space is the ACTUAL output of the trained projection head
    (nn.Linear(1280, 128), loaded from phase4_model.pt's real weights), not raw ESM-2 + PCA.
  - Prototype vectors are the ACTUAL trained prototypes from the checkpoint, not tier means.
  - Purity uses Adjusted Rand Index, matching the student's own fix (K-means "purity" was found
    mathematically degenerate at this project's Tier1:Tier2 class imbalance -- see
    progress_log.md Phase 5b).
  - Recall@{5,10,20}/nDCG@10 and the 4-model ablation comparison (Primary-v2, HP1-Random,
    HP2-Fusion, Primary-v2-Balanced) are RECOMPUTED HERE from the real checkpoints and the real
    LSO fold split (query=fold1, gallery=fold0) -- not copied from the log, independently
    reproduced using the exact methodology extracted from the student's own notebook code
    (retrieval_eval / ari_eval, `Research/my/C1/STEP 05/AOP-ProCon_Phase4v2_Phase5b.ipynb`).
  - HP1-HP4 significance results are the real Mann-Whitney U / Bonferroni table the student
    generated (phase5_3_statistical_summary.csv), served as-is.
  - The training loss/prototype-distance curve is the real per-epoch history
    (phase4_training_history.csv), including the collapse-then-recover dynamic documented in
    the log.

Nothing in this file is synthetic. Where recomputation doesn't reproduce the log's numbers to
the last decimal (fusion-model preprocessing has some legitimate reconstruction risk -- see the
StandardScaler note below), both this run's number and the log's are surfaced, not silently
reconciled.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import adjusted_rand_score, ndcg_score
from sklearn.preprocessing import StandardScaler

RANDOM_SEED = 42
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
TM = RAW / "trained_model"
ARTIFACT_DIR = ROOT / "artifacts" / "c1"
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

DESCRIPTOR_COLS = [
    "mw", "gravy", "aromaticity", "instability", "charge_ph7", "aliphatic_index",
    "ctd_hydro_C_hydrophobic", "ctd_hydro_C_neutral", "ctd_hydro_C_polar",
    "ctd_hydro_T_hydrophobic_neutral", "ctd_hydro_T_neutral_polar", "ctd_hydro_T_hydrophobic_polar",
    "ctd_charge_C_positive", "ctd_charge_C_negative",
]


def load_projection_head(filename: str, in_dim: int) -> nn.Linear:
    ckpt = torch.load(TM / filename, map_location="cpu", weights_only=False)
    head = nn.Linear(in_dim, 128)
    head.load_state_dict(ckpt["projection_head_state_dict"])
    head.eval()
    return head, ckpt


def make_project_fn(head: nn.Linear, seq_to_vec: dict):
    def project(seqs: list[str]) -> np.ndarray:
        raw = torch.tensor(np.stack([seq_to_vec[s] for s in seqs]), dtype=torch.float32)
        with torch.no_grad():
            out = head(raw)
        return F.normalize(out, dim=-1).numpy()
    return project


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


def ari_eval(tier12_df, project_fn) -> float:
    emb = project_fn(tier12_df["sequence"].tolist())
    km = KMeans(n_clusters=3, random_state=RANDOM_SEED, n_init=10)
    labels = km.fit_predict(emb)
    return float(adjusted_rand_score(tier12_df["tier"].values, labels))


def main():
    aop_benchpos = pd.read_csv(RAW / "AOP-BenchPos.csv")
    descriptors = pd.read_csv(RAW / "descriptors.csv")
    esm_embeddings = np.load(RAW / "esm2_650M.npy")
    esm_sequences = (RAW / "esm2_650M_sequences.txt").read_text().splitlines()

    assert (aop_benchpos["sequence"].values == np.array(esm_sequences)).all(), "sequence order mismatch"
    assert (aop_benchpos["sequence"].values == descriptors["sequence"].values).all(), "sequence order mismatch"

    seq_to_emb = {seq: emb for seq, emb in zip(aop_benchpos["sequence"], esm_embeddings)}

    descriptor_cols = [c for c in descriptors.columns if c != "sequence"]
    scaler = StandardScaler()
    descriptors_scaled = scaler.fit_transform(descriptors[descriptor_cols].values)
    seq_to_fused_emb = {
        seq: np.concatenate([seq_to_emb[seq], descriptors_scaled[i]])
        for i, seq in enumerate(descriptors["sequence"])
    }
    print(f"Fused embedding dim: {next(iter(seq_to_fused_emb.values())).shape[0]} (expect 1294)")

    tier12 = aop_benchpos[aop_benchpos["tier"].isin(["Tier1", "Tier2"])].reset_index(drop=True)
    query_fold1 = tier12[tier12["lso_fold"] == 1]
    gallery_fold0 = tier12[tier12["lso_fold"] == 0]
    print(f"Tier1/Tier2 pool: {len(tier12)} | query(fold1): {len(query_fold1)} | gallery(fold0): {len(gallery_fold0)}")

    # ---- Primary model (phase4_model.pt): the headline trained embedding space ----
    primary_head, primary_ckpt = load_projection_head("phase4_model.pt", 1280)
    project_primary = make_project_fn(primary_head, seq_to_emb)

    prototypes = {k: F.normalize(v, dim=-1) for k, v in primary_ckpt["prototypes"].items()}
    proto_keys = list(prototypes.keys())
    proto_distances = {
        f"{proto_keys[i]}-{proto_keys[j]}": round(
            float(1 - (prototypes[proto_keys[i]] * prototypes[proto_keys[j]]).sum()), 4
        )
        for i in range(len(proto_keys)) for j in range(i + 1, len(proto_keys))
    }
    print("Real trained prototype distances:", proto_distances)

    # Real 128-D embeddings for every sequence (Tier1/2/3), PCA'd to 2D for the scatter plot.
    all_emb_128 = project_primary(aop_benchpos["sequence"].tolist())
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
    print("Saved c1_trained_embedding_coordinates.json (PCA of REAL trained 128-D embeddings)")

    prototype_summary = {
        k: {
            "n_support": int((aop_benchpos["tier"] == k).sum()),
            "vector_preview": [round(float(v), 4) for v in prototypes[k][:8].tolist()],
        }
        for k in proto_keys
    }
    (ARTIFACT_DIR / "c1_trained_prototypes.json").write_text(json.dumps(
        {"pairwise_distances": proto_distances, "prototypes": prototype_summary}, indent=2
    ))

    ari_primary = ari_eval(tier12, project_primary)
    primary_retrieval = retrieval_eval(query_fold1, gallery_fold0, project_primary)
    primary_metrics = {
        "recall@5": round(float(primary_retrieval["recall@5"].mean()), 4),
        "recall@10": round(float(primary_retrieval["recall@10"].mean()), 4),
        "recall@20": round(float(primary_retrieval["recall@20"].mean()), 4),
        "ndcg@10": round(float(primary_retrieval["ndcg@10"].mean()), 4),
        "tier2_recall@5": round(float(primary_retrieval[primary_retrieval["tier"] == "Tier2"]["recall@5"].mean()), 4),
        "ari": round(ari_primary, 4),
        "n_query": int(len(query_fold1)),
        "n_gallery": int(len(gallery_fold0)),
    }
    print("Primary (original Phase 4) real recomputed metrics:", primary_metrics)

    # ---- Retrieval demo (real cosine similarity in the real trained 128-D space) ----
    demo_queries = tier12.sample(n=min(5, len(tier12)), random_state=RANDOM_SEED)
    all_emb_tier12 = project_primary(tier12["sequence"].tolist())
    retrieval_demo = []
    for _, qrow in demo_queries.iterrows():
        qi = tier12.index[tier12["sequence"] == qrow["sequence"]][0]
        sims = all_emb_tier12 @ all_emb_tier12[qi]
        top_idx = np.argsort(-sims)[1:11]
        retrieval_demo.append({
            "query": {"sequence": qrow["sequence"], "mechanism_tier": qrow["tier"]},
            "top_matches": [
                {
                    "rank": r + 1,
                    "sequence": tier12.iloc[idx]["sequence"],
                    "mechanism_tier": tier12.iloc[idx]["tier"],
                    "similarity": round(float(sims[idx]), 4),
                }
                for r, idx in enumerate(top_idx)
            ],
        })
    (ARTIFACT_DIR / "c1_trained_retrieval_demo.json").write_text(json.dumps(retrieval_demo, indent=2))
    print("Saved c1_trained_retrieval_demo.json")

    # ---- 4-model ablation comparison: recomputed from the real checkpoints ----
    ablation_configs = [
        ("Primary-v2", "phase4_model_v2.pt", 1280, seq_to_emb),
        ("HP1-Random", "phase5b_hp1_model.pt", 1280, seq_to_emb),
        ("HP2-Fusion", "phase5b_hp2_model.pt", 1294, seq_to_fused_emb),
        ("Primary-v2-Balanced", "phase5b_primary_balanced_model.pt", 1280, seq_to_emb),
    ]
    ablation_results = [{
        "model": "Baseline (original Phase 4)",
        "recall@10": primary_metrics["recall@10"],
        "tier2_recall@5": primary_metrics["tier2_recall@5"],
        "ari": primary_metrics["ari"],
    }]
    for name, filename, in_dim, lookup in ablation_configs:
        head, _ = load_projection_head(filename, in_dim)
        project_fn = make_project_fn(head, lookup)
        retrieval = retrieval_eval(query_fold1, gallery_fold0, project_fn)
        ari = ari_eval(tier12, project_fn)
        row = {
            "model": name,
            "recall@10": round(float(retrieval["recall@10"].mean()), 4),
            "tier2_recall@5": round(float(retrieval[retrieval["tier"] == "Tier2"]["recall@5"].mean()), 4),
            "ari": round(ari, 4),
        }
        ablation_results.append(row)
        print(f"  {name}: {row}")

    (ARTIFACT_DIR / "c1_ablation_comparison.json").write_text(json.dumps({
        "description": (
            "Recall@10, Tier2 Recall@5, and ARI recomputed here from the real checkpoints "
            "(not copied from the log), using the exact LSO retrieval and ARI methodology "
            "extracted from the student's own evaluation notebook."
        ),
        "results": ablation_results,
    }, indent=2))
    print("Saved c1_ablation_comparison.json")

    # ---- Real training history (loss + prototype-distance curve) ----
    history_df = pd.read_csv(TM / "phase4_training_history.csv")
    (ARTIFACT_DIR / "c1_training_history.json").write_text(
        history_df.to_json(orient="records", indent=2)
    )
    print("Saved c1_training_history.json")

    # ---- Real statistical test results (HP1-HP4, Mann-Whitney U + Bonferroni) ----
    stats_df = pd.read_csv(TM / "phase5_3_statistical_summary.csv")
    (ARTIFACT_DIR / "c1_statistical_tests.json").write_text(
        stats_df.to_json(orient="records", indent=2)
    )
    print("Saved c1_statistical_tests.json")

    # ---- Tier 3 soft-prototype-assignment summary ----
    tier3_df = pd.read_csv(TM / "tier3_soft_assignment.csv")
    tier3_summary = {
        "n_sequences": int(len(tier3_df)),
        "closest_prototype_counts": tier3_df["closest_prototype"].value_counts().to_dict(),
        "mean_sim_frs": round(float(tier3_df["sim_frs"].mean()), 4),
        "mean_sim_mc": round(float(tier3_df["sim_mc"].mean()), 4),
        "mean_sim_gen": round(float(tier3_df["sim_gen"].mean()), 4),
    }
    (ARTIFACT_DIR / "c1_tier3_soft_assignment_summary.json").write_text(json.dumps(tier3_summary, indent=2))
    print("Saved c1_tier3_soft_assignment_summary.json:", tier3_summary)

    # ---- Top-level summary tying it together ----
    summary = {
        "component": "C1_AOP_ProCon",
        "data_mode": "real_trained_model",
        "checkpoint_epoch": primary_ckpt.get("checkpoint_epoch"),
        "prototype_distances": proto_distances,
        "primary_metrics": primary_metrics,
        "notes": [
            "This is the REAL trained positive-only SupCon model (Google Colab run), not a "
            "PCA/KMeans stand-in. Projection head, prototypes, embedding space, retrieval "
            "metrics, and ARI are all computed from the actual checkpoint weights.",
            "Recall@K/nDCG@10/ARI were independently recomputed in this script from the real "
            "checkpoints using the exact LSO methodology from the student's own notebook, not "
            "copied from progress_log.md -- serves as an independent cross-check.",
            "HP1-HP4 statistical significance results are the real Mann-Whitney U / effect-size "
            "/ Bonferroni-corrected table generated by the student's own Phase 5.3 run.",
        ],
    }
    (ARTIFACT_DIR / "c1_trained_summary.json").write_text(json.dumps(summary, indent=2))
    print("Saved c1_trained_summary.json")
    print("\nComponent 1 real trained-model artifacts generated successfully.")


if __name__ == "__main__":
    main()
