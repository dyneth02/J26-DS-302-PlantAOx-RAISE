"""Bucket 3.5 acceptance tests: the offline feature-pipeline demonstration
against the real local Tasks 3.1-3.4 artifacts.

Gated to skip cleanly when those artifacts aren't present locally.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pandas as pd
import pytest

from plantaox.c2_pu.run import (
    C3_RANKING_PATH,
    FR3_DEMO_FOLD_ID,
    FR3_DEMO_OUTPUT_PATH,
    FR3_DEMO_PEPTIDE_IDS,
    FR3_DESCRIPTOR_TABLE_PATH,
    FR3_EMBEDDINGS_MANIFEST_PATH,
    FR3_FEATURE_CACHE_MANIFEST_PATH,
    FR3_FEATURE_CACHE_PATH_TEMPLATE,
    FR3_FUSION_SCALERS_PATH,
    FROZEN_DIR,
    FR2_FROZEN_DIR,
    run_fr3_demo,
)

REQUIRED_INPUTS = [
    FR3_DESCRIPTOR_TABLE_PATH,
    FR3_EMBEDDINGS_MANIFEST_PATH,
    FR3_FUSION_SCALERS_PATH,
    FR3_FEATURE_CACHE_MANIFEST_PATH,
    Path(FR3_FEATURE_CACHE_PATH_TEMPLATE.format(fold_id=FR3_DEMO_FOLD_ID)),
]
pytestmark = pytest.mark.skipif(
    not all(p.exists() for p in REQUIRED_INPUTS),
    reason="Tasks 3.1-3.4 outputs not present locally.",
)


def _sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def pre_run_hashes():
    return {
        "descriptor_table": _sha256(FR3_DESCRIPTOR_TABLE_PATH),
        "embeddings_manifest": _sha256(FR3_EMBEDDINGS_MANIFEST_PATH),
        "fusion_scalers": _sha256(FR3_FUSION_SCALERS_PATH),
        "feature_cache_manifest": _sha256(FR3_FEATURE_CACHE_MANIFEST_PATH),
    }


@pytest.fixture(scope="module")
def summary(pre_run_hashes):
    return run_fr3_demo()


def test_prior_task_outputs_and_frozen_baselines_are_untouched(summary, pre_run_hashes):
    assert _sha256(FR3_DESCRIPTOR_TABLE_PATH) == pre_run_hashes["descriptor_table"]
    assert _sha256(FR3_EMBEDDINGS_MANIFEST_PATH) == pre_run_hashes["embeddings_manifest"]
    assert _sha256(FR3_FUSION_SCALERS_PATH) == pre_run_hashes["fusion_scalers"]
    assert _sha256(FR3_FEATURE_CACHE_MANIFEST_PATH) == pre_run_hashes["feature_cache_manifest"]
    assert FROZEN_DIR.exists() and FR2_FROZEN_DIR.exists()
    assert not (FROZEN_DIR / "fr3_demo_output.json").exists()
    assert not (FR2_FROZEN_DIR / "fr3_demo_output.json").exists()


def test_pool_coverage_matches_the_documented_accepted_counts(summary):
    assert summary["pool_coverage"] == {
        "FR1_positives_training": 710,
        "FR1_positives_held_out": 124,
        "C1": 3788,
        "C2": 2000,
        "C3_union_in_cache": 2325,
        "C3_fold0_challenge_selection": 2000,
        "external_control": 38,
    }


def test_every_validation_check_passes(summary):
    assert all(summary["validation"].values()), summary["validation"]


def test_descriptor_and_embedding_shapes_are_correct(summary):
    assert summary["descriptor_extraction"]["shape"] == [7, 15]
    assert summary["embedding_loading"]["shape"] == [7, 480]
    assert summary["embedding_loading"]["source"] == "loaded from fr3_embeddings.npz -- NOT recomputed"


def test_feature_cache_shape_is_the_full_9356_by_495(summary):
    assert summary["feature_cache_loading"]["shape"] == [9356, 495]


def test_demo_c3_peptides_are_the_real_fold0_rank_1_and_2(summary):
    ranking = pd.read_csv(C3_RANKING_PATH)
    fold0 = ranking[ranking["fold_id"] == 0].set_index("peptide_id")
    assert fold0.loc[FR3_DEMO_PEPTIDE_IDS["C3_fold0_rank1"], "rank"] == 1
    assert fold0.loc[FR3_DEMO_PEPTIDE_IDS["C3_fold0_rank2"], "rank"] == 2


def test_demo_output_file_on_disk_matches_the_returned_summary(summary):
    on_disk = json.loads(FR3_DEMO_OUTPUT_PATH.read_text(encoding="utf-8"))
    assert on_disk == summary


def test_rerunning_the_demo_is_fully_deterministic():
    first = run_fr3_demo()
    second = run_fr3_demo()
    assert first == second


def test_demo_completes_in_well_under_ten_seconds():
    start = time.time()
    run_fr3_demo()
    elapsed = time.time() - start
    assert elapsed < 10, f"demo took {elapsed:.1f}s -- should be near-instant with no live inference"


def test_missing_fold_cache_raises_a_clear_prerequisite_error():
    with pytest.raises(FileNotFoundError, match="Tasks 3.1-3.4"):
        run_fr3_demo(fold_id=99)


def test_smoke_demo_runs_offline_without_torch_or_esm_in_a_fresh_subprocess():
    # Proves the FULL demo path (input validation, live descriptor
    # extraction, cached-embedding lookup, cached-feature-cache lookup,
    # pool/fold selection) never imports torch/esm -- run in a genuinely
    # fresh subprocess since other tests in this session already import
    # torch and would mask a real accidental import if checked in-process.
    script = (
        "import sys\n"
        "from plantaox.c2_pu.run import run_fr3_demo\n"
        "assert 'torch' not in sys.modules, 'importing run.py pulled in torch'\n"
        "assert 'esm' not in sys.modules, 'importing run.py pulled in esm'\n"
        "summary = run_fr3_demo()\n"
        "assert all(summary['validation'].values())\n"
        "assert 'torch' not in sys.modules, 'running the demo pulled in torch'\n"
        "print('SMOKE_OK')\n"
    )
    start = time.time()
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=Path(__file__).resolve().parents[2],
        env={**os.environ, "PYTHONPATH": "src"},
        capture_output=True,
        text=True,
        timeout=30,
    )
    elapsed = time.time() - start
    assert result.returncode == 0, f"stdout={result.stdout}\nstderr={result.stderr}"
    assert "SMOKE_OK" in result.stdout
    assert elapsed < 15, f"smoke-test subprocess took {elapsed:.1f}s -- suspiciously slow for an offline demo"
