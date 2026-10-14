"""Unit tests for common/feature_cache.py (Bucket 3.4)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from plantaox.c2_pu.common.feature_cache import (
    CACHE_SCHEMA_VERSION,
    CorruptedCacheError,
    FeatureCacheMembershipError,
    build_fold_cache_arrays,
    get_c3_fold_challenge_rows,
    get_held_out_rows,
    get_pool_rows,
    get_training_rows,
    load_fold_feature_cache,
    scaler_identity_sha256,
    sha256_of,
)
from plantaox.c2_pu.curation.feature_fusion import FUSED_DIM, apply_scaler


def _write_cache(tmp_path, peptide_ids, pools, features, feature_names, scaler_mean, scaler_std, name="cache.npz"):
    path = tmp_path / name
    np.savez_compressed(
        path,
        peptide_ids=np.array(peptide_ids),
        pools=np.array(pools),
        features=features,
        feature_names=np.array(feature_names),
        scaler_mean=scaler_mean,
        scaler_std=scaler_std,
    )
    return path


def _manifest_entry_for(path, fold_id, shape, dtype, scaler_mean, scaler_std):
    return {
        "cache_path": str(path),
        "cache_sha256": sha256_of(path),
        "fold_id": fold_id,
        "shape": list(shape),
        "dtype": dtype,
        "feature_schema_version": CACHE_SCHEMA_VERSION,
        "scaler_identity_sha256": scaler_identity_sha256(scaler_mean, scaler_std),
        "n_training_samples": 3,
    }


# ---------------------------------------------------------------------------
# build_fold_cache_arrays / scaler_identity_sha256 / sha256_of
# ---------------------------------------------------------------------------


def test_build_fold_cache_arrays_matches_apply_scaler_within_float32_precision():
    rng = np.random.default_rng(0)
    raw = rng.normal(size=(10, FUSED_DIM))
    mean = raw[:5].mean(axis=0)
    std = raw[:5].std(axis=0, ddof=0)
    std = np.where(std < 1e-12, 1.0, std)

    expected = apply_scaler(raw, {"mean": mean, "std": std})
    actual = build_fold_cache_arrays([f"P{i}" for i in range(10)], ["FR1_positives"] * 10, raw, mean, std)

    assert actual.dtype == np.float32
    np.testing.assert_allclose(actual, expected, atol=1e-5, rtol=1e-5)


def test_scaler_identity_sha256_is_deterministic_and_sensitive():
    mean = np.zeros(495)
    std = np.ones(495)
    a = scaler_identity_sha256(mean, std)
    b = scaler_identity_sha256(mean, std)
    assert a == b
    std2 = std.copy()
    std2[0] = 2.0
    assert scaler_identity_sha256(mean, std2) != a


def test_sha256_of_matches_direct_hashlib(tmp_path):
    import hashlib

    path = tmp_path / "f.bin"
    path.write_bytes(b"hello world")
    assert sha256_of(path) == hashlib.sha256(b"hello world").hexdigest()


# ---------------------------------------------------------------------------
# load_fold_feature_cache -- happy path + every corruption mode
# ---------------------------------------------------------------------------


def _toy_cache(tmp_path):
    peptide_ids = ["P0", "P1", "P2"]
    pools = ["FR1_positives", "FR1_positives", "C1"]
    features = np.ones((3, FUSED_DIM), dtype=np.float32)
    feature_names = [f"f{i}" for i in range(FUSED_DIM)]
    mean = np.zeros(FUSED_DIM)
    std = np.ones(FUSED_DIM)
    path = _write_cache(tmp_path, peptide_ids, pools, features, feature_names, mean, std)
    entry = _manifest_entry_for(path, fold_id=0, shape=(3, FUSED_DIM), dtype="float32", scaler_mean=mean, scaler_std=std)
    return path, entry


def test_load_fold_feature_cache_happy_path(tmp_path):
    path, entry = _toy_cache(tmp_path)
    loaded = load_fold_feature_cache(path, entry)
    assert loaded["fold_id"] == 0
    assert list(loaded["peptide_ids"]) == ["P0", "P1", "P2"]
    assert loaded["features"].shape == (3, FUSED_DIM)


def test_load_fold_feature_cache_missing_file_raises(tmp_path):
    _, entry = _toy_cache(tmp_path)
    with pytest.raises(CorruptedCacheError, match="not found"):
        load_fold_feature_cache(tmp_path / "does_not_exist.npz", entry)


def test_load_fold_feature_cache_rejects_corrupted_bytes(tmp_path):
    path, entry = _toy_cache(tmp_path)
    data = bytearray(path.read_bytes())
    data[-10] ^= 0xFF  # flip a byte near the end (likely inside array data, not just zip central directory)
    path.write_bytes(bytes(data))
    with pytest.raises(CorruptedCacheError, match="SHA-256 mismatch"):
        load_fold_feature_cache(path, entry)


def test_load_fold_feature_cache_rejects_shape_mismatch(tmp_path):
    path, entry = _toy_cache(tmp_path)
    entry["shape"] = [999, FUSED_DIM]
    with pytest.raises(CorruptedCacheError, match="shape"):
        load_fold_feature_cache(path, entry)


def test_load_fold_feature_cache_rejects_dtype_mismatch(tmp_path):
    path, entry = _toy_cache(tmp_path)
    entry["dtype"] = "float64"
    with pytest.raises(CorruptedCacheError, match="dtype"):
        load_fold_feature_cache(path, entry)


def test_load_fold_feature_cache_rejects_schema_version_mismatch(tmp_path):
    path, entry = _toy_cache(tmp_path)
    entry["feature_schema_version"] = "some_other_version"
    with pytest.raises(CorruptedCacheError, match="schema_version"):
        load_fold_feature_cache(path, entry)


def test_load_fold_feature_cache_rejects_scaler_identity_mismatch(tmp_path):
    path, entry = _toy_cache(tmp_path)
    entry["scaler_identity_sha256"] = "0" * 64
    with pytest.raises(CorruptedCacheError, match="scaler"):
        load_fold_feature_cache(path, entry)


# ---------------------------------------------------------------------------
# Row accessors
# ---------------------------------------------------------------------------


def test_get_pool_rows_filters_by_pool(tmp_path):
    path, entry = _toy_cache(tmp_path)
    cache = load_fold_feature_cache(path, entry)
    ids, rows = get_pool_rows(cache, "C1")
    assert list(ids) == ["P2"]
    assert rows.shape == (1, FUSED_DIM)


def test_get_training_and_held_out_rows(tmp_path):
    path, entry = _toy_cache(tmp_path)
    cache = load_fold_feature_cache(path, entry)
    ids, rows = get_training_rows(cache, ["P0", "P1"])
    assert list(ids) == ["P0", "P1"]
    ids2, rows2 = get_held_out_rows(cache, ["P1"])
    assert list(ids2) == ["P1"]


def test_get_training_rows_raises_on_unknown_peptide_id(tmp_path):
    path, entry = _toy_cache(tmp_path)
    cache = load_fold_feature_cache(path, entry)
    with pytest.raises(FeatureCacheMembershipError, match="not present"):
        get_training_rows(cache, ["P0", "NOPE"])


# ---------------------------------------------------------------------------
# C3 fold-specific retrieval
# ---------------------------------------------------------------------------


def test_get_c3_fold_challenge_rows_rejects_mismatched_fold_id(tmp_path):
    path, entry = _toy_cache(tmp_path)
    cache = load_fold_feature_cache(path, entry)  # cache's own fold_id is 0
    with pytest.raises(ValueError, match="does not match"):
        get_c3_fold_challenge_rows(cache, tmp_path / "ranking.csv", fold_id=1)


def test_get_c3_fold_challenge_rows_resolves_via_load_fold_challenges(tmp_path):
    peptide_ids = ["P0", "P1", "C3-A", "C3-B"]
    pools = ["FR1_positives", "FR1_positives", "C3", "C3"]
    features = np.arange(4 * FUSED_DIM, dtype=np.float32).reshape(4, FUSED_DIM)
    feature_names = [f"f{i}" for i in range(FUSED_DIM)]
    mean = np.zeros(FUSED_DIM)
    std = np.ones(FUSED_DIM)
    path = _write_cache(tmp_path, peptide_ids, pools, features, feature_names, mean, std)
    entry = _manifest_entry_for(path, fold_id=0, shape=(4, FUSED_DIM), dtype="float32", scaler_mean=mean, scaler_std=std)
    cache = load_fold_feature_cache(path, entry)

    ranking_path = tmp_path / "ranking.csv"
    pd.DataFrame(
        {
            "fold_id": [0, 0, 1],
            "peptide_id": ["C3-A", "C3-B", "C3-A"],
            "sequence": ["AAA", "BBB", "AAA"],
            "rank": [1, 2, 1],
            "cosine_similarity": [0.9, 0.8, 0.9],
        }
    ).to_csv(ranking_path, index=False)

    ids, rows, fold_df = get_c3_fold_challenge_rows(cache, ranking_path, fold_id=0)
    assert list(ids) == ["C3-A", "C3-B"]
    assert rows.shape == (2, FUSED_DIM)
    assert len(fold_df) == 2
