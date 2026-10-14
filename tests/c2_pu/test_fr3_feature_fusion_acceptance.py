"""Bucket 3.3 acceptance tests: full-file validation of the
fr3-feature-fusion stage against the real Task 3.1/3.2 outputs.

Gated to skip cleanly when those outputs aren't present locally.
"""

from __future__ import annotations

import hashlib
import json

import numpy as np
import pandas as pd
import pytest

from plantaox.c2_pu.run import (
    FR3_DESCRIPTOR_TABLE_PATH,
    FR3_EMBEDDINGS_CACHE_PATH,
    FR3_EMBEDDINGS_MANIFEST_PATH,
    FR3_FUSED_RAW_CACHE_PATH,
    FR3_FUSION_SCALERS_PATH,
    FR3_FUSION_SCHEMA_PATH,
    FR3_FUSION_VALIDATION_REPORT_PATH,
    FR3_RECORD_MAP_PATH,
    FROZEN_DIR,
    FR2_FROZEN_DIR,
    run_fr3_feature_fusion,
)

REQUIRED_INPUTS = [FR3_DESCRIPTOR_TABLE_PATH, FR3_EMBEDDINGS_CACHE_PATH, FR3_RECORD_MAP_PATH]
pytestmark = pytest.mark.skipif(
    not all(p.exists() for p in REQUIRED_INPUTS),
    reason="Task 3.1/3.2 outputs not present locally.",
)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def pre_run_hashes():
    return {
        "descriptor_table": _sha256(FR3_DESCRIPTOR_TABLE_PATH),
        "embeddings_cache": _sha256(FR3_EMBEDDINGS_CACHE_PATH),
        "record_map": _sha256(FR3_RECORD_MAP_PATH),
    }


@pytest.fixture(scope="module")
def summary(pre_run_hashes):
    return run_fr3_feature_fusion()


def test_task_3_1_and_3_2_outputs_are_untouched_by_running_fusion(summary, pre_run_hashes):
    assert _sha256(FR3_DESCRIPTOR_TABLE_PATH) == pre_run_hashes["descriptor_table"]
    assert _sha256(FR3_EMBEDDINGS_CACHE_PATH) == pre_run_hashes["embeddings_cache"]
    assert _sha256(FR3_RECORD_MAP_PATH) == pre_run_hashes["record_map"]


def test_frozen_baselines_are_untouched(summary):
    assert FROZEN_DIR.exists()
    assert FR2_FROZEN_DIR.exists()
    assert not (FROZEN_DIR / "fr3_fused_raw.npz").exists()
    assert not (FR2_FROZEN_DIR / "fr3_fused_raw.npz").exists()


def test_fold_training_sizes_match_the_documented_graphpart_split(summary):
    assert summary["fold_training_sizes"] == {"0": 710, "1": 700, "2": 697, "3": 661, "4": 568}


def test_raw_fused_matrix_shape_and_finiteness():
    with np.load(FR3_FUSED_RAW_CACHE_PATH, allow_pickle=False) as npz:
        features = npz["features"]
        peptide_ids = npz["peptide_ids"]
        feature_names = npz["feature_names"]
    assert features.shape == (9356, 495)
    assert np.isfinite(features).all()
    assert len(peptide_ids) == 9356
    assert len(feature_names) == 495


def test_raw_fused_matrix_peptide_id_order_matches_descriptor_table_and_embeddings():
    descriptor_df = pd.read_parquet(FR3_DESCRIPTOR_TABLE_PATH)
    with np.load(FR3_FUSED_RAW_CACHE_PATH, allow_pickle=False) as npz:
        fused_ids = list(npz["peptide_ids"])
    with np.load(FR3_EMBEDDINGS_CACHE_PATH, allow_pickle=False) as npz:
        embeddings_ids = list(npz["peptide_ids"])
    assert fused_ids == descriptor_df["peptide_id"].tolist() == embeddings_ids


def test_peptide_id_order_sha256_matches_task_3_2s_manifest(summary):
    embeddings_manifest = json.loads(FR3_EMBEDDINGS_MANIFEST_PATH.read_text(encoding="utf-8"))
    fusion_validation = json.loads(FR3_FUSION_VALIDATION_REPORT_PATH.read_text(encoding="utf-8"))
    assert fusion_validation["peptide_id_order_sha256"] == embeddings_manifest["peptide_id_order_sha256"]


