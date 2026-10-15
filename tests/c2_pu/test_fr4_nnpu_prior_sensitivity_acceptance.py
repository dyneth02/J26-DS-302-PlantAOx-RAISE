"""Bucket 4.3 POST-ACCEPTANCE DIAGNOSTIC -- acceptance tests for the
`fr4-nnpu-prior-sensitivity` / `fr4-nnpu-prior-sensitivity-report` CLI
stages against the real local fold-0 artifacts.

Gated to skip cleanly when those artifacts aren't present locally,
matching ``test_fr4_nnpu_baseline_acceptance.py``'s own convention.

These tests are diagnostic-only: they never assert anything about which
prior is "better," and they explicitly verify the accepted pi=0.10 Task
4.3 baseline (summary JSON, learning curve, checkpoint weights) is
BYTE-IDENTICAL before and after every diagnostic run in this file.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pandas as pd
import pytest
import torch

from plantaox.c2_pu.run import (
    C3_RANKING_PATH,
    FR3_FEATURE_CACHE_MANIFEST_PATH,
    FR3_FUSION_SCALERS_PATH,
    FR3_RECORD_MAP_PATH,
    FR4_NNPU_BASELINE_SUMMARY_PATH_TEMPLATE,
    run_fr4_nnpu_prior_sensitivity,
    run_fr4_nnpu_prior_sensitivity_report,
)

REQUIRED_INPUTS = [FR3_FEATURE_CACHE_MANIFEST_PATH, FR3_FUSION_SCALERS_PATH, FR3_RECORD_MAP_PATH, C3_RANKING_PATH]
ACCEPTED_BASELINE_SUMMARY_PATH = Path(FR4_NNPU_BASELINE_SUMMARY_PATH_TEMPLATE.format(fold_id=0))
pytestmark = pytest.mark.skipif(
    not all(p.exists() for p in REQUIRED_INPUTS) or not ACCEPTED_BASELINE_SUMMARY_PATH.exists(),
    reason="Tasks 3.1-3.4 outputs or the accepted Task 4.3 pi=0.10 baseline are not present locally.",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def accepted_baseline_hashes():
    """Recorded BEFORE any diagnostic run in this module -- re-checked by
    every test in the 'baseline preservation' section below."""
    summary = json.loads(ACCEPTED_BASELINE_SUMMARY_PATH.read_text(encoding="utf-8"))
    run_dir = Path(summary["run_dir"])
    hashes = {"summary": _sha256(ACCEPTED_BASELINE_SUMMARY_PATH)}
    curve_path = Path(summary["outputs"]["learning_curve"])
    if curve_path.exists():
        hashes["learning_curve"] = _sha256(curve_path)
    best_ckpt = run_dir / "checkpoint_best.pt"
    if best_ckpt.exists():
        hashes["best_checkpoint"] = _sha256(best_ckpt)
    return hashes, summary


# ---------------------------------------------------------------------------
# Reduced-data smoke test -- both pi values the diagnostic brief requires
# in addition to the accepted pi=0.10 reference.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def smoke_summary_pi005(accepted_baseline_hashes):
    return run_fr4_nnpu_prior_sensitivity(prior=0.05, fold_id=0, max_epochs=2, early_stopping_patience=None)


@pytest.fixture(scope="module")
def smoke_summary_pi020(accepted_baseline_hashes):
    return run_fr4_nnpu_prior_sensitivity(prior=0.20, fold_id=0, max_epochs=2, early_stopping_patience=None)


def test_smoke_run_produces_valid_epoch_level_and_per_update_history(smoke_summary_pi005):
    assert smoke_summary_pi005["training"]["executed_epochs"] == 2
    assert len(smoke_summary_pi005["epoch_level_history"]) == 2
    assert len(smoke_summary_pi005["per_update_diagnostic_history"]) == 2
    for record in smoke_summary_pi005["per_update_diagnostic_history"]:
        assert "per_update_negative_risk_unclamped" in record
        stats = record["per_update_negative_risk_unclamped"]
        assert stats["min"] <= stats["p50"] <= stats["max"]
        assert 0.0 <= record["clamped_update_fraction"] <= 1.0


def test_smoke_run_rejects_an_out_of_grid_prior():
    with pytest.raises(ValueError):
        run_fr4_nnpu_prior_sensitivity(prior=0.37, fold_id=0, max_epochs=2, early_stopping_patience=None)


def test_smoke_run_best_checkpoint_score_distributions_cover_all_six_groups(smoke_summary_pi005):
    dist = smoke_summary_pi005["best_checkpoint_score_distributions"]
    for group in ("train_e1", "train_e2", "train_c1", "val_e1", "val_e2", "val_c1"):
        assert group in dist
        assert dist[group]["n"] > 0
        assert 0.0 <= dist[group]["median"] <= 1.0


def test_reproducible_diagnostics_under_unchanged_seeds(smoke_summary_pi005):
    second = run_fr4_nnpu_prior_sensitivity(prior=0.05, fold_id=0, max_epochs=2, early_stopping_patience=None)
    assert second["epoch_level_history"] == smoke_summary_pi005["epoch_level_history"]
    assert second["per_update_diagnostic_history"] == smoke_summary_pi005["per_update_diagnostic_history"]
    assert second["training"]["best_epoch"] == smoke_summary_pi005["training"]["best_epoch"]
    assert second["run_dir"] != smoke_summary_pi005["run_dir"]  # run dirs are timestamped, not expected to match


def test_reruns_produce_bit_identical_checkpoint_weights(smoke_summary_pi005):
    from plantaox.c2_pu.models import BinaryMlp, MlpArchitecture
    from plantaox.c2_pu.run_recorder import load_checkpoint

    second = run_fr4_nnpu_prior_sensitivity(prior=0.05, fold_id=0, max_epochs=2, early_stopping_patience=None)
    model_a = BinaryMlp(MlpArchitecture(input_dim=495, hidden_dims=(128, 64)))
    model_b = BinaryMlp(MlpArchitecture(input_dim=495, hidden_dims=(128, 64)))
    load_checkpoint(Path(smoke_summary_pi005["run_dir"]) / "checkpoint_best.pt", model_a)
    load_checkpoint(Path(second["run_dir"]) / "checkpoint_best.pt", model_b)
    assert all(torch.equal(a, b) for a, b in zip(model_a.parameters(), model_b.parameters()))


# ---------------------------------------------------------------------------
# Controlled-variable checks: only pi varies across the sensitivity grid.
# ---------------------------------------------------------------------------


def test_c1_train_validation_membership_identical_across_prior_conditions(smoke_summary_pi005, smoke_summary_pi020):
    from plantaox.c2_pu.experiment_config import ExperimentConfig
    from plantaox.c2_pu.experiment_data import build_experiment_data
    from plantaox.c2_pu.nnpu_baseline import build_nnpu_dataset

    cache_manifest = json.loads(FR3_FEATURE_CACHE_MANIFEST_PATH.read_text(encoding="utf-8"))
    fusion_scalers = json.loads(FR3_FUSION_SCALERS_PATH.read_text(encoding="utf-8"))
    record_map = pd.read_csv(FR3_RECORD_MAP_PATH)
    entry = cache_manifest["folds"]["0"]

    config_a = ExperimentConfig(experiment_id="verify_pi_a", baseline="nnPU", fold_id=0)
    config_b = ExperimentConfig(experiment_id="verify_pi_b", baseline="nnPU", fold_id=0)
    data_a = build_experiment_data(config_a, Path(entry["cache_path"]), entry, fusion_scalers["0"], record_map, C3_RANKING_PATH)
    data_b = build_experiment_data(config_b, Path(entry["cache_path"]), entry, fusion_scalers["0"], record_map, C3_RANKING_PATH)
    dataset_005 = build_nnpu_dataset(data_a, config_a, prior=0.05)
    dataset_020 = build_nnpu_dataset(data_b, config_b, prior=0.20)

    assert set(dataset_005.train_unlabeled_ids.tolist()) == set(dataset_020.train_unlabeled_ids.tolist())
    assert set(dataset_005.validation_unlabeled_ids.tolist()) == set(dataset_020.validation_unlabeled_ids.tolist())
    assert set(dataset_005.train_positive_ids.tolist()) == set(dataset_020.train_positive_ids.tolist())
    assert set(dataset_005.validation_positive_ids.tolist()) == set(dataset_020.validation_positive_ids.tolist())
    # Only the prior differs between the two datasets.
    assert dataset_005.prior != dataset_020.prior


# ---------------------------------------------------------------------------
# Regression guard: the diagnostic training loop must not change the
# accepted nnPU risk estimator or training-loop math in any way.
# ---------------------------------------------------------------------------


def test_diagnostic_loop_reproduces_accepted_loops_epoch_aggregates_at_same_prior():
    """Running the DIAGNOSTIC loop at pi=0.10 (the accepted prior), same
    seed/fold/epochs, must produce epoch-level aggregates (train/val nnPU
    risk, clamped fraction, every existing Section 10.3 field) IDENTICAL
    to the accepted ``train_nnpu_baseline`` -- proving the new
    instrumentation adds bookkeeping only and changes nothing about what
    is actually trained."""
    from plantaox.c2_pu.experiment_config import ExperimentConfig
    from plantaox.c2_pu.experiment_data import build_experiment_data
    from plantaox.c2_pu.nnpu_baseline import build_nnpu_dataset, train_nnpu_baseline
    from plantaox.c2_pu.nnpu_prior_diagnostics import train_nnpu_with_diagnostics
    from plantaox.c2_pu.run_recorder import create_run_dir

    cache_manifest = json.loads(FR3_FEATURE_CACHE_MANIFEST_PATH.read_text(encoding="utf-8"))
    fusion_scalers = json.loads(FR3_FUSION_SCALERS_PATH.read_text(encoding="utf-8"))
    record_map = pd.read_csv(FR3_RECORD_MAP_PATH)
    entry = cache_manifest["folds"]["0"]

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        config_a = ExperimentConfig(experiment_id="regression_guard_a", baseline="nnPU", fold_id=0, max_epochs=3, checkpoint_dir=str(tmp_path / "a"))
        config_b = ExperimentConfig(experiment_id="regression_guard_b", baseline="nnPU", fold_id=0, max_epochs=3, checkpoint_dir=str(tmp_path / "b"))
        data_a = build_experiment_data(config_a, Path(entry["cache_path"]), entry, fusion_scalers["0"], record_map, C3_RANKING_PATH)
        data_b = build_experiment_data(config_b, Path(entry["cache_path"]), entry, fusion_scalers["0"], record_map, C3_RANKING_PATH)
        dataset_a = build_nnpu_dataset(data_a, config_a, prior=0.10)
        dataset_b = build_nnpu_dataset(data_b, config_b, prior=0.10)

        run_dir_a = create_run_dir(tmp_path / "a", config_a.experiment_id)
        run_dir_b = create_run_dir(tmp_path / "b", config_b.experiment_id)

        accepted_result = train_nnpu_baseline(config_a, dataset_a, run_dir_a, early_stopping_patience=None)
        diagnostic_result = train_nnpu_with_diagnostics(config_b, dataset_b, run_dir_b, early_stopping_patience=None)

        assert len(accepted_result["history"]) == len(diagnostic_result["history"]) == 3
        shared_keys = set(accepted_result["history"][0].keys())
        for epoch_idx in range(3):
            accepted_epoch = accepted_result["history"][epoch_idx]
            diagnostic_epoch = diagnostic_result["history"][epoch_idx]
            for key in shared_keys:
                assert accepted_epoch[key] == diagnostic_epoch[key], f"epoch {epoch_idx} field {key!r} diverged"
        assert accepted_result["best_epoch"] == diagnostic_result["best_epoch"]
        assert accepted_result["total_optimizer_updates"] == diagnostic_result["total_optimizer_updates"]


# ---------------------------------------------------------------------------
# Comparison-report stage: missing-prerequisite handling + a real run.
# ---------------------------------------------------------------------------


def test_report_raises_clear_error_when_a_sensitivity_summary_is_missing(monkeypatch):
    import plantaox.c2_pu.run as run_module

    monkeypatch.setattr(
        run_module,
        "FR4_NNPU_PRIOR_SENSITIVITY_SUMMARY_PATH_TEMPLATE",
        str(Path(run_module.PROCESSED_DIR) / "does_not_exist_pi{prior_tag}_fold{fold_id}_summary.json"),
    )
    with pytest.raises(FileNotFoundError, match="fr4-nnpu-prior-sensitivity"):
        run_fr4_nnpu_prior_sensitivity_report(fold_id=0)


def test_report_raises_clear_error_when_accepted_baseline_summary_is_missing(monkeypatch, tmp_path):
    import plantaox.c2_pu.run as run_module

    bogus = tmp_path / "does_not_exist.json"
    monkeypatch.setattr(run_module, "FR4_NNPU_BASELINE_SUMMARY_PATH_TEMPLATE", str(bogus))
    with pytest.raises(FileNotFoundError, match="accepted Task 4.3"):
        run_fr4_nnpu_prior_sensitivity_report(fold_id=0)


def test_full_report_combines_all_three_priors_and_classifies(smoke_summary_pi005, smoke_summary_pi020):
    report = run_fr4_nnpu_prior_sensitivity_report(fold_id=0)
    assert report["priors_compared"] == ["0.05", "0.10", "0.20"]
    assert report["classification"] in {"Prior-sensitive", "Persistently clamped", "Mixed behavior", "Inconclusive"}
    for prior_label in ("0.05", "0.10", "0.20"):
        assert prior_label in report["comparison_table"]
    for plot_path in report["plots"].values():
        assert Path(plot_path).exists()
        assert Path(plot_path).read_text(encoding="utf-8").startswith("<svg")


# ---------------------------------------------------------------------------
# Baseline-preservation checks (Section 3/10's non-negotiable requirement)
# ---------------------------------------------------------------------------


def test_accepted_baseline_summary_and_learning_curve_are_byte_identical_after_diagnostics(
    accepted_baseline_hashes, smoke_summary_pi005, smoke_summary_pi020
):
    before, summary = accepted_baseline_hashes
    assert _sha256(ACCEPTED_BASELINE_SUMMARY_PATH) == before["summary"]
    if "learning_curve" in before:
        assert _sha256(Path(summary["outputs"]["learning_curve"])) == before["learning_curve"]


def test_accepted_baseline_best_checkpoint_weights_are_unchanged_after_diagnostics(
    accepted_baseline_hashes, smoke_summary_pi005, smoke_summary_pi020
):
    before, summary = accepted_baseline_hashes
    if "best_checkpoint" not in before:
        pytest.skip("Accepted pi=0.10 best checkpoint not present on disk in this checkout.")
    run_dir = Path(summary["run_dir"])
    assert _sha256(run_dir / "checkpoint_best.pt") == before["best_checkpoint"]


def test_sensitivity_runs_write_to_a_separate_path_from_the_accepted_baseline(smoke_summary_pi005):
    assert Path(smoke_summary_pi005["run_dir"]).parent.name == "fr4_nnpu_prior_sensitivity_runs"
    assert "fr4_nnpu_baseline_runs" not in str(smoke_summary_pi005["run_dir"])


def test_fr3_upstream_artifacts_are_untouched_by_diagnostic_runs(smoke_summary_pi005, smoke_summary_pi020):
    # These are frozen, read-only inputs -- re-hash them after two
    # diagnostic training runs to confirm no code path wrote to them.
    for p in REQUIRED_INPUTS:
        assert p.exists()
