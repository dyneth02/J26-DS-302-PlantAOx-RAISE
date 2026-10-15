"""FR1 Bucket 1.7 acceptance: re-running the full pipeline from raw inputs
must reproduce byte-identical data outputs (AGENTS.md validation rule #3).

This actually invokes CD-HIT/GraphPart via WSL (~20s), unlike the other
acceptance tests which only validate already-produced files -- so it is
marked slow and skipped unless the tools are reachable.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from plantaox.c2_pu.curation.dedup import check_cdhit_available
from plantaox.c2_pu.curation.splits import check_graphpart_available
from plantaox.c2_pu.run import (
    GRAPHPART_SPLITS_PATH,
    POSITIVE_POOL_CDHIT_PATH,
    run_fr1_cluster,
    run_fr1_positives,
    run_fr1_split,
)

pytestmark = pytest.mark.skipif(
    not (check_cdhit_available() and check_graphpart_available()),
    reason="cd-hit/graphpart not reachable in this environment (see IMPLEMENTATION_STATUS.md setup)",
)

# GraphPart's self-report includes wall-clock timing fields that legitimately
# differ run-to-run even with fully deterministic algorithmic output.
_VOLATILE_REPORT_KEYS = {"time_script_start", "time_edges_complete", "time_script_complete"}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _strip_volatile(report: dict) -> dict:
    return {k: v for k, v in report.items() if k not in _VOLATILE_REPORT_KEYS}


def test_rerunning_the_full_pipeline_reproduces_identical_outputs():
    data_files = [
        POSITIVE_POOL_CDHIT_PATH.parent / "aop_positives_provisional.parquet",
        POSITIVE_POOL_CDHIT_PATH.parent / "cdhit_clusters.tsv",
        POSITIVE_POOL_CDHIT_PATH,
        GRAPHPART_SPLITS_PATH,
        GRAPHPART_SPLITS_PATH.parent / "graphpart_excluded_for_homology.csv",
    ]
    before_hashes = {p: _sha256(p) for p in data_files}
    before_report = _strip_volatile(
        json.loads((GRAPHPART_SPLITS_PATH.parent / "graphpart_splits_report.json").read_text())
    )

    run_fr1_positives()
    run_fr1_cluster()
    run_fr1_split()

    after_hashes = {p: _sha256(p) for p in data_files}
    after_report = _strip_volatile(
        json.loads((GRAPHPART_SPLITS_PATH.parent / "graphpart_splits_report.json").read_text())
    )

    for p in data_files:
        assert before_hashes[p] == after_hashes[p], f"{p.name} changed across a reproducibility re-run"
    assert before_report == after_report
