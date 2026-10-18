"""Tests for Task 3.7 CD-HIT identity deduplication."""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.cleaning import OUTPUT_FIELDS as CLEANED_FIELDS
from plantaox.c3_aop_bcs.identity_deduplication import (
    CLUSTER_FIELDS,
    REPRESENTATIVE_FIELDS,
    build_representative_records,
    parse_cd_hit_clusters,
    read_fasta,
    write_fasta,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
TEST_DIRECTORY = Path(__file__).parent
DATA_DIRECTORY = REPOSITORY_ROOT / "data" / "processed" / "c3_aop_bcs"
CLEANED_PATH = DATA_DIRECTORY / "cleaned_aop_sequences_v1.csv"
INPUT_FASTA_PATH = DATA_DIRECTORY / "cd_hit_input_v1.fasta"
REPRESENTATIVE_FASTA_PATH = DATA_DIRECTORY / "cd_hit_representatives_90_v1.fasta"
CLUSTER_PATH = DATA_DIRECTORY / "cd_hit_representatives_90_v1.fasta.clstr"
REPRESENTATIVE_CSV_PATH = DATA_DIRECTORY / "cd_hit_representatives_90_v1.csv"
CLUSTER_CSV_PATH = DATA_DIRECTORY / "cd_hit_clusters_90_v1.csv"
REPORT_PATH = DATA_DIRECTORY / "cd_hit_deduplication_report_v1.json"


def _record(sequence_id: str, sequence: str) -> dict[str, str]:
    record = {field: "" for field in CLEANED_FIELDS}
    record.update(
        sequence_id=sequence_id,
        peptide_sequence=sequence,
        sequence_length=str(len(sequence)),
    )
    return record


class IdentityDeduplicationTests(unittest.TestCase):
    def test_fasta_generation_is_deterministic_and_round_trips(self):
        records = [_record("C3-TEST-000001", "ACDE"), _record("C3-TEST-000002", "WYHM")]
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            first = Path(directory) / "first.fasta"
            second = Path(directory) / "second.fasta"
            self.assertEqual(write_fasta(records, first), 2)
            self.assertEqual(write_fasta(records, second), 2)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(
                read_fasta(first),
                [("C3-TEST-000001", "ACDE"), ("C3-TEST-000002", "WYHM")],
            )

    def test_native_cluster_parser_preserves_representatives_and_identity(self):
        content = """>Cluster 0
0 4aa, >C3-TEST-000001... *
1 4aa, >C3-TEST-000002... at 100.00%
>Cluster 1
0 3aa, >C3-TEST-000003... *
"""
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            cluster_path = Path(directory) / "test.clstr"
            cluster_path.write_text(content, encoding="utf-8", newline="\n")
            memberships = parse_cd_hit_clusters(cluster_path)

        self.assertEqual(len(memberships), 3)
        self.assertEqual(memberships[0]["is_representative"], "true")
        self.assertEqual(memberships[1]["identity_to_representative_percent"], "100.00")
        self.assertEqual(memberships[2]["cd_hit_cluster_id"], 1)

    def test_representatives_rejoin_the_cleaned_schema(self):
        cleaned = [_record("one", "ACDE"), _record("two", "ACDF"), _record("three", "WYH")]
        memberships = [
            {
                "cd_hit_cluster_id": 0,
                "sequence_id": "one",
                "is_representative": "true",
            },
            {
                "cd_hit_cluster_id": 0,
                "sequence_id": "two",
                "is_representative": "false",
            },
            {
                "cd_hit_cluster_id": 1,
                "sequence_id": "three",
                "is_representative": "true",
            },
        ]

        representatives = build_representative_records(
            cleaned,
            [("one", "ACDE"), ("three", "WYH")],
            memberships,
        )

        self.assertEqual([row["sequence_id"] for row in representatives], ["one", "three"])
        self.assertEqual(representatives[0]["cd_hit_cluster_size"], 2)
        self.assertEqual(representatives[1]["cd_hit_cluster_size"], 1)

    def test_committed_cd_hit_artifacts_are_complete_and_traceable(self):
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        counts = report["counts"]
        self.assertEqual(report["dataset_version"], "c3_aop_bcs_cd_hit_90_v1")
        self.assertEqual(report["tool"]["name"], "CD-HIT")
        self.assertEqual(report["tool"]["version"], "4.8.1")
        self.assertEqual(report["parameters"]["identity_threshold"], 0.9)
        self.assertEqual(counts["input_count"], 1473)
        self.assertEqual(counts["representative_count"], counts["cluster_count"])
        self.assertEqual(
            counts["input_count"],
            counts["representative_count"] + counts["removed_at_90_percent_identity"],
        )

        cleaned_ids = set()
        with CLEANED_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            for row in csv.DictReader(csv_file):
                cleaned_ids.add(row["sequence_id"])
        input_records = read_fasta(INPUT_FASTA_PATH)
        self.assertEqual(len(input_records), counts["input_count"])
        self.assertEqual({sequence_id for sequence_id, _ in input_records}, cleaned_ids)

        native_memberships = parse_cd_hit_clusters(CLUSTER_PATH)
        self.assertEqual(len(native_memberships), counts["input_count"])
        self.assertEqual(
            {str(row["sequence_id"]) for row in native_memberships},
            cleaned_ids,
        )
        representative_ids = {
            str(row["sequence_id"])
            for row in native_memberships
            if row["is_representative"] == "true"
        }
        self.assertEqual(len(representative_ids), counts["representative_count"])
        self.assertEqual(
            {sequence_id for sequence_id, _ in read_fasta(REPRESENTATIVE_FASTA_PATH)},
            representative_ids,
        )

        with REPRESENTATIVE_CSV_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            representative_reader = csv.DictReader(csv_file)
            representative_rows = list(representative_reader)
        self.assertEqual(tuple(representative_reader.fieldnames or ()), REPRESENTATIVE_FIELDS)
        self.assertEqual(len(representative_rows), counts["representative_count"])
        self.assertEqual({row["sequence_id"] for row in representative_rows}, representative_ids)

        with CLUSTER_CSV_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            cluster_reader = csv.DictReader(csv_file)
            cluster_rows = list(cluster_reader)
        self.assertEqual(tuple(cluster_reader.fieldnames or ()), CLUSTER_FIELDS)
        self.assertEqual(len(cluster_rows), counts["input_count"])

        for artifact in report["outputs"].values():
            artifact_path = REPOSITORY_ROOT / artifact["path"]
            self.assertEqual(hashlib.sha256(artifact_path.read_bytes()).hexdigest(), artifact["sha256"])


if __name__ == "__main__":
    unittest.main()
