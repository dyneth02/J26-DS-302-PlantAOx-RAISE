"""Geometry of the frozen and trained embeddings, plus the contrastive training pairs (read-only)."""

from __future__ import annotations

import pandas as pd

from backend.app.schemas.c1_procon import (
    EmbeddingMeta,
    EmbeddingPoint,
    EmbeddingResponse,
    EmbeddingSpace,
    PairExample,
    PairSetCount,
)
from backend.app.services.c1_procon.artifacts import num, read_csv, read_json, req

SPACE_KEYS = ["esm2", "primary", "maxspread"]
PAIR_SET_TEXT = {
    "positive_pairs": "Main pairs: peptides of the same mechanism that are close in 14 physico-chemical descriptors",
    "knn_pairs_k8": "Nearest-neighbour pairs: the 8 closest same-mechanism partners of each peptide",
    "ablation_random_pairs": "Control: random same-mechanism pairs (same count as the main pairs)",
    "ablation_physchem_only_pairs": "Control: pairs chosen by descriptors only, ignoring the mechanism label",
}
READING_GUIDE = [
    "Each dot is one peptide, placed by a projection (PCA, shown in 2-D or 3-D) of its embedding. Peptides that look alike to the model sit close together.",
    "If the model had learned the mechanism, metal-chelating (MC-active) peptides would form their own region. They do not: they sit among the radical-scavenging (FRS-only) peptides.",
    "The strongest structure in the untrained embedding is peptide length: short and long peptides form separate clouds because ESM-2 vectors are pooled differently below and above 10 amino acids.",
    "Training pulls same-mechanism pairs together, but with so few positive examples the main head pulls everything together: nearly all pairs end up with cosine similarity 0.99 (collapse).",
]


def get_embedding() -> EmbeddingResponse:
    stats = read_json("results/embedding_stats.json")
    meta = EmbeddingMeta(**stats["meta"])
    spaces = [EmbeddingSpace(key=key, **{k: v for k, v in stats["spaces"][key].items()}) for key in SPACE_KEYS]

    proj = read_csv("results/embedding_projection.csv")
    points = [
        EmbeddingPoint(
            sequence=str(r["sequence"]),
            label=str(r["label"]),
            length=int(r["length"]),
            source_group=None if pd.isna(r["source_group"]) else str(r["source_group"]),
            strict_class=str(r["strict_class"]),
            coords={key: [req(r[f"{key}_pc1"]), req(r[f"{key}_pc2"]), req(r[f"{key}_pc3"])] for key in SPACE_KEYS},
        )
        for _, r in proj.iterrows()
    ]

    manifest = read_json("pairs_manifest.json")
    counts = manifest["pair_counts"]["strict"]
    pair_counts = [PairSetCount(pair_set=k, description=PAIR_SET_TEXT[k], pairs=int(v)) for k, v in counts.items() if k in PAIR_SET_TEXT]

    pairs = read_csv("pairs/strict/positive_pairs.csv")
    examples: list[PairExample] = []
    used: set[str] = set()
    for mechanism in ("MC", "FRS"):
        sub = pairs[(pairs["mechanism"] == mechanism) & (pairs["seq1"].str.len() >= 4) & (pairs["seq2"].str.len() >= 4)]
        picked = 0
        for _, r in sub.sort_values(["distance", "seq1", "seq2"]).iterrows():
            if r["seq1"] in used or r["seq2"] in used:  # show different peptides for each mechanism
                continue
            examples.append(PairExample(mechanism=mechanism, seq1=str(r["seq1"]), seq2=str(r["seq2"]), distance=req(r["distance"])))
            used.update([r["seq1"], r["seq2"]])
            picked += 1
            if picked == 3:
                break

    return EmbeddingResponse(
        meta=meta,
        spaces=spaces,
        points=points,
        pair_counts=pair_counts,
        pair_examples=examples,
        reading_guide=READING_GUIDE,
    )
