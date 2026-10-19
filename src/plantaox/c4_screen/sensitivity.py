"""C4 post-hoc diagnostics; sensitivity outputs never modify production tiers."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

from .ad import calibrate_ad, cosine_distance_to_centroid


def write_length_diagnostics(tiers_path: str | Path, candidates_path: str | Path,
                             memberships_path: str | Path, cloud_sequences_path: str | Path,
                             output_dir: str | Path) -> tuple[Path, Path]:
    """Write per-plant d_AD/length Spearman correlations and cloud/candidate length distributions."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    tiers = pd.read_parquet(tiers_path)
    candidates = pd.read_parquet(candidates_path)
    memberships = pd.read_parquet(memberships_path)
    cloud = pd.read_csv(cloud_sequences_path)

    rows = tiers.merge(memberships[["peptide_id", "plant"]], on="peptide_id", how="left",
                       validate="one_to_many")
    rows = rows[rows.embedded.astype(bool)].copy()
    rows["length"] = rows.sequence.str.len()
    correlations = []
    for plant, part in rows.groupby("plant", sort=True):
        result = spearmanr(part.length.to_numpy(), part.d_AD.to_numpy(dtype=float))
        correlations.append({"plant": plant, "n": len(part), "spearman_rho": float(result.statistic),
            "p_value_descriptive_only": float(result.pvalue), "reference_source": "mock_cloud",
            "interpretation": "descriptive association; reference cloud is MOCK"})
    corr_path = out / "d_ad_vs_sequence_length_spearman.csv"
    pd.DataFrame(correlations).to_csv(corr_path, index=False, lineterminator="\n")

    distributions = []
    cohorts = [("mock_cloud", "reference_cloud", cloud.sequence.astype(str))]
    unique_candidates = candidates.drop_duplicates("peptide_id")
    cohorts.append(("all_candidates", "unique_candidates", unique_candidates.sequence.astype(str)))
    for plant, group in memberships.groupby("plant", sort=True):
        ids = set(group.peptide_id)
        subset = candidates[candidates.peptide_id.isin(ids)]
        cohorts.append((plant, "candidate_plant", subset.sequence.astype(str)))
    for label, cohort, sequences in cohorts:
        counts = sequences.str.len().value_counts().sort_index()
        total = int(counts.sum())
        for length, count in counts.items():
            distributions.append({"group": label, "cohort": cohort, "length": int(length),
                "count": int(count), "fraction": float(count / total),
                "source": "mock_cloud" if cohort == "reference_cloud" else "candidate_sequences"})
    length_path = out / "cloud_vs_candidate_length_distribution.csv"
    pd.DataFrame(distributions).to_csv(length_path, index=False, lineterminator="\n")
    return corr_path, length_path


def write_mean_centering_sensitivity(candidates_path: str | Path, memberships_path: str | Path,
                                     embedding_index_path: str | Path, candidate_embeddings_path: str | Path,
                                     cloud_embeddings_path: str | Path, baseline_tiers_path: str | Path,
                                     output_dir: str | Path, sd_multiplier: float = 1.0,
                                     chunk_rows: int = 8192) -> tuple[Path, Path]:
    """Assess mean-centering as a separate sensitivity; preserve the baseline tier table unchanged.

    The centering vector is the joint mean of the supplied candidate and MOCK-cloud embeddings.
    The same LOO calibration rule is recomputed in this transformed space; this is a labeled
    sensitivity scenario, not threshold tuning and never overwrites production thresholds/tiers.
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    candidates = pd.read_parquet(candidates_path)
    index = pd.read_parquet(embedding_index_path)
    if not candidates[["peptide_id", "sequence"]].reset_index(drop=True).equals(
            index[["peptide_id", "sequence"]].reset_index(drop=True)):
        raise ValueError("Mean-centering sensitivity requires candidate/index row order to match")
    matrix = np.load(candidate_embeddings_path, mmap_mode="r")
    cloud = np.load(cloud_embeddings_path, mmap_mode="r")
    if matrix.ndim != 2 or cloud.ndim != 2 or matrix.shape[1] != cloud.shape[1]:
        raise ValueError(f"Mean-centering sensitivity dimension mismatch: candidates={matrix.shape}, cloud={cloud.shape}")

    total = np.zeros(matrix.shape[1], dtype=np.float64)
    for start in range(0, len(matrix), chunk_rows):
        total += np.asarray(matrix[start:start + chunk_rows], dtype=np.float64).sum(axis=0)
    total += np.asarray(cloud, dtype=np.float64).sum(axis=0)
    center = (total / (len(matrix) + len(cloud))).astype(np.float32)
    centered_cloud = np.asarray(cloud, dtype=np.float32) - center
    sensitivity_params, centroid, _ = calibrate_ad(centered_cloud, sd_multiplier, "mock_cloud")

    d_ad = np.empty(len(matrix), dtype=np.float32)
    for start in range(0, len(matrix), chunk_rows):
        vectors = np.asarray(matrix[start:start + chunk_rows], dtype=np.float32) - center
        d_ad[start:start + len(vectors)] = cosine_distance_to_centroid(vectors, centroid)
    t1, t2 = sensitivity_params["t1"], sensitivity_params["t2"]
    sensitivity_tier = np.where(d_ad < t1, 1, np.where(d_ad < t2, 2, 3)).astype(np.int8)

    baseline = pd.read_parquet(baseline_tiers_path)[["peptide_id", "tier"]].copy()
    baseline = baseline.set_index("peptide_id").loc[candidates.peptide_id].reset_index()
    baseline_tier = pd.to_numeric(baseline.tier, errors="coerce").to_numpy(dtype=float)
    memberships = pd.read_parquet(memberships_path)
    lengths = candidates.sequence.str.len().to_numpy()
    rows = []
    groups = [("all_candidates", candidates.peptide_id)]
    groups.extend((plant, part.peptide_id) for plant, part in memberships.groupby("plant", sort=True))
    for group, peptide_ids in groups:
        positions = candidates.reset_index().set_index("peptide_id").loc[list(peptide_ids), "index"].to_numpy(dtype=int)
        bins = [("all", np.ones(len(positions), dtype=bool)), ("3-10", (lengths[positions] >= 3) & (lengths[positions] <= 10)),
                ("11-20", (lengths[positions] >= 11) & (lengths[positions] <= 20))]
        for length_bin, mask in bins:
            selected = positions[mask]
            if not len(selected):
                continue
            for tier in (1, 2, 3):
                rows.append({"analysis": "MEAN_CENTERING_SENSITIVITY_ONLY", "group": group,
                    "length_bin": length_bin, "n": len(selected), "tier": tier,
                    "baseline_fraction": float(np.mean(baseline_tier[selected] == tier)),
                    "mean_centered_fraction": float(np.mean(sensitivity_tier[selected] == tier)),
                    "fraction_delta": float(np.mean(sensitivity_tier[selected] == tier) - np.mean(baseline_tier[selected] == tier)),
                    "thresholds_tuned": False, "reference_source": "mock_cloud"})
    fractions_path = out / "mean_centering_tier_fraction_sensitivity.csv"
    pd.DataFrame(rows).to_csv(fractions_path, index=False, lineterminator="\n")
    sensitivity_params.update({"analysis": "MEAN_CENTERING_SENSITIVITY_ONLY", "thresholds_tuned": False,
        "centering_vector": "joint feature-wise mean of all candidate and MOCK-cloud embeddings",
        "candidate_count": int(len(candidates)), "cloud_source": "mock_cloud"})
    params_path = out / "mean_centering_sensitivity_params.json"
    params_path.write_text(json.dumps(sensitivity_params, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return fractions_path, params_path
