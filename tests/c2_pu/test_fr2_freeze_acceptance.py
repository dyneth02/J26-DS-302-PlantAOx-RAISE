"""FR2 Bucket 2.7 freeze acceptance checks against the real, full
`pp2_baseline_v1` artifact. Skips cleanly if not present.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from plantaox.c2_pu.curation.freeze import verify_frozen_baseline
from plantaox.c2_pu.run import FR2_FROZEN_DIR, FR1_BASELINE_VERSION
from plantaox.c2_pu.run import FROZEN_DIR as FR1_FROZEN_DIR

MANIFEST_PATH = FR2_FROZEN_DIR / "MANIFEST.json"

pytestmark = pytest.mark.skipif(not MANIFEST_PATH.exists(), reason="pp2_baseline_v1 not frozen in this checkout")


def test_manifest_checksums_all_verify():
    result = verify_frozen_baseline(FR2_FROZEN_DIR)
    assert result, "manifest listed zero files"
    assert all(result.values()), f"checksum mismatch: {result}"


def test_manifest_includes_every_required_canonical_artifact():
    manifest = json.loads(MANIFEST_PATH.read_text())
    checksums = manifest["file_checksums"]
    required_files = [
        "stage_c1_decoys_v3.fasta",
        "stage_c2_bioactive_unlabeled_v2.fasta",
        "stage_c3_esm2_hard_challenges.fasta",
        "c3_similarity_ranking.csv",
        "anoxpepred_external_control_validated.csv",
        "fr2_pool_audit_report.json",
        "distribution_ks_comparison.csv",
    ]
    for f in required_files:
        assert f in checksums, f"{f} missing from pp2_baseline_v1 manifest"


def test_manifest_counts_match_canonical_artifacts():
    manifest = json.loads(MANIFEST_PATH.read_text())
    counts = manifest["counts"]
    assert counts["c1_v3_records"] == 5000
    assert counts["c2_v2_records"] == 2000
    assert counts["c3_union_records"] >= 1
    assert counts["c3_ranking_rows"] >= 1
    assert counts["external_control_records"] == 38


def test_manifest_documents_known_limitations_not_silently_clean():
    manifest = json.loads(MANIFEST_PATH.read_text())
    assert len(manifest["known_limitations"]) >= 5


def test_fr1_baseline_untouched_by_the_fr2_freeze():
    result = verify_frozen_baseline(FR1_FROZEN_DIR)
    assert all(result.values()), f"pp1_baseline_v1 corrupted: {result}"


def test_fr2_baseline_declares_its_fr1_dependency():
    manifest = json.loads(MANIFEST_PATH.read_text())
    assert manifest["fr1_baseline_dependency"] == FR1_BASELINE_VERSION
