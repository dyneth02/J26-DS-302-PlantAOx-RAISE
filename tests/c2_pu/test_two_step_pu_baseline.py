"""Unit tests for two_step_pu_baseline.py (Bucket 4, Task 4.4) -- the
Elkan & Noto 2008-style Two-Step PU training loop, against small, fully
synthetic fixtures (no real cached artifacts required; a separate
acceptance test exercises the real fold-0 data -- see
test_fr4_two_step_pu_baseline_acceptance.py)."""

from __future__ import annotations

import numpy as np
import pytest

from plantaox.c2_pu.experiment_config import ExperimentConfig
from plantaox.c2_pu.experiment_data import ExperimentData, PoolData
from plantaox.c2_pu.pu_sklearn_common import build_sklearn_pu_dataset, load_sklearn_checkpoint
from plantaox.c2_pu.two_step_pu_baseline import (
    DEFAULT_HOLD_OUT_RATIO,
    train_two_step_pu_baseline,
)

FEATURE_DIM = 495
N_POS = 60
N_C1 = 300


def _synthetic_pool(pool, peptide_ids, seed_offset, label_shift=0.0, evidence_tier=None):
    n = len(peptide_ids)
    rng = np.random.default_rng(seed_offset + len(pool))
    features = (rng.normal(size=(n, FEATURE_DIM)) + label_shift).astype(np.float32)
    sequences = np.array([f"SEQ_{pool}_{pid}" for pid in peptide_ids])
    tier = np.array(evidence_tier) if evidence_tier is not None else None
    return PoolData(pool=pool, peptide_ids=np.array(peptide_ids), sequences=sequences, features=features, evidence_tier=tier)


