"""Unit tests for pu_sklearn_common.py (Bucket 4, Task 4.4) -- shared
dataset assembly, leakage checks, and the sklearn-estimator checkpoint
helper, all against small, fully synthetic fixtures (no real cached
artifacts required; separate acceptance tests exercise the real fold-0
data -- see test_fr4_two_step_pu_baseline_acceptance.py /
test_fr4_pu_bagging_baseline_acceptance.py).

Deliberately does NOT import torch directly -- confirms (via a dedicated
test below) that this module's own import graph stays torch-free, same
discipline as pn_baseline.py's/nnpu_baseline.py's dataset-construction
halves.
"""

from __future__ import annotations

import sys

import numpy as np
import pytest

from plantaox.c2_pu.experiment_config import ExperimentConfig
from plantaox.c2_pu.experiment_data import DataLeakageError, ExperimentData, PoolData
from plantaox.c2_pu.pn_baseline import InsufficientDataError
from plantaox.c2_pu.pu_sklearn_common import (
    SklearnPuDataset,
    build_sklearn_pu_dataset,
    combined_fit_arrays,
    load_sklearn_checkpoint,
    save_sklearn_checkpoint,
    score_distribution_summary,
    select_e1_e2_positive_evidence,
)

FEATURE_DIM = 495


def _pool(pool, peptide_ids, seed_offset=0, evidence_tier=None):
    n = len(peptide_ids)
    rng = np.random.default_rng(seed_offset + len(pool))
    features = rng.normal(size=(n, FEATURE_DIM)).astype(np.float32)
    sequences = np.array([f"SEQ_{pool}_{pid}" for pid in peptide_ids])
    tier = np.array(evidence_tier) if evidence_tier is not None else None
    return PoolData(pool=pool, peptide_ids=np.array(peptide_ids), sequences=sequences, features=features, evidence_tier=tier)


def _experiment_data(
    train_ids=("P1", "P2", "P3", "P4", "P5"),
    train_tiers=("E1", "E1", "E2", "E2", "E3"),
    val_ids=("P6", "P7", "P8"),
    val_tiers=("E1", "E2", "E3"),
    held_out_ids=("P9", "P10"),
    c1_ids=tuple(f"C1-{i}" for i in range(20)),
    c2_ids=("C2-1",),
    c3_ids=("C3-1",),
    ext_ids=("EXT-1",),
    fold_id=0,
):
    return ExperimentData(
        fold_id=fold_id,
        feature_representation="fused",
        feature_dim=FEATURE_DIM,
        train_positive=_pool("FR1_positives_train", train_ids, evidence_tier=train_tiers),
        validation_positive=_pool("FR1_positives_validation", val_ids, seed_offset=1, evidence_tier=val_tiers),
        held_out_positive=_pool("FR1_positives_held_out", held_out_ids, seed_offset=2, evidence_tier=["E1"] * len(held_out_ids)),
        c1=_pool("C1", c1_ids, seed_offset=3),
        c2=_pool("C2", c2_ids, seed_offset=4),
        c3_fold_challenges=_pool(f"C3_fold{fold_id}", c3_ids, seed_offset=5),
        external_control=_pool("external_control", ext_ids, seed_offset=6),
        leakage_report={"pairs_checked": [], "overlap_found": False},
    )


def _config(**overrides):
    base = {"experiment_id": "pu_sklearn_test", "baseline": "TwoStepPU", "fold_id": 0, "validation_fraction": 0.2, "eval_seed": 1}
    base.update(overrides)
    return ExperimentConfig(**base)


# ---------------------------------------------------------------------------
# Module import graph stays torch-free
# ---------------------------------------------------------------------------


