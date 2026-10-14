"""FR2 Bucket 2.4 acceptance checks against the real, full audit artifacts.
Skips cleanly if the audit hasn't been run in this checkout. This stage is
read-only by design -- these tests verify the audit's own outputs are
internally consistent, not that the underlying pools are contamination-
free (the audit's job is to report that honestly, including when they are
not; see IMPLEMENTATION_STATUS.md for the findings pending a decision).
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = REPO_ROOT / "data" / "processed" / "c2_pu"

AUDIT_REPORT_PATH = PROCESSED_DIR / "fr2_pool_audit_report.json"
AUDIT_INTEGRITY_REPORT_PATH = PROCESSED_DIR / "audit_integrity_report.json"
AUDIT_OVERLAP_MATRIX_PATH = PROCESSED_DIR / "audit_exact_overlap_matrix.csv"
AUDIT_OVERLAP_DETAIL_PATH = PROCESSED_DIR / "audit_exact_overlap_detail.csv"
AUDIT_HOMOLOGY_CLUSTERS_PATH = PROCESSED_DIR / "audit_cross_pool_homology_clusters.csv"
AUDIT_HOMOLOGY_SUMMARY_PATH = PROCESSED_DIR / "audit_cross_pool_homology_summary.json"
AUDIT_C3_CONTRACT_REPORT_PATH = PROCESSED_DIR / "audit_c3_fold_contract_report.json"

pytestmark = pytest.mark.skipif(
    not AUDIT_REPORT_PATH.exists(), reason="FR2 pool audit not present in this checkout"
)


def test_integrity_report_covers_every_pool_with_known_authoritative_counts():
    reports = {r["pool"]: r for r in json.loads(AUDIT_INTEGRITY_REPORT_PATH.read_text())}
    assert reports["FR1_positives"]["n_records"] == 1205
    assert reports["conflicts_179"]["n_records"] == 179
    assert reports["external_control"]["n_records"] == 38
    assert reports["C1_v2"]["n_records"] == 5000
    assert reports["C2"]["n_records"] == 2000
    assert reports["C3_union"]["n_records"] == 2325
    # No pool introduces a duplicate ID or a non-standard-alphabet sequence.
    for name, r in reports.items():
        assert r["n_duplicate_ids"] == 0, name
        assert r["n_non_standard_alphabet"] == 0, name


def test_overlap_matrix_diagonal_matches_each_pools_unique_sequence_count():
    matrix = pd.read_csv(AUDIT_OVERLAP_MATRIX_PATH, index_col=0)
    reports = {r["pool"]: r for r in json.loads(AUDIT_INTEGRITY_REPORT_PATH.read_text())}
    for name in matrix.index:
        assert matrix.loc[name, name] == reports[name]["n_unique_sequences"]


def test_overlap_matrix_is_symmetric():
    matrix = pd.read_csv(AUDIT_OVERLAP_MATRIX_PATH, index_col=0)
    for a in matrix.index:
        for b in matrix.columns:
            assert matrix.loc[a, b] == matrix.loc[b, a], f"{a}/{b} asymmetric"


def test_overlap_detail_row_count_matches_matrix_off_diagonal_counts():
    matrix = pd.read_csv(AUDIT_OVERLAP_MATRIX_PATH, index_col=0)
    detail = pd.read_csv(AUDIT_OVERLAP_DETAIL_PATH)
    for a in matrix.index:
        for b in matrix.columns:
            if a >= b:
                continue
            expected = matrix.loc[a, b]
            actual = len(detail[(detail["pool_a"] == a) & (detail["pool_b"] == b)])
            assert actual == expected, f"{a}/{b}: matrix says {expected}, detail has {actual}"


def test_fr1_positives_pool_has_zero_exact_overlap_with_any_challenge_pool():
    # The one invariant that must never fail: FR1's own confirmed positives
    # must not leak (exactly) into C1/C2/C3 -- this was enforced at
    # construction time for all three and is re-verified here independently.
    matrix = pd.read_csv(AUDIT_OVERLAP_MATRIX_PATH, index_col=0)
    for challenge_pool in ("C1_v2", "C2", "C3_union"):
        assert matrix.loc["FR1_positives", challenge_pool] == 0


def test_homology_summary_is_internally_consistent_with_the_clusters_file():
    summary = json.loads(AUDIT_HOMOLOGY_SUMMARY_PATH.read_text())
    clusters = pd.read_csv(AUDIT_HOMOLOGY_CLUSTERS_PATH)
    assert clusters["cluster_id"].nunique() == summary["n_cross_pool_clusters_raw"]
    # Every cross-pool cluster must genuinely span >1 pool.
    for cid, g in clusters.groupby("cluster_id"):
        assert g["pool"].nunique() > 1, f"cluster {cid} doesn't actually span multiple pools"


def test_real_homology_candidates_are_all_at_or_above_the_length_floor():
    summary = json.loads(AUDIT_HOMOLOGY_SUMMARY_PATH.read_text())
    clusters = pd.read_csv(AUDIT_HOMOLOGY_CLUSTERS_PATH)
    floor = summary["length_floor_for_interpretation"]
    for cid in summary["real_homology_cluster_ids"]:
        g = clusters[clusters["cluster_id"] == cid]
        long_enough_pools = g[g["length"] >= floor]["pool"].nunique()
        assert long_enough_pools > 1, f"cluster {cid} listed as real but doesn't meet the length floor"


def test_c3_fold_contract_report_confirms_fold_safety_when_cache_available():
    report = json.loads(AUDIT_C3_CONTRACT_REPORT_PATH.read_text())
    if report.get("fold_safety_verified") is None:
        pytest.skip("C3 embedding cache not present locally -- contract not re-verified this run")
    assert report["fold_safety_verified"] is True
    assert report["n_folds"] == 5
    assert report["top_n_per_fold"] == 2000


def test_top_level_report_flags_known_contamination_rather_than_hiding_it():
    report = json.loads(AUDIT_REPORT_PATH.read_text())
    assert "c1_c2_exact_overlap" in report["contamination_requiring_decision"]
    assert report["contamination_requiring_decision"]["c1_c2_exact_overlap"]["n_sequences"] > 0
    assert report["ready_for_technical_acceptance"] is False
