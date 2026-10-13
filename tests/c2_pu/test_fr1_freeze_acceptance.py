"""FR1 Bucket 1.7 acceptance: the committed pp1_baseline_v1 freeze must be
internally consistent with its own manifest. Run this any time to confirm
the frozen directory hasn't drifted from what MANIFEST.json claims it is
(AGENTS.md rule #4: frozen artifacts stay frozen -- this is the tripwire).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from plantaox.c2_pu.curation.freeze import verify_frozen_baseline

REPO_ROOT = Path(__file__).resolve().parents[2]
FROZEN_DIR = REPO_ROOT / "data" / "processed" / "c2_pu" / "frozen" / "pp1_baseline_v1"

pytestmark = pytest.mark.skipif(
    not (FROZEN_DIR / "MANIFEST.json").exists(), reason="pp1_baseline_v1 not frozen in this checkout"
)


def test_every_frozen_file_matches_its_manifest_checksum():
    results = verify_frozen_baseline(FROZEN_DIR)
    failures = {name: ok for name, ok in results.items() if not ok}
    assert not failures, f"Frozen baseline tampered or incomplete: {failures}"


def test_manifest_counts_match_the_frozen_files():
    manifest = json.loads((FROZEN_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
    counts = manifest["counts"]

    import pandas as pd

    positive_df = pd.read_parquet(FROZEN_DIR / "aop_positives_provisional.parquet")
    assert len(positive_df) == counts["positive_pool_provisional"]
    assert int((positive_df["evidence_tier"] == "E1").sum()) == counts["positive_pool_provisional_e1"]
    assert int((positive_df["evidence_tier"] == "E2").sum()) == counts["positive_pool_provisional_e2"]

    cdhit_df = pd.read_parquet(FROZEN_DIR / "aop_positives_cdhit90.parquet")
    assert len(cdhit_df) == counts["cdhit_clusters"]

    splits_df = pd.read_csv(FROZEN_DIR / "graphpart_splits.csv")
    assert len(splits_df) == counts["graphpart_retained"]

    excluded_df = pd.read_csv(FROZEN_DIR / "graphpart_excluded_for_homology.csv")
    assert len(excluded_df) == counts["graphpart_excluded_for_homology"]


def test_manifest_declares_required_metadata():
    manifest = json.loads((FROZEN_DIR / "MANIFEST.json").read_text(encoding="utf-8"))
    for key in ("version_id", "created_at", "git_commit", "tool_versions", "config", "known_limitations",
                "pending_supervisor_approvals", "file_checksums"):
        assert key in manifest, f"MANIFEST.json missing required key: {key}"
    assert manifest["config"]["graphpart"]["denominator"] == "full"
    assert len(manifest["known_limitations"]) >= 4
    assert len(manifest["pending_supervisor_approvals"]) >= 1