def test_module_import_graph_is_torch_free():
    import os
    import subprocess
    from pathlib import Path

    src_dir = str(Path(__file__).resolve().parents[2] / "src")
    env = dict(os.environ)
    env["PYTHONPATH"] = src_dir + os.pathsep + env.get("PYTHONPATH", "")
    result = subprocess.run(
        [sys.executable, "-c", "import sys; import plantaox.c2_pu.pu_sklearn_common; print('torch' in sys.modules)"],
        capture_output=True, text=True, env=env,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "False"


# ---------------------------------------------------------------------------
# select_e1_e2_positive_evidence: equivalence with nnpu_baseline's own
# function of the same name (duplicated here to avoid a transitive torch
# import -- see pu_sklearn_common.py's module-level comment).
# ---------------------------------------------------------------------------


def test_select_e1_e2_positive_evidence_keeps_e1_and_e2():
    pool = _pool("FR1_positives_train", ["P1", "P2", "P3"], evidence_tier=["E1", "E2", "E3"])
    selected = select_e1_e2_positive_evidence(pool)
    assert set(selected.peptide_ids.tolist()) == {"P1", "P2"}
    assert set(selected.evidence_tier.tolist()) == {"E1", "E2"}


def test_select_e1_e2_positive_evidence_raises_without_evidence_info():
    pool = _pool("C1", ["C1-1", "C1-2"])
    with pytest.raises(ValueError, match="evidence_tier"):
        select_e1_e2_positive_evidence(pool)


def test_select_e1_e2_positive_evidence_matches_nnpu_baseline_implementation():
    from plantaox.c2_pu.nnpu_baseline import select_e1_e2_positive_evidence as nnpu_select

    pool = _pool("FR1_positives_train", ["P1", "P2", "P3", "P4"], evidence_tier=["E1", "E2", "E3", "E1"])
    local_result = select_e1_e2_positive_evidence(pool)
    nnpu_result = nnpu_select(pool)
    assert local_result.peptide_ids.tolist() == nnpu_result.peptide_ids.tolist()
    assert local_result.evidence_tier.tolist() == nnpu_result.evidence_tier.tolist()
    assert np.array_equal(local_result.features, nnpu_result.features)


# ---------------------------------------------------------------------------
# build_sklearn_pu_dataset: E1+E2 positive, C1-only unlabeled, leakage
# checks, identical C1 partition to PN/nnPU
# ---------------------------------------------------------------------------


def test_build_sklearn_pu_dataset_includes_e1_and_e2_excludes_e3():
    data = _experiment_data()
    dataset = build_sklearn_pu_dataset(data, _config())
    assert set(dataset.train_positive_ids.tolist()) == {"P1", "P2", "P3", "P4"}
    assert set(dataset.validation_positive_ids.tolist()) == {"P6", "P7"}
    assert dataset.e1_train_count == 2
    assert dataset.e2_train_count == 2
    assert dataset.e1_validation_count == 1
    assert dataset.e2_validation_count == 1


def test_build_sklearn_pu_dataset_c1_partition_matches_pn_shared_splitter():
    from plantaox.c2_pu.pn_baseline import split_c1_train_validation

    data = _experiment_data()
    config = _config()
    dataset = build_sklearn_pu_dataset(data, config)
    expected_train, expected_validation = split_c1_train_validation(data.c1, config.validation_fraction, config.eval_seed)
    assert set(dataset.train_unlabeled_ids.tolist()) == set(expected_train.peptide_ids.tolist())
    assert set(dataset.validation_unlabeled_ids.tolist()) == set(expected_validation.peptide_ids.tolist())


def test_build_sklearn_pu_dataset_has_no_binary_label_field_for_c1():
    # Structural guarantee: C1 is never assigned a binary label anywhere
    # in this dataclass (mirrors NnPuDataset's own discipline).
    assert not hasattr(SklearnPuDataset, "train_unlabeled_labels")
    assert "train_unlabeled_labels" not in SklearnPuDataset.__dataclass_fields__


def test_build_sklearn_pu_dataset_raises_on_zero_positives():
    data = _experiment_data(train_ids=("P1",), train_tiers=("E3",))
    with pytest.raises(InsufficientDataError):
        build_sklearn_pu_dataset(data, _config())


def test_build_sklearn_pu_dataset_raises_on_zero_c1_rows():
    data = _experiment_data(c1_ids=())
    with pytest.raises(InsufficientDataError):
        build_sklearn_pu_dataset(data, _config())


def test_build_sklearn_pu_dataset_catches_injected_cross_pool_leakage():
    data = _experiment_data(c2_ids=("P1",))  # P1 is also a training positive id
    with pytest.raises(DataLeakageError):
        build_sklearn_pu_dataset(data, _config())


def test_build_sklearn_pu_dataset_catches_injected_sequence_leakage():
    # Same sequence under a different peptide_id across two subsets.
    # Built from scratch (not via in-place numpy-string mutation, which
    # silently truncates to the original fixed-width dtype's length and
    # would not actually reproduce the leak).
    import dataclasses

    data = _experiment_data()
    leaked_sequence = str(data.train_positive.sequences[0])
    leaked_c2 = PoolData(
        pool="C2",
        peptide_ids=data.c2.peptide_ids,
        sequences=np.array([leaked_sequence]),
        features=data.c2.features,
        evidence_tier=data.c2.evidence_tier,
    )
    data = dataclasses.replace(data, c2=leaked_c2)
    with pytest.raises(DataLeakageError):
        build_sklearn_pu_dataset(data, _config())


# ---------------------------------------------------------------------------
# combined_fit_arrays: label encoding
# ---------------------------------------------------------------------------


def test_combined_fit_arrays_train_split_encodes_positive_as_one_unlabeled_as_zero():
    data = _experiment_data()
    dataset = build_sklearn_pu_dataset(data, _config())
    x, y, ids = combined_fit_arrays(dataset, "train")
    n_pos = dataset.e1_train_count + dataset.e2_train_count
    n_unl = dataset.train_unlabeled_features.shape[0]
    assert x.shape == (n_pos + n_unl, FEATURE_DIM)
    assert set(y.tolist()) == {0, 1}
    assert int(y[:n_pos].sum()) == n_pos  # all positives listed first
    assert int(y[n_pos:].sum()) == 0
    assert len(ids) == n_pos + n_unl


def test_combined_fit_arrays_validation_split():
    data = _experiment_data()
    dataset = build_sklearn_pu_dataset(data, _config())
    x, y, ids = combined_fit_arrays(dataset, "validation")
    n_pos = dataset.e1_validation_count + dataset.e2_validation_count
    n_unl = dataset.validation_unlabeled_features.shape[0]
    assert x.shape[0] == n_pos + n_unl
    assert int(y.sum()) == n_pos


def test_combined_fit_arrays_rejects_unknown_split():
    data = _experiment_data()
    dataset = build_sklearn_pu_dataset(data, _config())
    with pytest.raises(ValueError, match="split"):
        combined_fit_arrays(dataset, "bogus")


# ---------------------------------------------------------------------------
# score_distribution_summary
# ---------------------------------------------------------------------------


def test_score_distribution_summary_basic_stats():
    scores = np.array([0.001, 0.5, 0.999, 1.0, 0.0])
    summary = score_distribution_summary(scores)
    assert summary["n"] == 5
    assert summary["min"] == pytest.approx(0.0)
    assert summary["max"] == pytest.approx(1.0)
    assert summary["fraction_near_zero_lt_0p01"] == pytest.approx(2 / 5)
    assert summary["fraction_near_one_gt_0p99"] == pytest.approx(2 / 5)


def test_score_distribution_summary_empty_array_returns_nones():
    summary = score_distribution_summary(np.array([]))
    assert summary["n"] == 0
    assert summary["mean"] is None
    assert summary["fraction_near_zero_lt_0p01"] is None


# ---------------------------------------------------------------------------
# sklearn checkpoint save/load round-trip
# ---------------------------------------------------------------------------


def test_sklearn_checkpoint_round_trip(tmp_path):
    from sklearn.linear_model import LogisticRegression

    rng = np.random.default_rng(0)
    x = rng.normal(size=(40, 5))
    y = (x[:, 0] > 0).astype(int)
    estimator = LogisticRegression().fit(x, y)

    best_path = save_sklearn_checkpoint(tmp_path, estimator, metrics={"foo": 1}, is_best=True)
    last_path = save_sklearn_checkpoint(tmp_path, estimator, metrics={"foo": 1}, is_best=False)
    assert best_path.name == "checkpoint_best.joblib"
    assert last_path.name == "checkpoint_last.joblib"

    payload = load_sklearn_checkpoint(best_path)
    assert payload["metrics"] == {"foo": 1}
    reloaded_proba = payload["estimator"].predict_proba(x)
    original_proba = estimator.predict_proba(x)
    assert np.array_equal(reloaded_proba, original_proba)


def test_load_sklearn_checkpoint_missing_file_raises_file_not_found(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_sklearn_checkpoint(tmp_path / "does_not_exist.joblib")
