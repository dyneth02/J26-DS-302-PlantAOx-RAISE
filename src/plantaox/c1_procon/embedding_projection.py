"""Builds the small tables behind the C1 "Embeddings & contrastive learning" page.

Inputs (not committed, regenerate with notebooks/c1_procon Steps 2 and 4):
  * ``esm2_650M.npy`` + ``esm2_650M_sequences.txt``  - frozen ESM-2 650M embeddings, one row per benchmark peptide
  * ``model_*.pt``                                    - trained contrastive heads (a single ``Linear(1280, 128)``)
  * ``AOP-BenchPos_S2.csv``                           - the benchmark (labels, length, source, homology groups)

Outputs (small, committed under ``data/processed/c1_procon/results``):
  * ``embedding_projection.csv`` - a 2-D PCA of the same 1,389 peptides in three spaces
  * ``embedding_stats.json``     - variance explained, cosine structure and neighbour purity per space

Nothing here is a model result: it only describes the geometry of the already-accepted embeddings.

Usage::

    python -m plantaox.c1_procon.embedding_projection --embeddings <dir> --checkpoints <dir> --benchmark <csv> --out <dir>
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

# (key, checkpoint file, plain-language name)
TRAINED_HEADS = [
    ("primary", "model_primary.pt", "Main trained head"),
    ("maxspread", "model_primary_maxspread.pt", "Head selected for spread"),
]
NEIGHBOURS = 10


def unit(x: np.ndarray) -> np.ndarray:
    return x / np.clip(np.linalg.norm(x, axis=1, keepdims=True), 1e-12, None)


def pca2(x: np.ndarray) -> tuple[np.ndarray, list[float]]:
    """Deterministic 2-D PCA (SVD of the centred matrix); also returns the variance share of PC1 and PC2."""
    centred = x - x.mean(axis=0, keepdims=True)
    u, s, _ = np.linalg.svd(centred, full_matrices=False)
    coords = u[:, :2] * s[:2]
    share = (s**2) / (s**2).sum()
    return coords, [float(share[0]), float(share[1])]


def strict_pool(s2: pd.DataFrame) -> pd.DataFrame:
    mech = s2[s2["labels"].str.contains("FRS|MC")]
    pool = mech[mech["strict_evidence"].astype(str) == "True"].copy()
    pool["mc_active"] = pool["labels"].str.contains("MC")
    return pool


def cosine_structure(z: np.ndarray, mc: np.ndarray) -> dict[str, float]:
    """Mean pairwise cosine within MC-active, within FRS-only and between the two (unit vectors)."""
    sim = z @ z.T
    n = len(z)
    off_diag = ~np.eye(n, dtype=bool)
    mm = off_diag & np.outer(mc, mc)
    ff = off_diag & np.outer(~mc, ~mc)
    mf = np.outer(mc, ~mc)
    within_mc, within_frs, between = float(sim[mm].mean()), float(sim[ff].mean()), float(sim[mf].mean())
    return {
        "within_mc": within_mc,
        "within_frs": within_frs,
        "between": between,
        "all_pairs": float(sim[off_diag].mean()),
        "separation": (within_mc + within_frs) / 2 - between,
    }


def neighbour_purity(z: np.ndarray, mc: np.ndarray, groups: np.ndarray, k: int = NEIGHBOURS) -> float:
    """Of the k nearest neighbours of an MC-active peptide, the share that are also MC-active.

    Neighbours from the same homology group are excluded, otherwise near-duplicates would inflate the score.
    """
    sim = z @ z.T
    same_group = groups[:, None] == groups[None, :]
    sim = np.where(same_group, -np.inf, sim)
    purities = []
    for i in np.flatnonzero(mc):
        nearest = np.argpartition(-sim[i], k)[:k]
        purities.append(mc[nearest].mean())
    return float(np.mean(purities))


def build(embeddings_dir: Path, checkpoints_dir: Path, benchmark_csv: Path, out_dir: Path) -> None:
    import torch

    s2 = pd.read_csv(benchmark_csv)
    seqs = (embeddings_dir / "esm2_650M_sequences.txt").read_text(encoding="utf-8").splitlines()
    raw = np.load(embeddings_dir / "esm2_650M.npy").astype(np.float32)
    assert raw.shape[0] == len(seqs) == len(s2), "embedding rows must align with the benchmark"
    s2 = s2.set_index("sequence").loc[seqs].reset_index()  # follow the embedding row order

    spaces: dict[str, np.ndarray] = {"esm2": unit(raw)}
    names = {"esm2": "Untrained ESM-2 650M"}
    for key, filename, name in TRAINED_HEADS:
        ckpt = torch.load(checkpoints_dir / filename, map_location="cpu", weights_only=False)
        head = torch.nn.Linear(ckpt["input_dim"], 128)
        head.load_state_dict(ckpt["head_state_dict"])
        head.eval()
        with torch.no_grad():
            spaces[key] = torch.nn.functional.normalize(head(torch.tensor(raw)), dim=-1).numpy()
        names[key] = name

    strict = strict_pool(s2)
    in_strict = s2["sequence"].isin(set(strict["sequence"])).to_numpy()
    mc_strict = s2.loc[in_strict, "labels"].str.contains("MC").to_numpy()
    groups_strict = s2.loc[in_strict, "homology_group"].astype(str).to_numpy()

    table = pd.DataFrame(
        {
            "sequence": s2["sequence"],
            "label": s2["labels"],
            "length": s2["length"],
            "source_group": s2["source_group"],
            "strict_class": np.where(in_strict, np.where(s2["labels"].str.contains("MC"), "MC-active", "FRS-only"), "not in strict pool"),
        }
    )
    stats: dict[str, dict] = {}
    for key, z in spaces.items():
        coords, share = pca2(z)
        table[f"{key}_pc1"], table[f"{key}_pc2"] = coords[:, 0].round(5), coords[:, 1].round(5)
        zs = z[in_strict]
        entry = {"name": names[key], "dim": int(z.shape[1]), "pc_variance_share": [round(v, 4) for v in share]}
        entry.update({k: round(v, 4) for k, v in cosine_structure(zs, mc_strict).items()})
        entry["mc_neighbour_purity"] = round(neighbour_purity(zs, mc_strict, groups_strict), 4)
        entry["pc1_length_correlation"] = round(float(np.corrcoef(coords[:, 0], np.log(s2["length"].to_numpy()))[0, 1]), 4)
        stats[key] = entry

    long_pep = int((s2["length"] >= 10).sum())
    meta = {
        "n_peptides": int(len(s2)),
        "n_strict": int(in_strict.sum()),
        "n_mc_active": int(mc_strict.sum()),
        "chance_mc_neighbour_purity": round(float(mc_strict.mean()), 4),
        "neighbours": NEIGHBOURS,
        "pooling_rule": "max-pool over residues for peptides shorter than 10 aa, mean-pool for 10 aa or longer",
        "peptides_ge_10_aa": long_pep,
        "peptides_lt_10_aa": int(len(s2) - long_pep),
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    table.to_csv(out_dir / "embedding_projection.csv", index=False)
    (out_dir / "embedding_stats.json").write_text(json.dumps({"meta": meta, "spaces": stats}, indent=2), encoding="utf-8")
    print(f"wrote {out_dir / 'embedding_projection.csv'} ({len(table)} rows) and embedding_stats.json")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--embeddings", type=Path, required=True)
    parser.add_argument("--checkpoints", type=Path, required=True)
    parser.add_argument("--benchmark", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    build(args.embeddings, args.checkpoints, args.benchmark, args.out)


if __name__ == "__main__":
    main()
