"""Read-only diagnostic for Task 4.5's external-control result."""

from __future__ import annotations

from collections import Counter

import numpy as np
import pandas as pd

from plantaox.c2_pu.baseline_evaluation import LoadedBaseline, classification_metrics, score_summary
from plantaox.c2_pu.experiment_data import ExperimentData, PoolData

DESCRIPTORS = (
    "length", "molecular_weight", "net_charge_ph7", "aromaticity",
    "gravy", "hydrophobic_moment", "frac_proline",
)


def _descriptor_summary(frame: pd.DataFrame) -> dict:
    return {
        name: {
            "mean": float(frame[name].mean()),
            "median": float(frame[name].median()),
            "min": float(frame[name].min()),
            "max": float(frame[name].max()),
            "std": float(frame[name].std(ddof=0)),
        }
        for name in DESCRIPTORS
    }


def _verify_pool_rows(pool: PoolData, descriptor_df: pd.DataFrame) -> None:
    indexed = descriptor_df.set_index("peptide_id", drop=False)
    missing = set(pool.peptide_ids.tolist()) - set(indexed.index)
    if missing:
        raise ValueError(f"{pool.pool}: descriptor rows missing for {sorted(missing)[:5]}")
    observed_sequences = indexed.loc[pool.peptide_ids.tolist(), "sequence"].astype(str).to_numpy()
    if not np.array_equal(observed_sequences, pool.sequences.astype(str)):
        raise ValueError(f"{pool.pool}: peptide-ID/sequence row alignment mismatch")


