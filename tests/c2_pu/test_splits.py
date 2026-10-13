"""Tests for curation.splits's GraphPart output parsing and report building.

These test the parsing/reporting LOGIC against synthetic fixtures matching
GraphPart's real output schema (verified against the installed package's
source, not guessed) and do not require graphpart/needleall to be installed.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pytest

from plantaox.c2_pu.common.io import read_fasta
from plantaox.c2_pu.curation.splits import build_split_report, load_graphpart_splits, write_stratified_fasta


@pytest.fixture
def sample_splits_csv(tmp_path: Path) -> Path:
    path = tmp_path / "splits.csv"
    pd.DataFrame(
        {
            "AC": ["AOP-A", "AOP-B", "AOP-C", "AOP-D", "AOP-E", "AOP-F"],
            "label-val": [0, 0, 0, 0, 0, 0],
            "cluster": [0, 0, 1, 1, 2, 2],
        }
    ).set_index("AC").to_csv(path)
    return path


@pytest.fixture
def sample_graphpart_report(tmp_path: Path) -> Path:
    path = tmp_path / "splits_report.json"
    report = {
        "labels_start": {"0": {"val": 0, "num": 6, "lim": 1}},
        "partitioning_pre_removal": {},
        "samples_pre_removal": 7,
        "score_pre_removal": 0.9,
        "removal_step_1": {0: {"Min-threshold": 0.41, "#Problematics": 1, "#Relocated": 0, "#To-be-removed": 1}},
    }
    path.write_text(json.dumps(report), encoding="utf-8")
    return path


def test_load_graphpart_splits_renames_cluster_to_fold(sample_splits_csv):
    df = load_graphpart_splits(sample_splits_csv)
    assert list(df.columns) == ["peptide_id", "fold"]
    assert set(df["peptide_id"]) == {"AOP-A", "AOP-B", "AOP-C", "AOP-D", "AOP-E", "AOP-F"}
    assert df.set_index("peptide_id").loc["AOP-C", "fold"] == 1


def test_load_graphpart_splits_requires_cluster_column(tmp_path):
    bad = tmp_path / "bad.csv"
    pd.DataFrame({"AC": ["AOP-A"], "something_else": [1]}).set_index("AC").to_csv(bad)
    with pytest.raises(ValueError, match="cluster"):
        load_graphpart_splits(bad)


def test_build_split_report_counts(sample_splits_csv, sample_graphpart_report):
    splits_df = load_graphpart_splits(sample_splits_csv)
    # "AOP-G" exists in the curated positive pool but was removed by GraphPart
    # to resolve a cross-fold homology violation -- it has no fold assignment.
    positive_df = pd.DataFrame(
        {
            "peptide_id": ["AOP-A", "AOP-B", "AOP-C", "AOP-D", "AOP-E", "AOP-F", "AOP-G"],
            "sequence": ["AAAAK", "BBBBK", "CCCCL", "DDDDM", "EEEEN", "FFFFP", "GGGGQ"],
            "length": [5] * 7,
            "evidence_tier": ["E1", "E2", "E1", "E1", "E2", "E2", "E1"],
        }
    )
    report, excluded_df = build_split_report(
        splits_df, positive_df, sample_graphpart_report, n_partitions_requested=3
    )
    assert report["n_sequences"] == 6
    assert report["n_partitions_produced"] == 3
    assert report["fold_sizes"] == {"0": 2, "1": 2, "2": 2}
    assert report["fold_evidence_tier_counts"]["0"] == {"E1": 1, "E2": 1}
    assert report["any_homology_violation_removal_needed"] is True
    assert report["n_sequences_removed_for_homology"] == 1  # 7 pre-removal -> 6 final
    assert list(excluded_df["peptide_id"]) == ["AOP-G"]
    assert excluded_df.iloc[0]["exclusion_reason"] == "graphpart_cross_fold_homology_violation"


def test_write_stratified_fasta_embeds_tier_metadata(tmp_path):
    out_path = tmp_path / "stratified.fasta"
    write_stratified_fasta(["AOP-A", "AOP-B"], ["AAAK", "CCCL"], ["E1", "E2"], out_path)
    records = read_fasta(out_path)
    assert records == [("AOP-A|tier=E1", "AAAK"), ("AOP-B|tier=E2", "CCCL")]


def test_build_split_report_flags_no_removal_when_clean(sample_splits_csv, tmp_path):
    splits_df = load_graphpart_splits(sample_splits_csv)
    positive_df = pd.DataFrame(
        {
            "peptide_id": splits_df["peptide_id"],
            "sequence": ["AAAAK"] * 6,
            "length": [5] * 6,
            "evidence_tier": ["E1"] * 6,
        }
    )
    clean_report_path = tmp_path / "clean_report.json"
    clean_report_path.write_text(
        json.dumps({"samples_pre_removal": 6, "removal_step_1": {}}), encoding="utf-8"
    )
    report, excluded_df = build_split_report(
        splits_df, positive_df, clean_report_path, n_partitions_requested=3
    )
    assert report["any_homology_violation_removal_needed"] is False
    assert report["n_sequences_removed_for_homology"] == 0
    assert excluded_df.empty
