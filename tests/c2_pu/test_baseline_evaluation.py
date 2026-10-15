from __future__ import annotations

import csv
import json
from pathlib import Path

import numpy as np
import pytest

from plantaox.c2_pu.baseline_evaluation import (
    classification_metrics,
    load_accepted_baselines,
    score_summary,
)


def _accepted_summary_paths() -> dict[str, Path]:
    root = Path("data/processed/c2_pu")
    return {
        "M1": root / "fr4_pn_baseline_fold0_summary.json",
        "M2": root / "fr4_nnpu_baseline_fold0_summary.json",
        "M3": root / "fr4_nnpu_corrective_fold0_summary.json",
        "M4": root / "fr4_two_step_pu_baseline_fold0_summary.json",
        "M5": root / "fr4_pu_bagging_baseline_fold0_summary.json",
    }


def test_classification_metrics_match_known_perfect_case():
    labels = np.array([1, 1, 0, 0])
    scores = np.array([0.9, 0.8, 0.2, 0.1])
    result = classification_metrics(labels, scores, scores)
    for key in ("mcc", "average_precision", "auroc", "precision", "recall", "f1", "balanced_accuracy"):
        assert result[key] == pytest.approx(1.0)
    assert result["confusion_matrix"] == {"tp": 2, "tn": 2, "fp": 0, "fn": 0}


def test_ranking_metrics_retain_raw_scores_while_threshold_metrics_use_bounded_scores():
    labels = np.array([1, 0, 1, 0])
    raw = np.array([1.8, 1.2, 0.7, 0.2])
    bounded = np.clip(raw, 0.0, 1.0)
    result = classification_metrics(labels, raw, bounded)
    assert result["average_precision"] == pytest.approx(5 / 6)
    assert result["confusion_matrix"] == {"tp": 2, "tn": 1, "fp": 1, "fn": 0}


def test_score_summary_reports_bounds_and_saturation_fractions():
    result = score_summary(np.array([0.0, 0.005, 0.5, 0.75, 0.995]))
    assert result["n"] == 5
    assert result["median"] == pytest.approx(0.5)
    assert result["fraction_lt_0_01"] == pytest.approx(0.4)
    assert result["fraction_gt_0_99"] == pytest.approx(0.2)
    assert result["fraction_gt_0_5"] == pytest.approx(0.4)


def test_all_five_accepted_checkpoints_reload_and_score_with_valid_bounded_output():
    models = load_accepted_baselines(_accepted_summary_paths())
    assert [model.model_id for model in models] == ["M1", "M2", "M3", "M4", "M5"]
    features = np.zeros((3, 495), dtype=np.float32)
    for model in models:
        output = model.predict(features)
        assert output.raw.shape == (3,)
        assert output.bounded.shape == (3,)
        assert np.isfinite(output.raw).all()
        assert np.isfinite(output.bounded).all()
        assert ((output.bounded >= 0) & (output.bounded <= 1)).all()
    assert "clipped" in models[3].predict(features).transformation


def test_real_fold0_evaluation_contains_five_models_and_common_samples():
    root = Path("data/processed/c2_pu")
    evaluation = json.loads((root / "fr4_baseline_evaluation_fold0.json").read_text(encoding="utf-8"))
    with open(root / "fr4_baseline_comparison_fold0.csv", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert [row["model_id"] for row in rows] == ["M1", "M2", "M3", "M4", "M5"]
    assert {(row["n_positive"], row["n_control"]) for row in rows} == {("124", "38")}
    assert evaluation["dataset_counts"] == {
        "held_out_positive": 124, "C1": 3788, "C2": 2000, "C3_fold0": 2000, "external_control": 38,
    }
    assert evaluation["leakage_report"]["overlap_found"] is False
    assert evaluation["smoke_checks"]["retraining_performed"] is False

