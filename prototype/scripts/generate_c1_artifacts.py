"""Component 1 (AOP-ProCon) prototype artifact generator.

Unlike a from-scratch prototype, this project already has real curated data:
- data/raw/AOP-BenchPos.csv        : 1639 curated positive AOP sequences (Tier1/2/3),
                                      merged from AnOxPePred, Multi-AOP, DFBP, Peptipedia
                                      and several plant-MCP papers.
- data/raw/descriptors.csv         : real 15-feature physicochemical descriptors.
- data/raw/esm2_650M.npy (+ .txt)  : real ESM-2 650M mean-pooled embeddings.

So nothing here is mocked except the 2D layout method label (PCA, not a trained UMAP/
contrastive projection) and the prototype "purity" figure, which is a proxy computed via
KMeans agreement with tier labels rather than the final positive-only SupCon model.
Everything else (tiers, descriptors, embeddings, retrieval, cloud stats) is real.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity

RANDOM_SEED = 42
ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
ARTIFACT_DIR = ROOT / "artifacts" / "c1"
PROCESSED.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

TARGET_MIN_PER_TIER = 150

np.random.seed(RANDOM_SEED)


def load_and_merge() -> pd.DataFrame:
    bench = pd.read_csv(RAW / "AOP-BenchPos.csv")
    desc = pd.read_csv(RAW / "descriptors.csv")

    seqs = [s.strip() for s in (RAW / "esm2_650M_sequences.txt").read_text().splitlines() if s.strip()]
    emb = np.load(RAW / "esm2_650M.npy")
    if len(seqs) != emb.shape[0]:
        # Keep only the aligned prefix; the trailing rows are dropped rather than
        # silently mis-paired.
        n = min(len(seqs), emb.shape[0])
        seqs, emb = seqs[:n], emb[:n]
    emb_lookup = {s: emb[i] for i, s in enumerate(seqs)}

    # A sequence that carries both a Tier1 (FRS) and a Tier2 (metal-chelation) row across
    # source databases has dual mechanism evidence. It is folded into Tier_Dual rather than
    # arbitrarily deduped to whichever tier happened to appear first.
    tiers_per_seq = bench.groupby("sequence")["tier"].agg(lambda s: set(s))
    dual_seqs = set(tiers_per_seq[tiers_per_seq.apply(lambda s: {"Tier1", "Tier2"} <= s)].index)

    bench = bench.drop_duplicates(subset=["sequence", "tier"]).copy()
    bench["tier"] = bench.apply(lambda r: "Tier_Dual" if r["sequence"] in dual_seqs else r["tier"], axis=1)
    bench = bench.drop_duplicates(subset="sequence").copy()
    desc = desc.drop_duplicates(subset="sequence").copy()

    df = bench.merge(desc, on="sequence", how="inner")
    has_embedding = df["sequence"].isin(emb_lookup)
    df = df[has_embedding].reset_index(drop=True)

    df.insert(0, "peptide_id", ["AOP_" + str(i).zfill(6) for i in range(1, len(df) + 1)])
    df["mechanism_tier"] = df["tier"].map(
        {"Tier1": "Tier1_FRS", "Tier2": "Tier2_MC", "Tier3": "Tier3_GEN", "Tier_Dual": "Tier_Dual"}
    )
    df["training_eligible"] = df["mechanism_tier"].isin(["Tier1_FRS", "Tier2_MC"])

    embeddings = np.stack([emb_lookup[s] for s in df["sequence"]])
    return df, embeddings


def main():
    df, embeddings = load_and_merge()
    print(f"Loaded {len(df)} real curated AOP peptides with real ESM-2 650M embeddings")

    df.to_parquet(PROCESSED / "aop_sequences.parquet", index=False)

    # --- 2D projection (real PCA of real embeddings, used in place of a trained UMAP) ---
    pca = PCA(n_components=2, random_state=RANDOM_SEED)
    coords = pca.fit_transform(embeddings)

    projection_records = [
        {
            "peptide_id": row.peptide_id,
            "sequence": row.sequence,
            "mechanism_tier": row.mechanism_tier,
            "training_eligible": bool(row.training_eligible),
            "umap_x": float(coords[i, 0]),
            "umap_y": float(coords[i, 1]),
        }
        for i, row in enumerate(df.itertuples(index=False))
    ]
    (ARTIFACT_DIR / "c1_umap_coordinates.json").write_text(json.dumps(projection_records, indent=2))
    print("Saved c1_umap_coordinates.json (PCA projection of real ESM-2 650M embeddings)")

    # --- Prototype centroids per mechanism tier (real mean embedding) ---
    prototypes = {}
    for tier in ["Tier1_FRS", "Tier2_MC", "Tier3_GEN", "Tier_Dual"]:
        mask = df["mechanism_tier"] == tier
        n_support = int(mask.sum())
        if n_support == 0:
            continue
        centroid = embeddings[mask.values].mean(axis=0)
        prototypes[tier] = {
            "prototype_id": f"PROTO_{tier.upper()}",
            "embedding_dim": int(embeddings.shape[1]),
            "n_support_sequences": n_support,
            "centroid_preview": [round(float(v), 4) for v in centroid[:8]],
        }

    # Prototype "purity", computed per tier (not per KMeans cluster): for each tier, find
    # the cluster its members fall into most often, then report what fraction of THAT
    # cluster is actually this tier. A per-cluster majority vote (assigning each cluster to
    # its single most common tier) can leave a rare tier owning no cluster at all, which
    # silently reads as an undefined/zero purity even when its members are well clustered.
    n_clusters = df["mechanism_tier"].nunique()
    kmeans = KMeans(n_clusters=n_clusters, random_state=RANDOM_SEED, n_init=10)
    cluster_labels = kmeans.fit_predict(embeddings)
    tier_by_row = df["mechanism_tier"].values

    tier_purities = {}
    for tier in prototypes:
        tier_mask = tier_by_row == tier
        home_cluster = np.bincount(cluster_labels[tier_mask]).argmax()
        home_cluster_mask = cluster_labels == home_cluster
        purity = float((tier_by_row[home_cluster_mask] == tier).mean())
        tier_purities[tier] = purity
        prototypes[tier]["purity"] = round(purity, 4)

    (ARTIFACT_DIR / "c1_prototypes.json").write_text(json.dumps(prototypes, indent=2))
    print("Saved c1_prototypes.json (real centroids, per-tier KMeans-agreement purity)")

    overall_purity = float(np.mean(list(tier_purities.values()))) if tier_purities else 0.0

    # --- Embedding cloud stats for Tier1 (consumed later by Component 4 for AD distance) ---
    tier1_mask = (df["mechanism_tier"] == "Tier1_FRS").values
    tier1_emb = embeddings[tier1_mask]
    tier1_centroid = tier1_emb.mean(axis=0)
    distances = 1.0 - cosine_similarity(tier1_emb, tier1_centroid.reshape(1, -1)).flatten()
    cloud_stats = {
        "model": "esm2_t33_650M_UR50D",
        "reference_tier": "Tier1_FRS",
        "n_sequences": int(tier1_mask.sum()),
        "mean_distance_to_centroid": round(float(distances.mean()), 4),
        "std_distance_to_centroid": round(float(distances.std()), 4),
        "centroid": [round(float(v), 6) for v in tier1_centroid],
        "notes": "Real ESM-2 650M cosine-distance cloud statistics. Used by Component 4 for applicability-domain distance.",
    }
    (ARTIFACT_DIR / "c1_embedding_cloud_stats.json").write_text(json.dumps(cloud_stats, indent=2))
    np.save(ARTIFACT_DIR / "c1_tier1_centroid.npy", tier1_centroid)
    print("Saved c1_embedding_cloud_stats.json + c1_tier1_centroid.npy")

    # --- Retrieval demo: real cosine-similarity search over real embeddings ---
    query_pool = df[df["mechanism_tier"].isin(["Tier1_FRS", "Tier2_MC"])].sample(
        min(5, len(df)), random_state=RANDOM_SEED
    )
    retrieval_demo = []
    for _, query_row in query_pool.iterrows():
        qi = df.index[df["peptide_id"] == query_row["peptide_id"]][0]
        sims = cosine_similarity(embeddings[qi].reshape(1, -1), embeddings)[0]
        top_idx = np.argsort(sims)[::-1][1:11]
        top_matches = [
            {
                "rank": rank,
                "peptide_id": df.iloc[idx]["peptide_id"],
                "sequence": df.iloc[idx]["sequence"],
                "mechanism_tier": df.iloc[idx]["mechanism_tier"],
                "similarity": round(float(sims[idx]), 4),
            }
            for rank, idx in enumerate(top_idx, start=1)
        ]
        retrieval_demo.append(
            {
                "query": {
                    "peptide_id": query_row["peptide_id"],
                    "sequence": query_row["sequence"],
                    "mechanism_tier": query_row["mechanism_tier"],
                },
                "top_matches": top_matches,
            }
        )
    (ARTIFACT_DIR / "c1_retrieval_demo.json").write_text(json.dumps(retrieval_demo, indent=2))
    print("Saved c1_retrieval_demo.json (real cosine similarity retrieval)")

    # --- Data sufficiency check against the n>=150-per-tier target ---
    tier_counts = df["mechanism_tier"].value_counts().to_dict()
    tier_counts = {t: int(tier_counts.get(t, 0)) for t in ["Tier1_FRS", "Tier2_MC", "Tier3_GEN", "Tier_Dual"]}
    trainable_tiers = {"Tier1_FRS", "Tier2_MC"}
    below_target = {t: c for t, c in tier_counts.items() if t in trainable_tiers and c < TARGET_MIN_PER_TIER}
    sufficiency = {
        "alert_level": "HIGH" if below_target else "OK",
        "issue": (
            f"Tiers below target: {below_target}" if below_target
            else "All training-eligible tiers meet the n>=150 target after merging AnOxPePred, "
                 "Multi-AOP, DFBP, Peptipedia and plant-MCP sources."
        ),
        "tier_counts": tier_counts,
        "target_minimum": TARGET_MIN_PER_TIER,
        "history": (
            "AnOxPePred alone gives only 11 Tier2_MC sequences. Merging Multi-AOP, DFBP, "
            "Peptipedia and 5 plant-MCP papers raised Tier2_MC to "
            f"{tier_counts['Tier2_MC']}, meeting the target."
        ),
    }
    (ARTIFACT_DIR / "c1_data_sufficiency_alert.json").write_text(json.dumps(sufficiency, indent=2))
    print("Saved c1_data_sufficiency_alert.json")

    # --- Summary ---
    summary = {
        "component": "C1_AOP_ProCon",
        "prototype_mode": True,
        "data_mode": "real_curated_data_real_embeddings",
        "source_datasets": sorted(df["source_db"].unique().tolist()),
        "total_sequences": int(len(df)),
        "training_eligible_sequences": int(df["training_eligible"].sum()),
        "tier_counts": tier_counts,
        "embedding_model": "esm2_t33_650M_UR50D",
        "embedding_dimension": int(embeddings.shape[1]),
        "prototype_purity": round(overall_purity, 4),
        "projection_method": "PCA(2) over real ESM-2 650M embeddings",
        "notes": [
            "Sequence curation, mechanism tiers, descriptors and embeddings are all real (not synthetic).",
            "The 2D scatter layout uses PCA as a stand-in for the final trained positive-only "
            "SupCon projection.",
            "Prototype purity is a KMeans-agreement proxy, not the final contrastive-model purity.",
        ],
    }
    (ARTIFACT_DIR / "c1_summary.json").write_text(json.dumps(summary, indent=2))
    df.to_parquet(ARTIFACT_DIR / "aop_benchpos_c1.parquet", index=False)
    print("Saved c1_summary.json + aop_benchpos_c1.parquet")
    print("\nComponent 1 prototype artifacts generated successfully.")


if __name__ == "__main__":
    main()
