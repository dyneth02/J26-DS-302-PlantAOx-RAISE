"""Unit tests for pu_bagging_baseline.py (Bucket 4, Task 4.4) -- the
Mordelet & Vert 2014-style PU-Bagging training loop, against small, fully
synthetic fixtures (no real cached artifacts required; a separate
acceptance test exercises the real fold-0 data -- see
test_fr4_pu_bagging_baseline_acceptance.py)."""

from __future__ import annotations

import numpy as np
import pytest

from plantaox.c2_pu.experiment_config import ExperimentConfig
from plantaox.c2_pu.experiment_data import ExperimentData, PoolData
from plantaox.c2_pu.pu_bagging_baseline import (
    DEFAULT_MAX_SAMPLES,
    DEFAULT_N_ESTIMATORS,
    train_pu_bagging_baseline,
)
from plantaox.c2_pu.pu_sklearn_common import build_sklearn_pu_dataset, load_sklearn_checkpoint

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
        experiment_id="pu_bagging_test", baseline="PUBagging", fold_id=0, validation_fraction=0.2, eval_seed=1, train_seed=42,
    )
    return build_sklearn_pu_dataset(data, config), config


def test_train_pu_bagging_baseline_produces_finite_bounded_predictions(dataset, tmp_path):
    ds, config = dataset
    result = train_pu_bagging_baseline(config, ds, tmp_path, n_estimators=15)
    val = result["validation_metrics"]
    for side in ("positive_rows", "unlabeled_rows"):
        assert val[side]["min"] >= 0.0
        assert val[side]["max"] <= 1.0
    assert val["positive_rows"]["mean"] > val["unlabeled_rows"]["mean"]


def test_oob_score_is_finite_and_in_unit_interval(dataset, tmp_path):
    ds, config = dataset
    result = train_pu_bagging_baseline(config, ds, tmp_path, n_estimators=15)
    oob = result["oob_metrics"]
    assert np.isfinite(oob["oob_score"])
    assert 0.0 <= oob["oob_score"] <= 1.0


def test_all_positive_rows_are_never_out_of_bag_by_design(dataset, tmp_path):
    # Mordelet & Vert's procedure keeps every labeled positive in EVERY
    # bootstrap member (only C1-unlabeled rows are bootstrap-resampled),
    # so positives structurally have zero valid OOB observations -- a
    # documented property, not a bug (see the module docstring).
    ds, config = dataset
    result = train_pu_bagging_baseline(config, ds, tmp_path, n_estimators=15)
    oob = result["oob_metrics"]
    n_train_positive = ds.e1_train_count + ds.e2_train_count
    assert oob["n_rows_never_out_of_bag"] == n_train_positive
    assert oob["positive_rows"]["n"] == 0


def test_train_pu_bagging_baseline_writes_checkpoints(dataset, tmp_path):
    ds, config = dataset
    train_pu_bagging_baseline(config, ds, tmp_path, n_estimators=15)
    assert (tmp_path / "checkpoint_best.joblib").exists()
    assert (tmp_path / "checkpoint_last.joblib").exists()
    assert (tmp_path / "epoch_metrics.jsonl").exists()


def test_checkpoint_reload_reproduces_predictions_exactly(dataset, tmp_path):
    ds, config = dataset
    train_pu_bagging_baseline(config, ds, tmp_path, n_estimators=15)
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
    result_a = train_pu_bagging_baseline(config, ds, run_dir_a, n_estimators=15)
    result_b = train_pu_bagging_baseline(config, ds, run_dir_b, n_estimators=15)
    assert result_a["oob_metrics"]["oob_score"] == result_b["oob_metrics"]["oob_score"]
    assert result_a["validation_metrics"] == result_b["validation_metrics"]
    payload_a = load_sklearn_checkpoint(run_dir_a / "checkpoint_best.joblib")
    payload_b = load_sklearn_checkpoint(run_dir_b / "checkpoint_best.joblib")
    sample = ds.validation_positive_features[:10]
    assert np.array_equal(
        payload_a["estimator"].predict_proba(sample), payload_b["estimator"].predict_proba(sample)
    )


def test_defaults_match_documented_values():
    assert DEFAULT_N_ESTIMATORS == 100
    assert DEFAULT_MAX_SAMPLES == pytest.approx(1.0)


def test_non_finite_training_feature_raises_runtime_error(dataset, tmp_path):
    import dataclasses

    ds, config = dataset
    bad_features = ds.train_unlabeled_features.copy()
    bad_features[0, 0] = np.inf
    bad_ds = dataclasses.replace(ds, train_unlabeled_features=bad_features)
    with pytest.raises(RuntimeError, match="[Nn]on-finite"):
        train_pu_bagging_baseline(config, bad_ds, tmp_path, n_estimators=15)


def test_no_learning_curve_reason_is_present_and_explains_why(dataset, tmp_path):
    ds, config = dataset
    result = train_pu_bagging_baseline(config, ds, tmp_path, n_estimators=15)
    assert "non-iterative" in result["no_learning_curve_reason"].lower()
    assert "learning_curve_path" not in result
