"""Unit tests for experiment_data.py (Bucket 4.1 §C) against a small,
fully synthetic fold-0 cache -- mirrors test_feature_cache.py's fixture
style so these tests are fast and independent of the real local
artifacts (a separate, real-artifact acceptance test covers the genuine
fold-0 cache; see test_fr4_infra_smoke_test_acceptance.py)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from plantaox.c2_pu.common.feature_cache import CACHE_SCHEMA_VERSION, scaler_identity_sha256, sha256_of
from plantaox.c2_pu.experiment_config import ExperimentConfig
from plantaox.c2_pu.experiment_data import DataLeakageError, PoolData, WrongFoldError, build_experiment_data

FUSED_DIM = 495

# Synthetic universe: 6 FR1 positives (P0..P5), 2 C1, 2 C2, 3 C3 (one of
# which -- C3-C -- is deliberately NOT part of fold 0's selection), 1
# external control.
PEPTIDE_IDS = ["P0", "P1", "P2", "P3", "P4", "P5", "C1-A", "C1-B", "C2-A", "C2-B", "C3-A", "C3-B", "C3-C", "EXT-A"]
POOLS = (
    ["FR1_positives"] * 6
    + ["C1", "C1"]
    + ["C2", "C2"]
    + ["C3", "C3", "C3"]
    + ["external_control"]
)
SEQUENCES = [f"SEQ{pid}" for pid in PEPTIDE_IDS]  # all distinct -- no synthetic sequence leakage by default


def _write_cache(tmp_path, peptide_ids=PEPTIDE_IDS, pools=POOLS, fold_id=0):
    n = len(peptide_ids)
    rng = np.random.default_rng(hash(tuple(peptide_ids)) % (2**31))
    features = rng.normal(size=(n, FUSED_DIM)).astype(np.float32)
    mean = np.zeros(FUSED_DIM)
    std = np.ones(FUSED_DIM)
    path = tmp_path / f"fold{fold_id}_cache.npz"
    np.savez_compressed(
        path,
        peptide_ids=np.array(peptide_ids),
        pools=np.array(pools),
        features=features,
        feature_names=np.array([f"f{i}" for i in range(FUSED_DIM)]),
        scaler_mean=mean,
        scaler_std=std,
    )
    entry = {
        "cache_path": str(path),
        "cache_sha256": sha256_of(path),
        "fold_id": fold_id,
        "shape": [n, FUSED_DIM],
        "dtype": "float32",
        "feature_schema_version": CACHE_SCHEMA_VERSION,
        "scaler_identity_sha256": scaler_identity_sha256(mean, std),
        "n_training_samples": 4,
    }
    return path, entry


def _record_map_df(peptide_ids=PEPTIDE_IDS, pools=POOLS, sequences=SEQUENCES):
    evidence = ["E1", "E1", "E2", "E2", "E1", "E2"] + [None] * (len(peptide_ids) - 6)
    return pd.DataFrame({"peptide_id": peptide_ids, "pool": pools, "sequence": sequences, "evidence_tier": evidence})


def _fusion_scaler_entry(training_ids=("P1", "P2", "P3", "P4"), held_out_ids=("P0", "P5")):
    return {
        "mean": [0.0] * FUSED_DIM,
        "std": [1.0] * FUSED_DIM,
        "training_peptide_ids": list(training_ids),
        "held_out_peptide_ids": list(held_out_ids),
        "n_training_samples": len(training_ids),
    }


def _ranking_csv(tmp_path):
    path = tmp_path / "c3_similarity_ranking.csv"
    pd.DataFrame(
        {
            "fold_id": [0, 0, 1, 1],
            "peptide_id": ["C3-A", "C3-B", "C3-B", "C3-C"],
            "sequence": ["SEQC3-A", "SEQC3-B", "SEQC3-B", "SEQC3-C"],
            "rank": [1, 2, 1, 2],
            "cosine_similarity": [0.9, 0.8, 0.85, 0.7],
        }
    ).to_csv(path, index=False)
    return path


@pytest.fixture
def scenario(tmp_path):
    cache_path, cache_entry = _write_cache(tmp_path, fold_id=0)
    record_map = _record_map_df()
    scaler_entry = _fusion_scaler_entry()
    ranking_path = _ranking_csv(tmp_path)
    config = ExperimentConfig(experiment_id="t", baseline="PN", fold_id=0, validation_fraction=0.25, eval_seed=1)
    return config, cache_path, cache_entry, scaler_entry, record_map, ranking_path


# ---------------------------------------------------------------------------
# Correct feature dimension and fold selection (F.3)
# ---------------------------------------------------------------------------


def test_fused_representation_returns_495_columns(scenario):
    config, cache_path, cache_entry, scaler_entry, record_map, ranking_path = scenario
    data = build_experiment_data(config, cache_path, cache_entry, scaler_entry, record_map, ranking_path)
    assert data.feature_dim == 495
    assert data.train_positive.features.shape[1] == 495


@pytest.mark.parametrize("representation,expected_dim", [("esm", 480), ("descriptors", 15)])
def test_esm_and_descriptor_representations_slice_correctly(tmp_path, representation, expected_dim):
    cache_path, cache_entry = _write_cache(tmp_path, fold_id=0)
    record_map = _record_map_df()
    scaler_entry = _fusion_scaler_entry()
    ranking_path = _ranking_csv(tmp_path)
    config = ExperimentConfig(experiment_id="t", baseline="PN", fold_id=0, feature_representation=representation)
    data = build_experiment_data(config, cache_path, cache_entry, scaler_entry, record_map, ranking_path)
    assert data.feature_dim == expected_dim
    assert data.train_positive.features.shape[1] == expected_dim
    assert data.c1.features.shape[1] == expected_dim


def test_requested_fold_is_the_one_actually_loaded(scenario):
    config, cache_path, cache_entry, scaler_entry, record_map, ranking_path = scenario
    data = build_experiment_data(config, cache_path, cache_entry, scaler_entry, record_map, ranking_path)
    assert data.fold_id == 0
    assert set(data.c3_fold_challenges.peptide_ids.tolist()) == {"C3-A", "C3-B"}


# ---------------------------------------------------------------------------
# Training/held-out positive disjointness (F.4)
# ---------------------------------------------------------------------------


def test_train_validation_and_held_out_are_pairwise_disjoint(scenario):
    config, cache_path, cache_entry, scaler_entry, record_map, ranking_path = scenario
    data = build_experiment_data(config, cache_path, cache_entry, scaler_entry, record_map, ranking_path)
    train_ids = set(data.train_positive.peptide_ids.tolist())
    val_ids = set(data.validation_positive.peptide_ids.tolist())
    held_out_ids = set(data.held_out_positive.peptide_ids.tolist())
    assert train_ids.isdisjoint(val_ids)
    assert train_ids.isdisjoint(held_out_ids)
    assert val_ids.isdisjoint(held_out_ids)
    assert held_out_ids == {"P0", "P5"}  # GraphPart's own held-out fold, untouched
    assert train_ids | val_ids == {"P1", "P2", "P3", "P4"}  # validation carved from training-side only


def test_validation_split_never_touches_held_out_positives(scenario):
    config, cache_path, cache_entry, scaler_entry, record_map, ranking_path = scenario
    data = build_experiment_data(config, cache_path, cache_entry, scaler_entry, record_map, ranking_path)
    assert set(data.validation_positive.peptide_ids.tolist()) <= {"P1", "P2", "P3", "P4"}


def test_validation_fraction_too_high_for_the_training_pool_raises(tmp_path):
    cache_path, cache_entry = _write_cache(tmp_path, fold_id=0)
    record_map = _record_map_df()
    scaler_entry = _fusion_scaler_entry(training_ids=("P1",), held_out_ids=("P0", "P2", "P3", "P4", "P5"))
    ranking_path = _ranking_csv(tmp_path)
    config = ExperimentConfig(experiment_id="t", baseline="PN", fold_id=0, validation_fraction=0.99)
    with pytest.raises(ValueError, match="validation_fraction"):
        build_experiment_data(config, cache_path, cache_entry, scaler_entry, record_map, ranking_path)


# ---------------------------------------------------------------------------
# Unique-sequence-aware protection against C1 duplicate leakage (F.5)
# ---------------------------------------------------------------------------


def test_c1_subset_has_no_duplicate_peptide_ids(scenario):
    config, cache_path, cache_entry, scaler_entry, record_map, ranking_path = scenario
    data = build_experiment_data(config, cache_path, cache_entry, scaler_entry, record_map, ranking_path)
    ids = data.c1.peptide_ids.tolist()
    assert len(ids) == len(set(ids))


def test_repeated_sequence_across_pools_is_detected_and_rejected(tmp_path):
    # C1-B is given the SAME underlying sequence as a training positive
    # (P1) -- same biological peptide under a different pool/peptide_id,
    # the exact "repeated-sequence leakage" scenario this check exists for.
    peptide_ids = list(PEPTIDE_IDS)
    sequences = list(SEQUENCES)
    c1_b_index = peptide_ids.index("C1-B")
    p1_index = peptide_ids.index("P1")
    sequences[c1_b_index] = sequences[p1_index]  # inject the leak

    cache_path, cache_entry = _write_cache(tmp_path, fold_id=0)
    record_map = _record_map_df(sequences=sequences)
    scaler_entry = _fusion_scaler_entry()
    ranking_path = _ranking_csv(tmp_path)
    config = ExperimentConfig(experiment_id="t", baseline="PN", fold_id=0)

    with pytest.raises(DataLeakageError, match="repeated-sequence leakage"):
        build_experiment_data(config, cache_path, cache_entry, scaler_entry, record_map, ranking_path)


def test_duplicate_peptide_id_within_a_single_pool_is_rejected():
    with pytest.raises(DataLeakageError, match="duplicate peptide_id"):
        PoolData(
            pool="C1",
            peptide_ids=np.array(["A", "A"]),
            sequences=np.array(["SEQ1", "SEQ2"]),
            features=np.zeros((2, 495), dtype=np.float32),
        )


# ---------------------------------------------------------------------------
# Fold-specific C3 selection and wrong-fold rejection (F.6)
# ---------------------------------------------------------------------------


def test_c3_fold_challenges_match_the_rankings_fold_specific_rows(scenario):
    config, cache_path, cache_entry, scaler_entry, record_map, ranking_path = scenario
    data = build_experiment_data(config, cache_path, cache_entry, scaler_entry, record_map, ranking_path)
    assert set(data.c3_fold_challenges.peptide_ids.tolist()) == {"C3-A", "C3-B"}
    assert "C3-C" not in data.c3_fold_challenges.peptide_ids.tolist()  # fold 1's selection, not fold 0's


def test_c3_union_pool_is_not_silently_treated_as_one_folds_selection(scenario):
    # Sanity: the cache's full C3 pool (3 rows) is larger than fold 0's
    # actual challenge selection (2 rows) -- confirms the module resolves
    # fold-specific membership rather than returning every C3 row in the cache.
    config, cache_path, cache_entry, scaler_entry, record_map, ranking_path = scenario
    data = build_experiment_data(config, cache_path, cache_entry, scaler_entry, record_map, ranking_path)
    assert len(data.c3_fold_challenges.peptide_ids) == 2


def test_wrong_fold_cache_selection_combination_is_rejected(tmp_path):
    cache_path, cache_entry = _write_cache(tmp_path, fold_id=1)  # cache's OWN fold_id is 1
    record_map = _record_map_df()
    scaler_entry = _fusion_scaler_entry()
    ranking_path = _ranking_csv(tmp_path)
    config = ExperimentConfig(experiment_id="t", baseline="PN", fold_id=0)  # but config asks for fold 0
    with pytest.raises(WrongFoldError):
        build_experiment_data(config, cache_path, cache_entry, scaler_entry, record_map, ranking_path)


# ---------------------------------------------------------------------------
# External-control isolation (F.7)
# ---------------------------------------------------------------------------


def test_external_control_is_returned_as_its_own_distinct_pool(scenario):
    config, cache_path, cache_entry, scaler_entry, record_map, ranking_path = scenario
    data = build_experiment_data(config, cache_path, cache_entry, scaler_entry, record_map, ranking_path)
    assert data.external_control.peptide_ids.tolist() == ["EXT-A"]


def test_external_control_overlap_with_training_is_detected(tmp_path):
    # Deliberately mislabel EXT-A's sequence to match a training positive's
    # sequence -- the leakage check must still catch this even though the
    # POOL labels ("external_control" vs "FR1_positives") correctly differ.
    peptide_ids = list(PEPTIDE_IDS)
    sequences = list(SEQUENCES)
    ext_index = peptide_ids.index("EXT-A")
    p2_index = peptide_ids.index("P2")
    sequences[ext_index] = sequences[p2_index]

    cache_path, cache_entry = _write_cache(tmp_path, fold_id=0)
    record_map = _record_map_df(sequences=sequences)
    scaler_entry = _fusion_scaler_entry()
    ranking_path = _ranking_csv(tmp_path)
    config = ExperimentConfig(experiment_id="t", baseline="PN", fold_id=0)

    with pytest.raises(DataLeakageError):
        build_experiment_data(config, cache_path, cache_entry, scaler_entry, record_map, ranking_path)


# ---------------------------------------------------------------------------
# General finiteness/dtype/schema checks
# ---------------------------------------------------------------------------


def test_all_pool_data_is_float32_and_finite(scenario):
    config, cache_path, cache_entry, scaler_entry, record_map, ranking_path = scenario
    data = build_experiment_data(config, cache_path, cache_entry, scaler_entry, record_map, ranking_path)
    for pool in (data.train_positive, data.validation_positive, data.held_out_positive, data.c1, data.c2, data.c3_fold_challenges, data.external_control):
        assert pool.features.dtype == np.float32
        assert np.isfinite(pool.features).all()


def test_evidence_tier_is_attached_for_positive_pools_only(scenario):
    config, cache_path, cache_entry, scaler_entry, record_map, ranking_path = scenario
    data = build_experiment_data(config, cache_path, cache_entry, scaler_entry, record_map, ranking_path)
    assert data.train_positive.evidence_tier is not None
    assert set(data.train_positive.evidence_tier.tolist()) <= {"E1", "E2"}
    assert data.c1.evidence_tier is None


def test_leakage_report_confirms_zero_overlap_and_lists_checked_pairs(scenario):
    config, cache_path, cache_entry, scaler_entry, record_map, ranking_path = scenario
    data = build_experiment_data(config, cache_path, cache_entry, scaler_entry, record_map, ranking_path)
    assert data.leakage_report["overlap_found"] is False
    assert len(data.leakage_report["pairs_checked"]) == 21  # 7 subsets choose 2
