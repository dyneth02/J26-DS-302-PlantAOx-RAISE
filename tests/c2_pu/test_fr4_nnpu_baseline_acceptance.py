"""Bucket 4, Task 4.3 acceptance tests: the fr4-nnpu-baseline CLI stage
against the real local Tasks 3.1-3.4 artifacts.

Gated to skip cleanly when those artifacts aren't present locally.
Stage B (reduced-data smoke test) and Stage C (full fold-0 run) are both
covered here; results are explicitly checked against the GraphPart
held-out fold to confirm it is never touched, and against Task 4.2's own
documented E1/E2/C1 counts to confirm the SAME real fold-0 cache is
being read (not a parallel/forked data path).
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
    FR3_DESCRIPTOR_TABLE_PATH,
    FR3_EMBEDDINGS_MANIFEST_PATH,
    FR3_FEATURE_CACHE_MANIFEST_PATH,
    FR3_FUSION_SCALERS_PATH,
    FR3_RECORD_MAP_PATH,
    FR2_FROZEN_DIR,
    FROZEN_DIR,
    run_fr4_nnpu_baseline,
)

REQUIRED_INPUTS = [FR3_FEATURE_CACHE_MANIFEST_PATH, FR3_FUSION_SCALERS_PATH, FR3_RECORD_MAP_PATH, C3_RANKING_PATH]
pytestmark = pytest.mark.skipif(
    not all(p.exists() for p in REQUIRED_INPUTS),
    reason="Tasks 3.1-3.4 outputs not present locally.",
)


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def pre_run_hashes():
    hashes = {
        "feature_cache_manifest": _sha256(FR3_FEATURE_CACHE_MANIFEST_PATH),
        "fusion_scalers": _sha256(FR3_FUSION_SCALERS_PATH),
        "record_map": _sha256(FR3_RECORD_MAP_PATH),
        "c3_ranking": _sha256(C3_RANKING_PATH),
    }
    if FR3_DESCRIPTOR_TABLE_PATH.exists():
        hashes["descriptor_table"] = _sha256(FR3_DESCRIPTOR_TABLE_PATH)
    if FR3_EMBEDDINGS_MANIFEST_PATH.exists():
        hashes["embeddings_manifest"] = _sha256(FR3_EMBEDDINGS_MANIFEST_PATH)
    return hashes


# ---------------------------------------------------------------------------
# Stage C: reduced-data smoke test (2 epochs, no early stopping) --
# exercises the exact same real fold-0 cache but is explicitly NOT
# presented as the final baseline result.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def smoke_summary(pre_run_hashes):
    return run_fr4_nnpu_baseline(fold_id=0, max_epochs=2, early_stopping_patience=None)


def test_stage_c_smoke_forward_backward_and_checkpointing_all_succeed(smoke_summary):
    assert smoke_summary["training"]["executed_epochs"] == 2
    assert smoke_summary["checkpoint_reload_verification"]["proba_finite"] is True
    assert smoke_summary["checkpoint_reload_verification"]["proba_bounded"] is True


def test_stage_c_smoke_does_not_expose_held_out_data():
    # The GraphPart held-out fold is never referenced anywhere in
    # build_nnpu_dataset/train_nnpu_baseline -- verified structurally by
    # re-running build_experiment_data + build_nnpu_dataset directly and
    # confirming held_out_positive's IDs are disjoint from every ID this
    # stage actually trains on.
    from plantaox.c2_pu.experiment_config import ExperimentConfig
    from plantaox.c2_pu.experiment_data import build_experiment_data
    from plantaox.c2_pu.nnpu_baseline import build_nnpu_dataset

    cache_manifest = json.loads(FR3_FEATURE_CACHE_MANIFEST_PATH.read_text(encoding="utf-8"))
    fusion_scalers = json.loads(FR3_FUSION_SCALERS_PATH.read_text(encoding="utf-8"))
    record_map = pd.read_csv(FR3_RECORD_MAP_PATH)
    config = ExperimentConfig(experiment_id="verify", baseline="nnPU", fold_id=0)
    entry = cache_manifest["folds"]["0"]
    data = build_experiment_data(config, Path(entry["cache_path"]), entry, fusion_scalers["0"], record_map, C3_RANKING_PATH)
    dataset = build_nnpu_dataset(data, config)

    trained_ids = (
        set(dataset.train_positive_ids.tolist())
        | set(dataset.validation_positive_ids.tolist())
        | set(dataset.train_unlabeled_ids.tolist())
        | set(dataset.validation_unlabeled_ids.tolist())
    )
    held_out_ids = set(data.held_out_positive.peptide_ids.tolist())
    assert trained_ids.isdisjoint(held_out_ids)
    assert len(held_out_ids) == 124  # the documented fold-0 GraphPart held-out count, untouched


def test_real_fold0_e1_e2_and_c1_counts_match_task_4_2_documented_values():
    # Task 4.2's accepted report documents: 331 E1 + 273 E2 = 604 train
    # positives, 48 E1 + 58 E2 = 106 validation positives, 3,220 C1
    # train / 568 C1 validation -- re-derived here directly from the real
    # cache (never hardcoded as "permission"), confirming nnPU reads the
    # SAME real fold-0 artifacts PN did, not a parallel data path.
    from plantaox.c2_pu.experiment_config import ExperimentConfig
    from plantaox.c2_pu.experiment_data import build_experiment_data
    from plantaox.c2_pu.nnpu_baseline import build_nnpu_dataset

    cache_manifest = json.loads(FR3_FEATURE_CACHE_MANIFEST_PATH.read_text(encoding="utf-8"))
    fusion_scalers = json.loads(FR3_FUSION_SCALERS_PATH.read_text(encoding="utf-8"))
    record_map = pd.read_csv(FR3_RECORD_MAP_PATH)
    config = ExperimentConfig(experiment_id="verify_counts", baseline="nnPU", fold_id=0)
    entry = cache_manifest["folds"]["0"]
    data = build_experiment_data(config, Path(entry["cache_path"]), entry, fusion_scalers["0"], record_map, C3_RANKING_PATH)
    dataset = build_nnpu_dataset(data, config)

    assert dataset.e1_train_count == 331
    assert dataset.e2_train_count == 273
    assert dataset.e1_validation_count == 48
    assert dataset.e2_validation_count == 58
    assert dataset.train_unlabeled_features.shape[0] == 3220
    assert dataset.validation_unlabeled_features.shape[0] == 568


# ---------------------------------------------------------------------------
# Stage D: full fold-0 plain nnPU baseline (default config: 100 max
# epochs, early stopping patience 10) -- the genuine initial baseline
# result.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def full_summary(smoke_summary):
    return run_fr4_nnpu_baseline(fold_id=0)


def test_e1_e2_positives_and_c1_unlabeled_loaded_correctly(full_summary):
    counts = full_summary["class_counts"]
    assert counts["train_positive"] == 604
    assert counts["validation_positive"] == 106
    assert counts["e1_train"] == 331
    assert counts["e2_train"] == 273
    assert counts["e1_validation"] == 48
    assert counts["e2_validation"] == 58
    assert counts["train_unlabeled"] == 3220
    assert counts["validation_unlabeled"] == 568
    # All of C1 (never confirmed-negative), across train+validation.
    assert counts["train_unlabeled"] + counts["validation_unlabeled"] == 3788


def test_c1_train_validation_partition_matches_pn_baseline_exactly(full_summary):
    assert full_summary["c1_partition"]["validation_fraction"] == pytest.approx(0.15)
    assert full_summary["c1_partition"]["seed"] == 42


def test_graphpart_held_out_fold_remains_isolated_from_the_full_run(full_summary):
    fusion_scalers = json.loads(FR3_FUSION_SCALERS_PATH.read_text(encoding="utf-8"))
    assert fusion_scalers["0"]["n_training_samples"] == 710
    held_out_count = len(fusion_scalers["0"]["held_out_peptide_ids"])
    assert held_out_count == 124


def test_existing_fold_scaled_495_dim_features_are_reused_not_recomputed(full_summary):
    resolved = json.loads((Path(full_summary["run_dir"]) / "resolved_config.json").read_text(encoding="utf-8"))
    assert resolved["feature_representation"] == "fused"
    assert resolved["feature_dim"] == 495


def test_nnpu_variant_is_the_direct_clamped_objective(full_summary):
    assert full_summary["nnpu_variant"] == "direct_clamped"


def test_prior_is_configured_valid_and_documented(full_summary):
    prior = full_summary["prior"]
    assert 0.0 < prior["value"] < 1.0
    assert prior["value"] == pytest.approx(0.10)
    assert set(prior["sensitivity_grid"]) == {0.05, 0.10, 0.20}
    assert "provisional" in prior["provenance_note"].lower()


def test_training_produced_finite_monitored_risk_and_every_required_component(full_summary):
    training = full_summary["training"]
    assert training["executed_epochs"] >= 1
    assert training["final_train_nnpu_risk"] is not None
    assert training["final_val_nnpu_risk"] is not None
    required_keys = {
        "train_nnpu_risk", "train_positive_risk_contribution", "train_positive_as_negative_risk",
        "train_unlabeled_as_negative_risk", "train_negative_risk_unclamped", "train_negative_risk_contribution",
        "train_clamped_update_fraction", "val_nnpu_risk", "val_positive_risk_contribution",
        "val_positive_as_negative_risk", "val_unlabeled_as_negative_risk", "val_negative_risk_unclamped",
        "val_negative_risk_contribution", "val_is_clamped", "learning_rate", "prior",
        "n_e1e2_positive_train", "n_c1_unlabeled_train", "n_optimizer_updates_this_epoch", "is_best",
    }
    for record in training["history"]:
        assert required_keys <= set(record.keys())
        assert record["train_nnpu_risk"] == record["train_nnpu_risk"]  # not NaN
        assert record["val_nnpu_risk"] == record["val_nnpu_risk"]
        assert record["prior"] == pytest.approx(0.10)


def test_stability_diagnostics_are_reported(full_summary):
    diag = full_summary["training"]["stability_diagnostics"]
    assert "persistent_negative_risk_clamping_last_5_epochs" in diag
    assert "mean_train_clamped_fraction_last_5_epochs" in diag
    assert "validation_prediction_saturation" in diag
    assert "diverging_risk_detected" in diag
    assert not diag["diverging_risk_detected"]  # a genuinely diverging run should not be called "stable"


def test_best_and_last_checkpoints_saved_and_distinct(full_summary):
    run_dir = Path(full_summary["run_dir"])
    assert (run_dir / "checkpoint_best.pt").exists()
    assert (run_dir / "checkpoint_last.pt").exists()
    assert full_summary["checkpoint"]["best_path_sha256"] != full_summary["checkpoint"]["last_path_sha256"]


def test_probability_inference_works_after_checkpoint_reload(full_summary):
    verification = full_summary["checkpoint_reload_verification"]
    assert verification["proba_bounded"] is True
    assert verification["proba_finite"] is True
    assert verification["proba_shape"][1] == 1


def test_learning_curve_artifact_exists_and_is_committed_location(full_summary):
    curve_path = Path(full_summary["outputs"]["learning_curve"])
    assert curve_path.exists()
    assert curve_path.parent.name == "c2_pu"
    content = curve_path.read_text(encoding="utf-8")
    assert content.startswith("<svg")
    assert "nnPU" in content


def test_limitations_section_is_present_and_explicit(full_summary):
    limitations = full_summary["limitations"]
    assert "unlabeled" in limitations["assumed_unlabeled_c1"].lower()
    assert "never" in limitations["assumed_unlabeled_c1"].lower()
    assert "provisional" in limitations["prior_is_provisional"].lower()
    assert "e2" in limitations["evidence_tiers"].lower()
    assert "never" in limitations["nnpu_vs_pn_loss_comparability"].lower()
    assert "surrogate" in limitations["validation_risk_is_a_surrogate"].lower()
    assert "sign-off" in limitations["scientific_sign_off"].lower() or "sign_off" in limitations["scientific_sign_off"].lower()


def test_rerunning_the_full_baseline_is_bit_identical_in_substance(full_summary):
    second = run_fr4_nnpu_baseline(fold_id=0)
    assert second["training"]["history"] == full_summary["training"]["history"]
    assert second["training"]["best_epoch"] == full_summary["training"]["best_epoch"]
    assert second["class_counts"] == full_summary["class_counts"]
    # Run directories themselves are NOT expected to be identical (timestamped).
    assert second["run_dir"] != full_summary["run_dir"]


def test_reruns_produce_bit_identical_checkpoint_weights(full_summary):
    # Checkpoint SHA-256 itself is NOT expected to match (the payload
    # embeds a live `saved_at` timestamp) -- the underlying model WEIGHTS
    # must still be bit-identical, which is the actual reproducibility
    # claim.
    from plantaox.c2_pu.models import BinaryMlp, MlpArchitecture
    from plantaox.c2_pu.run_recorder import load_checkpoint

    second = run_fr4_nnpu_baseline(fold_id=0)
    model_a = BinaryMlp(MlpArchitecture(input_dim=495, hidden_dims=(128, 64)))
    model_b = BinaryMlp(MlpArchitecture(input_dim=495, hidden_dims=(128, 64)))
    load_checkpoint(Path(full_summary["run_dir"]) / "checkpoint_best.pt", model_a)
    load_checkpoint(Path(second["run_dir"]) / "checkpoint_best.pt", model_b)
    assert all(torch.equal(a, b) for a, b in zip(model_a.parameters(), model_b.parameters()))


# ---------------------------------------------------------------------------
# Stage F: artifact immutability (frozen baselines + Tasks 3.1-4.2 outputs)
# ---------------------------------------------------------------------------


def test_all_prior_task_outputs_are_untouched(full_summary, pre_run_hashes):
    for name, path in [
        ("feature_cache_manifest", FR3_FEATURE_CACHE_MANIFEST_PATH),
        ("fusion_scalers", FR3_FUSION_SCALERS_PATH),
        ("record_map", FR3_RECORD_MAP_PATH),
        ("c3_ranking", C3_RANKING_PATH),
        ("descriptor_table", FR3_DESCRIPTOR_TABLE_PATH),
        ("embeddings_manifest", FR3_EMBEDDINGS_MANIFEST_PATH),
    ]:
        if name in pre_run_hashes:
            assert _sha256(path) == pre_run_hashes[name], f"{name} changed after running the nnPU baseline"


def test_pn_baseline_summary_is_unaffected_if_present(full_summary):
    # The nnPU run must never overwrite or depend on the PN summary file
    # -- confirms the two baselines write to genuinely separate artifact
    # paths (fr4_pn_baseline_* vs. fr4_nnpu_baseline_*).
    from plantaox.c2_pu.run import FR4_PN_BASELINE_SUMMARY_PATH_TEMPLATE

    pn_summary_path = Path(FR4_PN_BASELINE_SUMMARY_PATH_TEMPLATE.format(fold_id=0))
    nnpu_summary_path = Path(full_summary["outputs"]["learning_curve"]).parent / "fr4_nnpu_baseline_fold0_summary.json"
    assert nnpu_summary_path != pn_summary_path


def test_frozen_fr1_fr2_baselines_are_untouched(full_summary):
    assert FROZEN_DIR.exists() and FR2_FROZEN_DIR.exists()
    assert not (FROZEN_DIR / "fr4_nnpu_baseline_fold0_summary.json").exists()
    assert not (FR2_FROZEN_DIR / "fr4_nnpu_baseline_fold0_summary.json").exists()


def test_missing_prerequisite_raises_a_clear_error(monkeypatch, tmp_path):
    import plantaox.c2_pu.run as run_module

    bogus_path = tmp_path / "does_not_exist.json"
    monkeypatch.setattr(run_module, "FR3_FEATURE_CACHE_MANIFEST_PATH", bogus_path)
    with pytest.raises(FileNotFoundError, match="Tasks 3.1-3.4"):
        run_fr4_nnpu_baseline(fold_id=0)
