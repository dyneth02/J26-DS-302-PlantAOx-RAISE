"""Bucket 3.1 acceptance tests: full-file validation of the fr3-descriptors
stage against the real frozen pp1_baseline_v1/pp2_baseline_v1 artifacts.

Gated to skip cleanly when the frozen baselines aren't present locally
(same convention as the other test_fr*_acceptance.py files).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from plantaox.c2_pu.common.descriptors import DESCRIPTOR_NAMES
from plantaox.c2_pu.run import (
    C1_ACCESSION_MAP_V3_PATH,
    C1_CLEAN_FASTA_V3_PATH,
    C2_FASTA_V2_PATH,
    C3_FASTA_PATH,
    EXT_CONTROL_VALIDATED_PATH,
    FR3_COVERAGE_REPORT_PATH,
    FR3_DESCRIPTOR_SCHEMA_PATH,
    FR3_DESCRIPTOR_TABLE_PATH,
    FR3_RECORD_MAP_PATH,
    FR3_VALIDATION_REPORT_PATH,
    FROZEN_DIR,
    FROZEN_POSITIVE_POOL_PATH,
    GRAPHPART_SPLITS_PATH,
    run_fr3_descriptors,
)

REQUIRED_INPUTS = [
    FROZEN_POSITIVE_POOL_PATH,
    C1_CLEAN_FASTA_V3_PATH,
    C1_ACCESSION_MAP_V3_PATH,
    C2_FASTA_V2_PATH,
    C3_FASTA_PATH,
]

pytestmark = pytest.mark.skipif(
    not all(p.exists() for p in REQUIRED_INPUTS),
    reason="Frozen pp1_baseline_v1/pp2_baseline_v1 artifacts not present locally.",
)


@pytest.fixture(scope="module")
def summary():
    return run_fr3_descriptors()


def test_frozen_baselines_are_untouched_by_running_the_stage(summary):
    assert FROZEN_DIR.exists()
    # The stage must never write into either frozen directory.
    assert not (FROZEN_DIR / "fr3_descriptor_table.parquet").exists()


def test_coverage_matches_the_documented_frozen_counts(summary):
    coverage = summary["coverage"]
    assert coverage["FR1_positives"]["source_records"] == 1205
    assert coverage["FR1_positives"]["unique_sequences_with_descriptors"] == 1205
    assert coverage["C1"]["source_records"] == 5000
    assert coverage["C1"]["unique_sequences_with_descriptors"] == 3788
    assert coverage["C2"]["source_records"] == 2000
    assert coverage["C2"]["unique_sequences_with_descriptors"] == 2000
    assert coverage["C3"]["source_records"] == 2325
    assert coverage["C3"]["unique_sequences_with_descriptors"] == 2325
    if EXT_CONTROL_VALIDATED_PATH.exists():
        assert coverage["external_control"]["source_records"] == 38


def test_no_duplicate_peptide_ids_within_any_pool(summary):
    descriptor_df = pd.read_parquet(FR3_DESCRIPTOR_TABLE_PATH)
    for pool, group in descriptor_df.groupby("pool"):
        assert group["peptide_id"].is_unique, f"duplicate peptide_id within pool {pool}"


def test_record_map_preserves_every_source_record_with_no_loss_or_duplication(summary):
    record_df = pd.read_csv(FR3_RECORD_MAP_PATH)
    coverage = summary["coverage"]
    for pool, counts in coverage.items():
        pool_records = record_df[record_df["pool"] == pool]
        assert len(pool_records) == counts["source_records"]


def test_c1_record_level_duplication_does_not_multiply_descriptor_rows(summary):
    # C1 has 5,000 records but only 3,788 unique sequences -- the
    # descriptor table must have exactly 3,788 C1 rows, not 5,000.
    descriptor_df = pd.read_parquet(FR3_DESCRIPTOR_TABLE_PATH)
    c1_descriptors = descriptor_df[descriptor_df["pool"] == "C1"]
    assert len(c1_descriptors) == 3788
    record_df = pd.read_csv(FR3_RECORD_MAP_PATH)
    c1_records = record_df[record_df["pool"] == "C1"]
    assert len(c1_records) == 5000
    # Every C1 record's peptide_id must resolve to a row in the descriptor table.
    assert set(c1_records["peptide_id"]) == set(c1_descriptors["peptide_id"])


def test_graphpart_fold_membership_matches_the_documented_834_retained(summary):
    if not GRAPHPART_SPLITS_PATH.exists():
        pytest.skip("graphpart_splits.csv not present locally")
    record_df = pd.read_csv(FR3_RECORD_MAP_PATH)
    fr1 = record_df[record_df["pool"] == "FR1_positives"]
    assert int(fr1["graphpart_retained"].sum()) == 834
    fold_sizes = fr1[fr1["graphpart_retained"]]["graphpart_fold"].value_counts().sort_index()
    assert fold_sizes.tolist() == [124, 134, 137, 173, 266]


def test_descriptor_table_has_exactly_15_descriptor_columns_in_schema_order(summary):
    descriptor_df = pd.read_parquet(FR3_DESCRIPTOR_TABLE_PATH)
    expected_prefix = ["peptide_id", "sequence", "pool"]
    assert list(descriptor_df.columns) == expected_prefix + list(DESCRIPTOR_NAMES)


def test_all_descriptor_values_are_finite_over_the_complete_dataset(summary):
    # Full-file validation, not a sample (AGENTS.md validation rule 1).
    descriptor_df = pd.read_parquet(FR3_DESCRIPTOR_TABLE_PATH)
    values = descriptor_df[list(DESCRIPTOR_NAMES)].to_numpy(dtype=float)
    assert np.isfinite(values).all()


def test_external_control_pool_is_never_merged_into_the_unlabeled_pools(summary):
    descriptor_df = pd.read_parquet(FR3_DESCRIPTOR_TABLE_PATH)
    if "external_control" not in descriptor_df["pool"].unique():
        pytest.skip("external control not present locally")
    ext_ids = set(descriptor_df[descriptor_df["pool"] == "external_control"]["peptide_id"])
    other_ids = set(descriptor_df[descriptor_df["pool"] != "external_control"]["peptide_id"])
    assert ext_ids.isdisjoint(other_ids)


def test_validation_report_is_written_and_schema_versioned(summary):
    report = json.loads(FR3_VALIDATION_REPORT_PATH.read_text(encoding="utf-8"))
    assert report["schema_version"] == "descriptors_v1"
    assert report["n_rows"] == summary["total_descriptor_rows"]
    for name in DESCRIPTOR_NAMES:
        assert report["per_descriptor"][name]["missing"] == 0
        assert report["per_descriptor"][name]["nonfinite"] == 0


def test_schema_file_lists_exactly_the_15_frozen_descriptor_names(summary):
    schema = json.loads(FR3_DESCRIPTOR_SCHEMA_PATH.read_text(encoding="utf-8"))
    assert schema["n_descriptors"] == 15
    assert schema["descriptor_names"] == list(DESCRIPTOR_NAMES)


def test_rerunning_the_stage_is_reproducible():
    first = run_fr3_descriptors()
    second = run_fr3_descriptors()
    assert first["coverage"] == second["coverage"]
    assert first["total_descriptor_rows"] == second["total_descriptor_rows"]
    first_table = pd.read_parquet(FR3_DESCRIPTOR_TABLE_PATH)
    run_fr3_descriptors()
    second_table = pd.read_parquet(FR3_DESCRIPTOR_TABLE_PATH)
    pd.testing.assert_frame_equal(first_table, second_table)
