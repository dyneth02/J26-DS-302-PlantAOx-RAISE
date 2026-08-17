"""Component 1 PLM-scaling ablation.

The architecture doc lists "PLM scaling analysis in the representation setting" as one of
C1's novelty points. With real precomputed ESM-2 embeddings now available at four scales
(35M / 150M / 650M / 3B parameters, all for the same real AOP-BenchPos sequences), this is
no longer a placeholder -- it's a real, if small-sample, experiment: does a bigger protein
language model actually produce a more mechanism-tier-separable representation space for
antioxidant peptides?

For each scale, computed on the real curated sequences:
  - Recall@10: for a sample of query peptides, the fraction of their 10 nearest neighbours
    (by cosine similarity) that share the same mechanism tier.
  - Prototype purity: same per-tier KMeans-agreement metric used in generate_c1_artifacts.py.

Requires data/processed/aop_sequences.parquet, so run generate_c1_artifacts.py first.
"""
import json
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity

RANDOM_SEED = 42
np.random.seed(RANDOM_SEED)

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
ARTIFACT_DIR = ROOT / "artifacts" / "c1"

SCALES = [
    {"name": "esm2_t12_35M_UR50D", "prefix": "esm2_35M", "params": "35M"},
    {"name": "esm2_t30_150M_UR50D", "prefix": "esm2_150M", "params": "150M"},
    {"name": "esm2_t33_650M_UR50D", "prefix": "esm2_650M", "params": "650M"},
    {"name": "esm2_t36_3B_UR50D", "prefix": "esm2_3B", "params": "3B"},
]
N_QUERY_SAMPLE = 300
RECALL_K = 10


def load_scale_embeddings(prefix: str, df: pd.DataFrame):
    seqs = [s.strip() for s in (RAW / f"{prefix}_sequences.txt").read_text().splitlines() if s.strip()]
    emb = np.load(RAW / f"{prefix}.npy")
    lookup = {s: emb[i] for i, s in enumerate(seqs)}

    aligned = df[df["sequence"].isin(lookup)].reset_index(drop=True)
    vectors = np.stack([lookup[s] for s in aligned["sequence"]])
    return aligned, vectors


def recall_at_k(aligned: pd.DataFrame, vectors: np.ndarray, k: int, n_queries: int) -> float:
    tiers = aligned["mechanism_tier"].values
    n = len(aligned)
    query_idx = np.random.RandomState(RANDOM_SEED).choice(n, size=min(n_queries, n), replace=False)

    hits = 0
    for qi in query_idx:
        sims = cosine_similarity(vectors[qi].reshape(1, -1), vectors)[0]
        top_k = np.argsort(sims)[::-1][1:k + 1]
        hits += (tiers[top_k] == tiers[qi]).mean()
    return float(hits / len(query_idx))


def prototype_purity(aligned: pd.DataFrame, vectors: np.ndarray) -> float:
    tiers = aligned["mechanism_tier"].values
    n_clusters = aligned["mechanism_tier"].nunique()
    kmeans = KMeans(n_clusters=n_clusters, random_state=RANDOM_SEED, n_init=10)
    cluster_labels = kmeans.fit_predict(vectors)

    purities = []
    for tier in np.unique(tiers):
        tier_mask = tiers == tier
        home_cluster = np.bincount(cluster_labels[tier_mask]).argmax()
        home_mask = cluster_labels == home_cluster
        purities.append((tiers[home_mask] == tier).mean())
    return float(np.mean(purities))


def main():
    df = pd.read_parquet(ROOT / "data" / "processed" / "aop_sequences.parquet")

    results = []
    for scale in SCALES:
        aligned, vectors = load_scale_embeddings(scale["prefix"], df)
        recall = recall_at_k(aligned, vectors, RECALL_K, N_QUERY_SAMPLE)
        purity = prototype_purity(aligned, vectors)
        results.append({
            "model": scale["name"],
            "params": scale["params"],
            "embedding_dim": int(vectors.shape[1]),
            "n_sequences": int(len(aligned)),
            f"recall_at_{RECALL_K}": round(recall, 4),
            "prototype_purity": round(purity, 4),
        })
        print(f"{scale['name']:24s} dim={vectors.shape[1]:5d}  Recall@{RECALL_K}={recall:.4f}  purity={purity:.4f}")

    ablation = {
        "description": (
            "Real PLM-scaling comparison: mean-pooled ESM-2 embeddings at 4 scales for the "
            "same real curated AOP-BenchPos sequences, evaluated by mechanism-tier retrieval "
            "Recall@10 and KMeans prototype purity. No fine-tuning; raw mean-pooled embeddings only."
        ),
        "results": results,
    }
    (ARTIFACT_DIR / "c1_scaling_ablation.json").write_text(json.dumps(ablation, indent=2))
    print("Saved c1_scaling_ablation.json")


if __name__ == "__main__":
    main()
