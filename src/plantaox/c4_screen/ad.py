"""Cosine applicability-domain distances, leave-one-out calibration, and diagnostics."""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


def cosine_distance_to_centroid(vectors: np.ndarray, centroid: np.ndarray) -> np.ndarray:
    vectors = np.asarray(vectors, dtype=np.float32)
    centroid = np.asarray(centroid, dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=1) * np.linalg.norm(centroid)
    if np.any(norms == 0):
        raise ValueError("Cannot compute cosine distance for a zero-norm embedding")
    cosine = np.clip((vectors @ centroid) / norms, -1.0, 1.0)
    return (1.0 - cosine).astype(np.float32)


def leave_one_out_cloud_distances(cloud: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    cloud = np.asarray(cloud, dtype=np.float32)
    if cloud.ndim != 2 or cloud.shape[0] < 2:
        raise ValueError("At least two 2D cloud embeddings are required for leave-one-out calibration")
    total = cloud.sum(axis=0, dtype=np.float64).astype(np.float32)
    leave_centroids = (total[None, :] - cloud) / np.float32(len(cloud) - 1)
    norms = np.linalg.norm(cloud, axis=1) * np.linalg.norm(leave_centroids, axis=1)
    if np.any(norms == 0):
        raise ValueError("Zero-norm cloud embedding or leave-one-out centroid")
    cosine = np.clip(np.einsum("ij,ij->i", cloud, leave_centroids) / norms, -1.0, 1.0)
    return (1.0 - cosine).astype(np.float32), total / np.float32(len(cloud))


def calibrate_ad(cloud: np.ndarray, sd_multiplier: float = 1.0, cloud_source: str = "mock_cloud") -> dict:
    distances, centroid = leave_one_out_cloud_distances(cloud)
    mu = float(np.mean(distances, dtype=np.float64))
    sigma = float(np.std(distances, ddof=0, dtype=np.float64))
    t1, t2 = mu + sd_multiplier * sigma, mu + 2.0 * sd_multiplier * sigma
    if not np.isfinite([mu, sigma, t1, t2]).all() or t2 <= 0:
        raise ValueError(f"Invalid AD calibration values: mu={mu}, sigma={sigma}, t2={t2}")
    return {"cloud_source": cloud_source, "cloud_is_mock": cloud_source == "mock_cloud",
            "n_cloud": int(len(cloud)), "definition": "leave-one-out cosine distance to recomputed cloud centroid",
            "mu_cloud": mu, "sigma_cloud": sigma, "sd_multiplier": float(sd_multiplier),
            "t1": float(t1), "t2": float(t2), "d_norm": "min(d_AD / t2, 1)"}, centroid, distances


def assign_tiers(candidates: pd.DataFrame, embedding_index: pd.DataFrame, candidate_embeddings: np.ndarray,
                 cloud_embeddings: np.ndarray, sd_multiplier: float = 1.0,
                 cloud_source: str = "mock_cloud") -> tuple[pd.DataFrame, dict, np.ndarray]:
    params, centroid, cloud_distances = calibrate_ad(cloud_embeddings, sd_multiplier, cloud_source)
    if len(embedding_index) != len(candidate_embeddings):
        raise ValueError("Embedding index length does not equal candidate embedding rows")
    if not {"peptide_id", "sequence"}.issubset(candidates.columns):
        raise ValueError("Candidates require peptide_id and sequence columns")
    if not {"peptide_id", "sequence"}.issubset(embedding_index.columns):
        raise ValueError("Embedding index requires peptide_id and sequence columns")
    candidate_key = candidates.set_index("peptide_id")["sequence"]
    if embedding_index.peptide_id.duplicated().any():
        raise ValueError("Embedding index peptide_id values are not unique")
    if not embedding_index.peptide_id.isin(candidate_key.index).all():
        raise ValueError("Embedding index contains unknown peptide_id values")
    expected_sequences = embedding_index.peptide_id.map(candidate_key)
    if not np.array_equal(expected_sequences.to_numpy(), embedding_index.sequence.to_numpy()):
        raise ValueError("Embedding index peptide_id/sequence pairs do not match candidates")
    d_ad = cosine_distance_to_centroid(candidate_embeddings, centroid)
    out = candidates[["peptide_id", "sequence"]].copy()
    out["d_AD"] = np.nan
    out["d_norm"] = np.nan
    out["tier"] = pd.Series([pd.NA] * len(out), dtype="Int64")
    out["embedded"] = False
    positions = {pid: i for i, pid in enumerate(out.peptide_id)}
    for i, row in enumerate(embedding_index.itertuples(index=False)):
        pos = positions[row.peptide_id]
        distance = float(d_ad[i])
        out.at[pos, "d_AD"] = distance
        out.at[pos, "d_norm"] = min(distance / params["t2"], 1.0)
        out.at[pos, "tier"] = 1 if distance < params["t1"] else (2 if distance < params["t2"] else 3)
        out.at[pos, "embedded"] = True
    out["cloud_source"] = cloud_source
    params["embedded_count"] = int(out.embedded.sum())
    params["not_embedded_count"] = int((~out.embedded).sum())
    return out, params, cloud_distances


def write_ad_diagnostics(tiers: pd.DataFrame, memberships: pd.DataFrame, candidates: pd.DataFrame,
                         cloud_distances: np.ndarray, params: dict, output_dir: str | Path,
                         cloud_embeddings: np.ndarray | None = None,
                         candidate_embeddings: np.ndarray | None = None,
                         embedding_index: pd.DataFrame | None = None) -> dict:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    rows = tiers.merge(memberships[["peptide_id", "plant"]], on="peptide_id", how="left", validate="one_to_many")
    rows = rows[rows.embedded.astype(bool)]
    tier_rows, bin_rows = [], []
    labels = {1: "Tier 1", 2: "Tier 2", 3: "Tier 3"}
    for plant, group in rows.groupby("plant", sort=True):
        counts = group.tier.value_counts(normalize=True)
        for tier in (1, 2, 3):
            tier_rows.append({"plant": plant, "tier": tier, "fraction": float(counts.get(tier, 0.0)), "n": int((group.tier == tier).sum())})
        bins = pd.cut(group.length if "length" in group else group.sequence.str.len(), [2, 10, 20], labels=["3-10", "11-20"])
        for length_bin, part in group.assign(length_bin=bins).groupby("length_bin", observed=True):
            values = part.tier.value_counts(normalize=True)
            for tier in (1, 2, 3):
                bin_rows.append({"plant": plant, "length_bin": str(length_bin), "tier": tier,
                                 "fraction": float(values.get(tier, 0.0)), "n": int((part.tier == tier).sum())})
        fig, ax = plt.subplots(figsize=(8, 4.5))
        ax.hist(cloud_distances, bins=40, alpha=.55, label="Reference cloud (MOCK)", density=True)
        ax.hist(group.d_AD, bins=40, alpha=.5, label=f"{plant} candidates", density=True)
        ax.axvline(params["t1"], color="orange", linestyle="--", label="t1")
        ax.axvline(params["t2"], color="red", linestyle="--", label="t2")
        ax.set(xlabel="Cosine distance d_AD", ylabel="Density", title=f"{plant}: MOCK cloud applicability domain")
        ax.legend(); fig.tight_layout(); fig.savefig(output / f"d_ad_hist_{plant}.png", dpi=140); plt.close(fig)
    tier_df = pd.DataFrame(tier_rows)
    bins_df = pd.DataFrame(bin_rows)
    tier_df.to_csv(output / "tier_fractions_by_plant.csv", index=False)
    bins_df.to_csv(output / "tier_fractions_by_length_bin.csv", index=False)
    length_values = candidates.sequence.str.len().value_counts().sort_index()
    length_values.rename_axis("length").rename("count").to_csv(output / "candidate_length_distribution.csv")
    degenerate = []
    centered_cloud = None
    centered_centroid = None
    if cloud_embeddings is not None:
        cloud_array = np.asarray(cloud_embeddings, dtype=np.float32)
        feature_mean = cloud_array.mean(axis=0, dtype=np.float64).astype(np.float32)
        centered_cloud = cloud_array - feature_mean
        centered_centroid = centered_cloud.mean(axis=0, dtype=np.float64).astype(np.float32)
    candidate_position = ({pid: i for i, pid in enumerate(embedding_index.peptide_id)}
                          if embedding_index is not None and candidate_embeddings is not None else {})
    for plant, group in rows.groupby("plant", sort=True):
        fraction = float(group.tier.value_counts(normalize=True).max()) if len(group) else 0.0
        item = {"plant": plant, "max_tier_fraction": fraction, "degenerate_gt_95pct": fraction > .95}
        if fraction > .95:
            # Diagnostic only: baseline thresholds remain frozen and are never retuned here.
            if centered_cloud is not None and candidate_position:
                plant_ids = set(memberships.loc[memberships.plant == plant, "peptide_id"])
                indices = [candidate_position[pid] for pid in group.peptide_id if pid in plant_ids and pid in candidate_position]
                vectors = np.asarray(candidate_embeddings, dtype=np.float32)[indices] - feature_mean
                centered_cloud_distances = cosine_distance_to_centroid(centered_cloud, centered_centroid)
                centered_candidate_distances = cosine_distance_to_centroid(vectors, centered_centroid)
                item["anisotropy_check"] = {
                    "method": "subtract MOCK cloud feature mean, recompute centered cloud centroid, compare cosine distances",
                    "thresholds_retuned": False,
                    "centered_cloud_mean_d_AD": float(np.mean(centered_cloud_distances)),
                    "centered_candidate_mean_d_AD": float(np.mean(centered_candidate_distances)) if len(vectors) else None,
                    "centered_candidate_fraction_below_original_t1": float(np.mean(centered_candidate_distances < params["t1"])) if len(vectors) else None,
                    "centered_candidate_fraction_below_original_t2": float(np.mean(centered_candidate_distances < params["t2"])) if len(vectors) else None,
                }
            else:
                item["anisotropy_check"] = {"status": "unavailable; embedding arrays not supplied", "thresholds_retuned": False}
        degenerate.append(item)
    (output / "tier_degeneracy_report.json").write_text(json.dumps({"cloud_source": params["cloud_source"],
        "mock": True, "plants": degenerate}, indent=2) + "\n", encoding="utf-8")
    return {"tier_fractions": tier_df, "tier_fractions_by_length_bin": bins_df,
            "length_distribution": length_values, "degeneracy": degenerate}
