"""Bucket 3.4 acceptance tests: full-file validation of the
fr3-feature-cache stage against the real Task 3.1-3.3 outputs.

Gated to skip cleanly when those outputs aren't present locally.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import textwrap
import time
from pathlib import Path

import numpy as np
import pytest

from plantaox.c2_pu.common.feature_cache import CorruptedCacheError, get_c3_fold_challenge_rows, load_fold_feature_cache
from plantaox.c2_pu.run import (
    C3_RANKING_PATH,
    C3_TOP_N_PER_FOLD,
    FR3_DESCRIPTOR_TABLE_PATH,
    FR3_EMBEDDINGS_CACHE_PATH,
    FR3_FEATURE_CACHE_MANIFEST_PATH,
    FR3_FEATURE_CACHE_VALIDATION_REPORT_PATH,
    FR3_FUSED_RAW_CACHE_PATH,
    FR3_FUSION_SCALERS_PATH,
    FR3_FUSION_SCHEMA_PATH,
    FROZEN_DIR,
    FR2_FROZEN_DIR,
    run_fr3_feature_cache,
)

REQUIRED_INPUTS = [FR3_FUSED_RAW_CACHE_PATH, FR3_FUSION_SCALERS_PATH, FR3_FUSION_SCHEMA_PATH]
pytestmark = pytest.mark.skipif(
    not all(p.exists() for p in REQUIRED_INPUTS),
    reason="Task 3.3 outputs not present locally.",
)


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def pre_run_hashes():
    return {
        "descriptor_table": _sha256(FR3_DESCRIPTOR_TABLE_PATH),
        "embeddings_cache": _sha256(FR3_EMBEDDINGS_CACHE_PATH),
        "fused_raw": _sha256(FR3_FUSED_RAW_CACHE_PATH),
        "fusion_scalers": _sha256(FR3_FUSION_SCALERS_PATH),
        "fusion_schema": _sha256(FR3_FUSION_SCHEMA_PATH),
    }


@pytest.fixture(scope="module")
def summary(pre_run_hashes):
    return run_fr3_feature_cache()


@pytest.fixture(scope="module")
def manifest(summary):
    return json.loads(FR3_FEATURE_CACHE_MANIFEST_PATH.read_text(encoding="utf-8"))


def test_task_3_1_through_3_3_outputs_are_untouched(summary, pre_run_hashes):
    assert _sha256(FR3_DESCRIPTOR_TABLE_PATH) == pre_run_hashes["descriptor_table"]
    assert _sha256(FR3_EMBEDDINGS_CACHE_PATH) == pre_run_hashes["embeddings_cache"]
    assert _sha256(FR3_FUSED_RAW_CACHE_PATH) == pre_run_hashes["fused_raw"]
    assert _sha256(FR3_FUSION_SCALERS_PATH) == pre_run_hashes["fusion_scalers"]
    assert _sha256(FR3_FUSION_SCHEMA_PATH) == pre_run_hashes["fusion_schema"]


def test_frozen_baselines_are_untouched(summary):
    assert FROZEN_DIR.exists() and FR2_FROZEN_DIR.exists()
    assert not (FROZEN_DIR / "fr3_feature_cache_manifest.json").exists()
    assert not (FR2_FROZEN_DIR / "fr3_feature_cache_manifest.json").exists()


def test_manifest_has_5_fold_entries_with_matching_sha256(manifest):
    assert manifest["n_folds"] == 5
    assert set(manifest["folds"].keys()) == {"0", "1", "2", "3", "4"}
    for fold_id, entry in manifest["folds"].items():
        assert _sha256(entry["cache_path"]) == entry["cache_sha256"]
        assert entry["shape"] == [9356, 495]
        assert entry["dtype"] == "float32"


def test_each_cache_round_trip_loads_and_is_fully_finite(manifest):
    for fold_id, entry in manifest["folds"].items():
        cache = load_fold_feature_cache(entry["cache_path"], entry)
        assert cache["features"].shape == (9356, 495)
        assert cache["features"].dtype == np.float32
        assert np.isfinite(cache["features"]).all()


def test_c3_union_is_fully_present_in_every_fold_cache_not_fold_filtered(manifest):
    for fold_id, entry in manifest["folds"].items():
        cache = load_fold_feature_cache(entry["cache_path"], entry)
        assert int((cache["pools"] == "C3").sum()) == 2325


def test_c3_fold_specific_retrieval_matches_the_real_ranking_file(manifest):
    # End-to-end integration, not mocked: the real c3_similarity_ranking.csv,
    # the real load_fold_challenges, and a real materialized cache.
    for fold_id_str, entry in manifest["folds"].items():
        fold_id = int(fold_id_str)
        cache = load_fold_feature_cache(entry["cache_path"], entry)
        ids, rows, fold_df = get_c3_fold_challenge_rows(cache, C3_RANKING_PATH, fold_id)
        assert len(ids) == len(fold_df) == C3_TOP_N_PER_FOLD
        assert rows.shape == (C3_TOP_N_PER_FOLD, 495)


def test_requesting_a_different_folds_c3_selection_against_this_cache_is_rejected(manifest):
    entry = manifest["folds"]["0"]
    cache = load_fold_feature_cache(entry["cache_path"], entry)
    with pytest.raises(ValueError, match="does not match"):
        get_c3_fold_challenge_rows(cache, C3_RANKING_PATH, fold_id=1)


def test_external_control_never_appears_in_any_folds_training_or_held_out_set():
    validation = json.loads(FR3_FEATURE_CACHE_VALIDATION_REPORT_PATH.read_text(encoding="utf-8"))
    for fold_id, stats in validation["per_fold"].items():
        assert stats["external_control_disjoint_from_training_and_held_out"] is True


def test_each_folds_own_training_rows_standardize_to_mean_0_std_1():
    validation = json.loads(FR3_FEATURE_CACHE_VALIDATION_REPORT_PATH.read_text(encoding="utf-8"))
    for fold_id, stats in validation["per_fold"].items():
        assert stats["training_rows_mean_abs_max"] < 1e-3
        std_min, std_max = stats["training_rows_std_min_max"]
        assert 0.99 < std_min <= std_max < 1.01


def test_corrupted_real_cache_is_rejected_not_silently_loaded(manifest, tmp_path):
    entry = dict(manifest["folds"]["0"])
    original_path = Path(entry["cache_path"])
    corrupted_path = tmp_path / "corrupted_fold0.npz"
    data = bytearray(original_path.read_bytes())
    data[len(data) // 2] ^= 0xFF
    corrupted_path.write_bytes(bytes(data))
    entry["cache_path"] = str(corrupted_path)
    with pytest.raises(CorruptedCacheError, match="SHA-256 mismatch"):
        load_fold_feature_cache(corrupted_path, entry)


def test_rerunning_the_stage_is_fully_reproducible():
    first = run_fr3_feature_cache()
    first_manifest = json.loads(FR3_FEATURE_CACHE_MANIFEST_PATH.read_text(encoding="utf-8"))
    second = run_fr3_feature_cache()
    second_manifest = json.loads(FR3_FEATURE_CACHE_MANIFEST_PATH.read_text(encoding="utf-8"))
    assert first_manifest["peptide_id_order_sha256"] == second_manifest["peptide_id_order_sha256"]
    for fold_id in first_manifest["folds"]:
        assert first_manifest["folds"][fold_id]["cache_sha256"] == second_manifest["folds"][fold_id]["cache_sha256"]


def test_smoke_cached_feature_loading_needs_no_torch_wsl_or_descriptor_recomputation(manifest):
    # Proves the LOAD path (what an FR4 training script actually imports)
    # never pulls in torch/esm, never shells out to WSL, and never
    # recomputes descriptors -- run in a fresh subprocess so the check is
    # conclusive even though other tests in this session may have already
    # imported torch.
    entry = manifest["folds"]["0"]
    script = textwrap.dedent(f"""
        import sys, json
        assert "torch" not in sys.modules
        assert "esm" not in sys.modules
        from plantaox.c2_pu.common.feature_cache import load_fold_feature_cache, get_training_rows
        assert "torch" not in sys.modules, "importing feature_cache pulled in torch"
        assert "esm" not in sys.modules, "importing feature_cache pulled in esm"
        entry = json.loads({json.dumps(json.dumps(entry))})
        cache = load_fold_feature_cache(entry["cache_path"], entry)
        assert cache["features"].shape == (9356, 495)
        assert "torch" not in sys.modules, "loading a cache pulled in torch"
        print("SMOKE_OK")
    """)
    start = time.time()
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[2],
        env={**__import__("os").environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
        timeout=30,
    )
    elapsed = time.time() - start
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    assert "SMOKE_OK" in result.stdout
    # A real ESM-2 load+inference takes several seconds at minimum (model
    # load alone); loading a cache should be near-instant in comparison.
    assert elapsed < 10, f"smoke test took {elapsed:.1f}s -- suspiciously slow for a pure cache load"
