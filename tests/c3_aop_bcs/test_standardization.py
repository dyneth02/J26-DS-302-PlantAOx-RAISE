"""Tests for Task 3.5 sequence-record standardization."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.standardization import (
    OUTPUT_FIELDS,
    build_standardized_dataset,
    normalize_sequence,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
TEST_DIRECTORY = Path(__file__).parent
PROVENANCE_PATH = REPOSITORY_ROOT / "data" / "raw" / "c3_aop_bcs" / "PROVENANCE.json"
CANONICAL_OUTPUT_PATH = (
    REPOSITORY_ROOT / "data" / "interim" / "c3_aop_bcs" / "standardized_aop_candidates_v1.csv"
)
CANONICAL_REPORT_PATH = (
    REPOSITORY_ROOT / "data" / "interim" / "c3_aop_bcs" / "standardization_report_v1.json"
)


class StandardizationTests(unittest.TestCase):
    def test_normalize_sequence_uppercases_and_removes_all_whitespace(self):
        self.assertEqual(normalize_sequence("  aH k\nY\t"), "AHKY")
        self.assertEqual(normalize_sequence(None), "")

    def test_build_creates_deterministic_common_schema_and_report(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            directory_path = Path(directory)
            output_a = directory_path / "a.csv"
            report_a_path = directory_path / "a.json"
            output_b = directory_path / "b.csv"
            report_b_path = directory_path / "b.json"

            report_a = build_standardized_dataset(
                PROVENANCE_PATH,
                output_a,
                report_a_path,
                created_on=date(2026, 10, 18),
            )
            report_b = build_standardized_dataset(
                PROVENANCE_PATH,
                output_b,
                report_b_path,
                created_on=date(2026, 10, 18),
            )

            self.assertEqual(output_a.read_bytes(), output_b.read_bytes())
            self.assertEqual(report_a["record_count"], 3946)
            self.assertEqual(
                report_a["source_record_counts"],
                {
                    "AnOxPePred": 699,
                    "Multi-AOP:AnOxPePred": 676,
                    "Multi-AOP:AnOxPP": 1060,
                    "Multi-AOP:AOPP": 1511,
                },
            )
            self.assertEqual(
                report_a["output"]["sha256"],
                hashlib.sha256(output_a.read_bytes()).hexdigest(),
            )
            self.assertEqual(json.loads(report_a_path.read_text(encoding="utf-8")), report_a)
            self.assertEqual(report_b["output"]["sha256"], report_a["output"]["sha256"])

    def test_standardized_rows_preserve_source_mapping(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            output_path = Path(directory) / "standardized.csv"
            build_standardized_dataset(
                PROVENANCE_PATH,
                output_path,
                Path(directory) / "report.json",
                created_on=date(2026, 10, 18),
            )
            with output_path.open("r", encoding="utf-8", newline="") as csv_file:
                reader = csv.DictReader(csv_file)
                rows = list(reader)

        self.assertEqual(tuple(reader.fieldnames or ()), OUTPUT_FIELDS)
        self.assertEqual(len(rows), 3946)
        self.assertEqual(len({row["sequence_id"] for row in rows}), len(rows))
        self.assertTrue(all(row["peptide_sequence"] == row["peptide_sequence"].upper() for row in rows))
        self.assertTrue(all(not any(char.isspace() for char in row["peptide_sequence"]) for row in rows))

        first = rows[0]
        self.assertEqual(first["sequence_id"], "C3-ANOX-000001")
        self.assertEqual(first["peptide_sequence"], "AHK")
        self.assertEqual(first["source"], "AnOxPePred")
        self.assertEqual(first["source_record_id"], "0")
        self.assertEqual(first["evidence_tier_candidate"], "E1")
        self.assertEqual(first["source_reference"], "10.2174/138161207780414278")
        self.assertEqual(first["raw_row_number"], "2")

    def test_standardization_defers_cleaning_and_deduplication(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            report = build_standardized_dataset(
                PROVENANCE_PATH,
                Path(directory) / "standardized.csv",
                Path(directory) / "report.json",
                created_on=date(2026, 10, 18),
            )

        self.assertIn("exact duplicate removal", report["deferred_to_task_3_6"])
        self.assertIn("3-50 amino-acid length filtering", report["deferred_to_task_3_6"])

    def test_committed_intermediate_artifact_is_reproducible(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            regenerated_path = Path(directory) / "standardized.csv"
            regenerated_report_path = Path(directory) / "report.json"
            regenerated_report = build_standardized_dataset(
                PROVENANCE_PATH,
                regenerated_path,
                regenerated_report_path,
                created_on=date(2026, 10, 18),
            )
            regenerated_bytes = regenerated_path.read_bytes()

        canonical_report = json.loads(CANONICAL_REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(regenerated_bytes, CANONICAL_OUTPUT_PATH.read_bytes())
        self.assertEqual(regenerated_report["output"]["sha256"], canonical_report["output"]["sha256"])


if __name__ == "__main__":
    unittest.main()