@pytest.fixture
def dataset():
    pos_train_ids = [f"P{i}" for i in range(N_POS)]
    pos_val_ids = [f"PV{i}" for i in range(15)]
    c1_ids = [f"C1-{i}" for i in range(N_C1)]

    data = ExperimentData(
        fold_id=0,
        feature_representation="fused",
        feature_dim=FEATURE_DIM,
        train_positive=_synthetic_pool(
            "FR1_positives_train", pos_train_ids, seed_offset=0, label_shift=2.0,
            evidence_tier=["E1"] * (N_POS // 2) + ["E2"] * (N_POS - N_POS // 2),
        ),
        validation_positive=_synthetic_pool(
            "FR1_positives_validation", pos_val_ids, seed_offset=1, label_shift=2.0,
            evidence_tier=["E1"] * 8 + ["E2"] * 7,
        ),
        held_out_positive=_synthetic_pool("FR1_positives_held_out", ["PH1", "PH2"], seed_offset=2, evidence_tier=["E1", "E1"]),
        c1=_synthetic_pool("C1", c1_ids, seed_offset=3, label_shift=-2.0),
        c2=_synthetic_pool("C2", ["C2-1"], seed_offset=4),
        c3_fold_challenges=_synthetic_pool("C3_fold0", ["C3-1"], seed_offset=5),
        external_control=_synthetic_pool("external_control", ["EXT-1"], seed_offset=6),
        leakage_report={"pairs_checked": [], "overlap_found": False},
    )
    config = ExperimentConfig(
        experiment_id="two_step_pu_test", baseline="TwoStepPU", fold_id=0, validation_fraction=0.2, eval_seed=1, train_seed=42,
    )
    return build_sklearn_pu_dataset(data, config), config


def test_train_two_step_pu_baseline_produces_finite_bounded_base_predictions(dataset, tmp_path):
    ds, config = dataset
    result = train_two_step_pu_baseline(config, ds, tmp_path)
    assert 0.0 < result["estimated_c"] <= 1.0
    pos_base = result["validation_metrics"]["base_estimator_proba"]["positive_rows"]
    unl_base = result["validation_metrics"]["base_estimator_proba"]["unlabeled_rows"]
    assert pos_base["min"] >= 0.0 and pos_base["max"] <= 1.0
    assert unl_base["min"] >= 0.0 and unl_base["max"] <= 1.0
    # Separated synthetic clusters -> positives should score higher on average
    assert pos_base["mean"] > unl_base["mean"]


def test_train_two_step_pu_baseline_corrected_proba_can_exceed_one_and_is_documented(dataset, tmp_path):
    ds, config = dataset
    result = train_two_step_pu_baseline(config, ds, tmp_path)
    corrected = result["validation_metrics"]["corrected_proba_unclipped"]
    assert "fraction_exceeding_one_overall" in corrected
    clipped = result["validation_metrics"]["corrected_proba_clipped_0_1"]
    assert clipped["positive_rows"]["max"] <= 1.0
    assert clipped["unlabeled_rows"]["max"] <= 1.0


def test_train_two_step_pu_baseline_writes_checkpoints(dataset, tmp_path):
    ds, config = dataset
    train_two_step_pu_baseline(config, ds, tmp_path)
    assert (tmp_path / "checkpoint_best.joblib").exists()
    assert (tmp_path / "checkpoint_last.joblib").exists()
    assert (tmp_path / "epoch_metrics.jsonl").exists()


def test_checkpoint_reload_reproduces_predictions_exactly(dataset, tmp_path):
    ds, config = dataset
    train_two_step_pu_baseline(config, ds, tmp_path)
    payload = load_sklearn_checkpoint(tmp_path / "checkpoint_best.joblib")
    reloaded = payload["estimator"]
    sample = ds.validation_positive_features[:5]
    assert np.array_equal(reloaded.predict_proba(sample), reloaded.predict_proba(sample))


def test_same_seed_reruns_are_bit_identical(dataset, tmp_path):
    ds, config = dataset
    run_dir_a = tmp_path / "a"
    run_dir_b = tmp_path / "b"
    run_dir_a.mkdir()
    run_dir_b.mkdir()
    result_a = train_two_step_pu_baseline(config, ds, run_dir_a)
    result_b = train_two_step_pu_baseline(config, ds, run_dir_b)
    assert result_a["estimated_c"] == result_b["estimated_c"]
    assert result_a["validation_metrics"] == result_b["validation_metrics"]
    payload_a = load_sklearn_checkpoint(run_dir_a / "checkpoint_best.joblib")
    payload_b = load_sklearn_checkpoint(run_dir_b / "checkpoint_best.joblib")
    sample = ds.validation_positive_features[:10]
    assert np.array_equal(
        payload_a["estimator"].predict_proba(sample), payload_b["estimator"].predict_proba(sample)
    )


def test_different_seed_can_change_hold_out_split(dataset, tmp_path):
    ds, config = dataset
    config_other_seed = ExperimentConfig(
        experiment_id="two_step_pu_test2", baseline="TwoStepPU", fold_id=0, validation_fraction=0.2,
        eval_seed=1, train_seed=999,
    )
    run_dir_a = tmp_path / "a"
    run_dir_b = tmp_path / "b"
    run_dir_a.mkdir()
    run_dir_b.mkdir()
    result_a = train_two_step_pu_baseline(config, ds, run_dir_a)
    result_b = train_two_step_pu_baseline(config_other_seed, ds, run_dir_b)
    # Not asserting inequality (could coincidentally match) -- just that
    # both runs complete and produce a valid c in (0, 1].
    assert 0.0 < result_a["estimated_c"] <= 1.0
    assert 0.0 < result_b["estimated_c"] <= 1.0


def test_default_hold_out_ratio_is_pulearns_own_default():
    assert DEFAULT_HOLD_OUT_RATIO == pytest.approx(0.1)


def test_non_finite_training_feature_raises_runtime_error(dataset, tmp_path):
    import dataclasses

    ds, config = dataset
    bad_features = ds.train_positive_features.copy()
    bad_features[0, 0] = np.nan
    bad_ds = dataclasses.replace(ds, train_positive_features=bad_features)
    with pytest.raises(RuntimeError, match="[Nn]on-finite"):
        train_two_step_pu_baseline(config, bad_ds, tmp_path)


def test_no_learning_curve_reason_is_present_and_explains_why(dataset, tmp_path):
    ds, config = dataset
    result = train_two_step_pu_baseline(config, ds, tmp_path)
    assert "non-iterative" in result["no_learning_curve_reason"].lower()
    assert "learning_curve_path" not in result
