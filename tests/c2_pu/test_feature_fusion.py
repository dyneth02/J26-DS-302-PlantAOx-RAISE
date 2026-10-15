"""Unit tests for curation/feature_fusion.py (Bucket 3.3)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from plantaox.c2_pu.common.descriptors import DESCRIPTOR_NAMES
from plantaox.c2_pu.curation.feature_fusion import (
    ESM2_DIM,
    FUSED_DIM,
    FUSED_FEATURE_NAMES,
    FeatureAlignmentError,
    apply_scaler,
    build_raw_fused_matrix,
    compute_all_fold_scalers,
    compute_fold_training_peptide_ids,
    fit_scaler,
    load_and_validate_fusion_inputs,
    peptide_id_order_sha256,
)


def _toy_descriptor_df(peptide_ids, pools):
    n = len(peptide_ids)
    rng = np.random.default_rng(0)
    data = {name: rng.normal(size=n) for name in DESCRIPTOR_NAMES}
    data["peptide_id"] = peptide_ids
    data["sequence"] = [f"SEQ{i}" for i in range(n)]
    data["pool"] = pools
    return pd.DataFrame(data)


# ---------------------------------------------------------------------------
# Schema contract
# ---------------------------------------------------------------------------


def test_fused_feature_names_has_495_entries_in_the_frozen_order():
    assert len(FUSED_FEATURE_NAMES) == FUSED_DIM == 495
    assert FUSED_FEATURE_NAMES[:ESM2_DIM] == tuple(f"esm2_{i}" for i in range(ESM2_DIM))
    assert FUSED_FEATURE_NAMES[ESM2_DIM:] == DESCRIPTOR_NAMES


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def test_validation_passes_for_consistent_inputs():
    ids = ["A", "B", "C"]
    pools = ["FR1_positives", "C1", "C2"]
    df = _toy_descriptor_df(ids, pools)
    load_and_validate_fusion_inputs(df, np.array(ids), np.array(pools))  # no raise


def test_validation_rejects_duplicate_peptide_id_in_descriptor_table():
    ids = ["A", "A", "C"]
    pools = ["FR1_positives", "FR1_positives", "C1"]
    df = _toy_descriptor_df(ids, pools)
    with pytest.raises(FeatureAlignmentError, match="duplicate"):
        load_and_validate_fusion_inputs(df, np.array(ids), np.array(pools))


def test_validation_rejects_row_count_mismatch():
    ids = ["A", "B", "C"]
    pools = ["FR1_positives", "C1", "C2"]
    df = _toy_descriptor_df(ids, pools)
    with pytest.raises(FeatureAlignmentError, match="Row count mismatch"):
        load_and_validate_fusion_inputs(df, np.array(ids[:2]), np.array(pools[:2]))


def test_validation_rejects_different_peptide_id_sets():
    ids = ["A", "B", "C"]
    pools = ["FR1_positives", "C1", "C2"]
    df = _toy_descriptor_df(ids, pools)
    with pytest.raises(FeatureAlignmentError, match="peptide_id sets differ"):
        load_and_validate_fusion_inputs(df, np.array(["A", "B", "D"]), np.array(pools))


def test_validation_rejects_same_set_different_order():
    ids = ["A", "B", "C"]
    pools = ["FR1_positives", "C1", "C2"]
    df = _toy_descriptor_df(ids, pools)
    with pytest.raises(FeatureAlignmentError, match="ROW ORDER differs"):
        load_and_validate_fusion_inputs(df, np.array(["A", "C", "B"]), np.array(pools))


def test_validation_rejects_pool_mismatch():
    ids = ["A", "B", "C"]
    pools = ["FR1_positives", "C1", "C2"]
    df = _toy_descriptor_df(ids, pools)
    with pytest.raises(FeatureAlignmentError, match="inconsistent pool assignment"):
        load_and_validate_fusion_inputs(df, np.array(ids), np.array(["FR1_positives", "C2", "C2"]))


# ---------------------------------------------------------------------------
# Concatenation
# ---------------------------------------------------------------------------


def test_build_raw_fused_matrix_concatenates_embeddings_then_descriptors_in_order():
    ids = ["A", "B"]
    pools = ["FR1_positives", "C1"]
    df = _toy_descriptor_df(ids, pools)
    embeddings = np.arange(2 * ESM2_DIM, dtype=np.float32).reshape(2, ESM2_DIM)

    fused = build_raw_fused_matrix(df, embeddings)

    assert fused.shape == (2, FUSED_DIM)
    np.testing.assert_array_equal(fused[:, :ESM2_DIM], embeddings)
    np.testing.assert_allclose(fused[:, ESM2_DIM:], df[list(DESCRIPTOR_NAMES)].to_numpy(dtype=np.float32))


# ---------------------------------------------------------------------------
# Scaler fit/apply
# ---------------------------------------------------------------------------


def test_fit_scaler_recovers_known_mean_and_std():
    rows = np.array([[1.0, 10.0], [2.0, 10.0], [3.0, 10.0]])
    scaler = fit_scaler(rows)
    np.testing.assert_allclose(scaler["mean"], [2.0, 10.0])
    # Column 0: population std of [1,2,3] = sqrt(2/3)
    assert scaler["std"][0] == pytest.approx(np.sqrt(2 / 3))
    # Column 1 is constant -> std guarded to 1.0, not 0.0
    assert scaler["std"][1] == 1.0


def test_apply_scaler_zero_variance_column_does_not_produce_nan_or_inf():
    rows = np.array([[1.0, 10.0], [2.0, 10.0], [3.0, 10.0]])
    scaler = fit_scaler(rows)
    transformed = apply_scaler(rows, scaler)
    assert np.isfinite(transformed).all()
    np.testing.assert_allclose(transformed[:, 1], [0.0, 0.0, 0.0])


def test_apply_scaler_standardizes_its_own_training_rows_to_mean_0_std_1():
    rng = np.random.default_rng(1)
    rows = rng.normal(loc=5.0, scale=2.0, size=(200, 3))
    scaler = fit_scaler(rows)
    transformed = apply_scaler(rows, scaler)
    np.testing.assert_allclose(transformed.mean(axis=0), [0, 0, 0], atol=1e-10)
    np.testing.assert_allclose(transformed.std(axis=0, ddof=0), [1, 1, 1], atol=1e-10)


def test_apply_scaler_is_transform_only_and_does_not_mutate_the_scaler():
    rows = np.array([[1.0, 2.0], [3.0, 4.0]])
    scaler = fit_scaler(rows)
    mean_before = scaler["mean"].copy()
    apply_scaler(np.array([[100.0, 200.0]]), scaler)
    np.testing.assert_array_equal(scaler["mean"], mean_before)


# ---------------------------------------------------------------------------
# Fold-safe training/held-out partitioning
# ---------------------------------------------------------------------------


def _toy_record_map():
    return pd.DataFrame(
        {
            "peptide_id": ["P0", "P1", "P2", "P3", "P4", "P5", "EXCL", "C1-1", "C2-1"],
            "pool": ["FR1_positives"] * 7 + ["C1", "C2"],
            "graphpart_fold": [0, 0, 1, 1, 2, 2, np.nan, np.nan, np.nan],
            "graphpart_retained": [True, True, True, True, True, True, False, False, False],
        }
    )


def test_compute_fold_training_peptide_ids_excludes_held_out_and_homology_excluded():
    record_map = _toy_record_map()
    training, held_out = compute_fold_training_peptide_ids(record_map, fold_id=0)
    assert set(held_out) == {"P0", "P1"}
    assert set(training) == {"P2", "P3", "P4", "P5"}
    assert "EXCL" not in training and "EXCL" not in held_out
    assert "C1-1" not in training and "C2-1" not in training


def test_compute_all_fold_scalers_training_and_held_out_never_overlap():
    record_map = _toy_record_map()
    peptide_ids = record_map["peptide_id"].tolist()
    rng = np.random.default_rng(2)
    fused_matrix = rng.normal(size=(len(peptide_ids), FUSED_DIM))

    scalers = compute_all_fold_scalers(peptide_ids, fused_matrix, record_map, n_folds=3)

    assert set(scalers.keys()) == {0, 1, 2}
    for fold_id, scaler in scalers.items():
        assert not (set(scaler["training_peptide_ids"]) & set(scaler["held_out_peptide_ids"]))
        assert "EXCL" not in scaler["training_peptide_ids"]
        assert "EXCL" not in scaler["held_out_peptide_ids"]


def test_compute_all_fold_scalers_raises_on_a_fold_with_no_training_positives():
    record_map = pd.DataFrame(
        {
            "peptide_id": ["P0"],
            "pool": ["FR1_positives"],
            "graphpart_fold": [0],
            "graphpart_retained": [True],
        }
    )
    fused_matrix = np.zeros((1, FUSED_DIM))
    with pytest.raises(ValueError, match="zero training-positive"):
        compute_all_fold_scalers(["P0"], fused_matrix, record_map, n_folds=1)


def test_peptide_id_order_sha256_is_order_sensitive():
    a = peptide_id_order_sha256(["X", "Y"])
    b = peptide_id_order_sha256(["Y", "X"])
    assert a != b
    assert a == peptide_id_order_sha256(["X", "Y"])