def test_embedding_columns_of_fused_matrix_match_the_embeddings_cache_exactly():
    with np.load(FR3_FUSED_RAW_CACHE_PATH, allow_pickle=False) as npz:
        fused_embedding_block = npz["features"][:, :480]
    with np.load(FR3_EMBEDDINGS_CACHE_PATH, allow_pickle=False) as npz:
        embeddings = npz["embeddings"]
    np.testing.assert_array_equal(fused_embedding_block, embeddings)


def test_descriptor_columns_of_fused_matrix_match_the_descriptor_table_exactly():
    from plantaox.c2_pu.common.descriptors import DESCRIPTOR_NAMES

    descriptor_df = pd.read_parquet(FR3_DESCRIPTOR_TABLE_PATH)
    with np.load(FR3_FUSED_RAW_CACHE_PATH, allow_pickle=False) as npz:
        fused_descriptor_block = npz["features"][:, 480:]
    expected = descriptor_df[list(DESCRIPTOR_NAMES)].to_numpy(dtype=np.float32)
    np.testing.assert_array_equal(fused_descriptor_block, expected)


def test_no_fold_has_training_held_out_overlap_or_unlabeled_pool_contamination(summary):
    scalers = json.loads(FR3_FUSION_SCALERS_PATH.read_text(encoding="utf-8"))
    record_map = pd.read_csv(FR3_RECORD_MAP_PATH)
    fr1_ids = set(record_map[record_map["pool"] == "FR1_positives"]["peptide_id"])
    for fold_id, scaler in scalers.items():
        training = set(scaler["training_peptide_ids"])
        held_out = set(scaler["held_out_peptide_ids"])
        assert not (training & held_out), f"fold {fold_id} has training/held-out overlap"
        assert training <= fr1_ids and held_out <= fr1_ids, f"fold {fold_id} training/held-out set contains a non-FR1-positive peptide_id"
        assert len(training) + len(held_out) == 834, f"fold {fold_id}: training+held-out should total the 834 GraphPart-retained positives"


def test_each_folds_scaler_standardizes_its_own_training_rows_to_mean_0_std_1():
    validation = json.loads(FR3_FUSION_VALIDATION_REPORT_PATH.read_text(encoding="utf-8"))
    for fold_id, stats in validation["per_fold"].items():
        assert stats["training_rows_transformed_mean_abs_max"] < 1e-3, f"fold {fold_id} training mean not ~0"
        std_min, std_max = stats["training_rows_transformed_std_min_max"]
        assert 0.99 < std_min <= std_max < 1.01, f"fold {fold_id} training std not ~1"
        assert stats["all_rows_transformed_all_finite"] is True


def test_schema_lists_exactly_495_feature_names_in_the_frozen_order():
    schema = json.loads(FR3_FUSION_SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["fused_dim"] == 495
    assert schema["esm2_dim"] == 480
    assert schema["n_descriptors"] == 15
    assert len(schema["feature_names"]) == 495
    assert schema["feature_names"][:5] == ["esm2_0", "esm2_1", "esm2_2", "esm2_3", "esm2_4"]
    assert schema["feature_names"][-1] == "frac_proline"


def test_rerunning_the_stage_is_fully_reproducible():
    first = run_fr3_feature_fusion()
    with np.load(FR3_FUSED_RAW_CACHE_PATH, allow_pickle=False) as npz:
        first_features = npz["features"].copy()
    first_scalers = json.loads(FR3_FUSION_SCALERS_PATH.read_text(encoding="utf-8"))

    second = run_fr3_feature_fusion()
    with np.load(FR3_FUSED_RAW_CACHE_PATH, allow_pickle=False) as npz:
        second_features = npz["features"].copy()
    second_scalers = json.loads(FR3_FUSION_SCALERS_PATH.read_text(encoding="utf-8"))

    assert first["fold_training_sizes"] == second["fold_training_sizes"]
    np.testing.assert_array_equal(first_features, second_features)
    assert first_scalers == second_scalers