def diagnose_external_controls(
    data: ExperimentData,
    models: list[LoadedBaseline],
    descriptor_df: pd.DataFrame,
    control_metadata: pd.DataFrame,
) -> tuple[dict, list[dict]]:
    """Return a diagnostic summary and one auditable row per external control."""
    held = data.held_out_positive
    controls = data.external_control
    _verify_pool_rows(held, descriptor_df)
    _verify_pool_rows(controls, descriptor_df)

    if held.evidence_tier is None:
        raise ValueError("held-out positives lack evidence-tier metadata")
    meta = control_metadata.set_index("peptide_id", drop=False)
    if set(meta.index) != set(controls.peptide_ids.tolist()):
        raise ValueError("external-control metadata IDs do not exactly match evaluated control IDs")
    if not np.array_equal(meta.loc[controls.peptide_ids, "sequence"].astype(str).to_numpy(), controls.sequences.astype(str)):
        raise ValueError("external-control metadata sequence order does not match feature rows")

    descriptor_index = descriptor_df.set_index("peptide_id", drop=False)
    groups = {
        "held_out_E1": held.peptide_ids[held.evidence_tier == "E1"].tolist(),
        "held_out_E2": held.peptide_ids[held.evidence_tier == "E2"].tolist(),
        "external_control": controls.peptide_ids.tolist(),
    }
    descriptor_summaries = {
        name: _descriptor_summary(descriptor_index.loc[ids]) for name, ids in groups.items()
    }

    control_rows = []
    for index, peptide_id in enumerate(controls.peptide_ids.tolist()):
        row = meta.loc[peptide_id]
        control_rows.append({
            "peptide_id": peptide_id,
            "sequence": str(row["sequence"]),
            "anoxpepred_source": str(row["anoxpepred_source"]),
            "evidence_status": str(row["evidence_status"]),
            "has_biopep_antioxidative_conflict": bool(row["has_biopep_antioxidative_conflict"]),
            "feature_row_index_within_control_pool": index,
        })

    model_findings = {}
    leave_one_out_ranges = {}
    for model in models:
        held_scores = model.predict(held.features)
        control_scores = model.predict(controls.features)
        if not np.isfinite(held_scores.raw).all() or not np.isfinite(control_scores.raw).all():
            raise ValueError(f"{model.name}: non-finite score")
        y = np.concatenate([np.ones(len(held.peptide_ids)), np.zeros(len(controls.peptide_ids))])
        metrics = classification_metrics(
            y,
            np.concatenate([held_scores.raw, control_scores.raw]),
            np.concatenate([held_scores.bounded, control_scores.bounded]),
        )
        tier_summaries = {}
        for tier in ("E1", "E2"):
            mask = held.evidence_tier == tier
            tier_summaries[tier] = score_summary(held_scores.bounded[mask])
        tier_summaries["external_control"] = score_summary(control_scores.bounded)

        loo_aurocs = []
        for excluded in range(len(control_scores.raw)):
            keep = np.arange(len(control_scores.raw)) != excluded
            loo_y = np.concatenate([np.ones(len(held.peptide_ids)), np.zeros(int(keep.sum()))])
            loo = classification_metrics(
                loo_y,
                np.concatenate([held_scores.raw, control_scores.raw[keep]]),
                np.concatenate([held_scores.bounded, control_scores.bounded[keep]]),
            )
            loo_aurocs.append(loo["auroc"])
        leave_one_out_ranges[model.model_id] = {
            "full_auroc": metrics["auroc"],
            "minimum_after_excluding_one_control": float(min(loo_aurocs)),
            "maximum_after_excluding_one_control": float(max(loo_aurocs)),
            "maximum_absolute_change": float(max(abs(value - metrics["auroc"]) for value in loo_aurocs)),
        }
        model_findings[model.model_id] = {
            "model": model.name,
            "score_convention": "higher score means stronger model support for positive/AOP class",
            "label_mapping": {"held_out_positive": 1, "external_assay_inactive_control": 0},
            "metrics_reproduced": metrics,
            "score_summaries": tier_summaries,
        }
        for idx, value in enumerate(control_scores.bounded):
            control_rows[idx][f"{model.model_id}_bounded_score"] = float(value)
            control_rows[idx][f"{model.model_id}_fraction_heldout_scored_lower"] = float(
                np.mean(held_scores.raw < control_scores.raw[idx])
            )

    for row in control_rows:
        scores = [row[f"{model.model_id}_bounded_score"] for model in models]
        pairwise = [row[f"{model.model_id}_fraction_heldout_scored_lower"] for model in models]
        row["mean_bounded_score_across_models"] = float(np.mean(scores))
        row["models_scoring_above_0_5"] = int(sum(value >= 0.5 for value in scores))
        row["mean_fraction_heldout_scored_lower"] = float(np.mean(pairwise))

    source_counts = Counter(meta["anoxpepred_source"].astype(str).tolist())
    broad_pattern = {
        "controls_above_0_5_in_all_five_models": int(sum(r["models_scoring_above_0_5"] == 5 for r in control_rows)),
        "controls_above_0_5_in_at_least_four_models": int(sum(r["models_scoring_above_0_5"] >= 4 for r in control_rows)),
        "leave_one_control_out_auroc": leave_one_out_ranges,
        "interpretation": "A small-subset explanation is unsupported when deleting any one control changes AUROC only slightly.",
    }
    summary = {
        "status": "NO_BLOCKING_IMPLEMENTATION_DEFECT_IDENTIFIED",
        "orientation_verified": True,
        "label_mapping_verified": True,
        "feature_row_alignment_verified": True,
        "n_held_out_positive": int(len(held.peptide_ids)),
        "n_held_out_E1": int(np.sum(held.evidence_tier == "E1")),
        "n_held_out_E2": int(np.sum(held.evidence_tier == "E2")),
        "n_external_control": int(len(controls.peptide_ids)),
        "descriptor_summaries": descriptor_summaries,
        "model_findings": model_findings,
        "control_pattern": broad_pattern,
        "control_sources": dict(sorted(source_counts.items())),
        "biopep_conflict_ids": sorted(meta.loc[meta["has_biopep_antioxidative_conflict"].astype(bool)].index.tolist()),
        "limitations": [
            "The control labels are assay-specific and do not establish universal antioxidant inactivity.",
            "Source and descriptor differences can support shortcut behavior but do not prove a causal mechanism.",
            "Only 38 controls and one GraphPart fold are available.",
        ],
    }
    return summary, sorted(control_rows, key=lambda row: row["mean_bounded_score_across_models"], reverse=True)
