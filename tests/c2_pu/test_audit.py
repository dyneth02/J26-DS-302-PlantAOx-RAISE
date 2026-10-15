"""Tests for curation/audit.py (Bucket 2.4 -- pool contamination/leakage
audit). The CD-HIT-backed cross_pool_homology_clusters() is exercised by
the full-file acceptance test (WSL-dependent, skipped if unavailable);
everything else here is pure-Python and runs unconditionally.
"""

from __future__ import annotations

from plantaox.c2_pu.curation.audit import (
    external_reference_screen,
    overlap_detail,
    pairwise_exact_overlap,
    sequence_integrity_report,
)


def test_sequence_integrity_report_counts_everything_correctly():
    records = [
        ("id1", "ACDEFG"),  # fine
        ("id2", "ACDEFG"),  # duplicate sequence, unique id
        ("id1", "GHIKLM"),  # duplicate id
        ("id3", "ACXEFG"),  # non-standard alphabet
        ("id4", "AC"),  # too short
        ("id5", "A" * 60),  # too long
    ]
    report = sequence_integrity_report("test_pool", records)
    assert report["n_records"] == 6
    assert report["n_unique_ids"] == 5  # id1 repeated
    assert report["n_duplicate_ids"] == 1
    assert report["n_unique_sequences"] == 5  # ACDEFG repeated
    assert report["n_duplicate_sequences"] == 1
    assert report["n_non_standard_alphabet"] == 1
    assert report["n_length_window_violations"] == 2


def test_pairwise_exact_overlap_matrix_is_symmetric_with_pool_sizes_on_diagonal():
    pools = {
        "A": {"AAA", "BBB", "CCC"},
        "B": {"BBB", "CCC", "DDD"},
        "C": {"EEE"},
    }
    matrix = pairwise_exact_overlap(pools)
    assert matrix.loc["A", "A"] == 3
    assert matrix.loc["A", "B"] == 2
    assert matrix.loc["B", "A"] == 2  # symmetric
    assert matrix.loc["A", "C"] == 0
    assert matrix.loc["C", "C"] == 1


def test_overlap_detail_returns_the_actual_shared_sequences_sorted():
    pools = {"A": {"ZZZ", "AAA", "BBB"}, "B": {"BBB", "AAA", "CCC"}}
    assert overlap_detail(pools, "A", "B") == ["AAA", "BBB"]


def test_external_reference_screen_flags_hits_per_pool():
    pools = {"C1": {"AAA", "BBB"}, "C2": {"CCC"}, "FR1_positives": {"AAA", "DDD"}}
    reference = {"AAA", "CCC", "ZZZ"}
    hits = external_reference_screen(pools, reference)
    assert hits["C1"] == ["AAA"]
    assert hits["C2"] == ["CCC"]
    assert hits["FR1_positives"] == ["AAA"]
