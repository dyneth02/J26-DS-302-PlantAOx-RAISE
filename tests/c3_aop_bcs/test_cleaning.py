"""Tests for Task 3.6 sequence validation and cleaning."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.cleaning import (
    EXCLUSION_FIELDS,
    OUTPUT_FIELDS,
    build_cleaned_dataset,
    clean_records,
    validate_sequence,
)
from plantaox.c3_aop_bcs.config import STANDARD_AMINO_ACIDS, load_research_config
from plantaox.c3_aop_bcs.standardization import OUTPUT_FIELDS as STANDARDIZED_FIELDS


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
TEST_DIRECTORY = Path(__file__).parent
INPUT_PATH = (
    REPOSITORY_ROOT / "data" / "interim" / "c3_aop_bcs" / "standardized_aop_candidates_v1.csv"
)
CANONICAL_OUTPUT_PATH = (
    REPOSITORY_ROOT / "data" / "processed" / "c3_aop_bcs" / "cleaned_aop_sequences_v1.csv"
)
CANONICAL_EXCLUSIONS_PATH = (
    REPOSITORY_ROOT / "data" / "processed" / "c3_aop_bcs" / "sequence_cleaning_exclusions_v1.csv"
)
CANONICAL_REPORT_PATH = (
    REPOSITORY_ROOT / "data" / "processed" / "c3_aop_bcs" / "sequence_cleaning_report_v1.json"
)


def _record(sequence_id: str, sequence: str, tier: str = "E2") -> dict[str, str]:
    record = {field: "" for field in STANDARDIZED_FIELDS}
    record.update(
        sequence_id=sequence_id,
        peptide_sequence=sequence,
        source="test",
        evidence_tier_candidate=tier,
    )
    return record


class SequenceCleaningTests(unittest.TestCase):
    def test_validate_sequence_applies_missing_alphabet_and_inclusive_length_rules(self):
        self.assertEqual(validate_sequence("", 3, 50), ("missing_sequence", ()))
        self.assertEqual(validate_sequence(None, 3, 50), ("missing_sequence", ()))
        self.assertEqual(validate_sequence("ABXZ", 3, 50), ("invalid_amino_acid", ("B", "X", "Z")))
        self.assertEqual(validate_sequence("AA", 3, 50), ("length_out_of_range", ()))
        self.assertEqual(validate_sequence("A" * 51, 3, 50), ("length_out_of_range", ()))
        self.assertEqual(validate_sequence("ACD", 3, 50), (None, ()))
        self.assertEqual(validate_sequence("A" * 50, 3, 50), (None, ()))

    def test_clean_records_uses_exclusive_reasons_and_prefers_e1_duplicate(self):
        records = [
            _record("e2-first", "ACDE", "E2"),
            _record("missing", ""),
            _record("invalid", "AXZ"),
            _record("short", "AA"),
            _record("e1-retained", "ACDE", "E1"),
        ]

        retained, exclusions, counts = clean_records(records, load_research_config())

        self.assertEqual([row["sequence_id"] for row in retained], ["e1-retained"])
        self.assertEqual(
            counts,
            {
                "original_count": 5,
                "missing_count": 1,
                "invalid_count": 1,
                "out_of_range_count": 1,
                "exact_duplicate_count": 1,
                "retained_count": 1,
            },
        )
        duplicate = next(row for row in exclusions if row["exclusion_reason"] == "exact_duplicate")
        self.assertEqual(duplicate["sequence_id"], "e2-first")
        self.assertEqual(duplicate["retained_sequence_id"], "e1-retained")

    def test_build_is_deterministic_and_report_counts_reconcile(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            root = Path(directory)
            first_output, second_output = root / "first.csv", root / "second.csv"
            first_exclusions, second_exclusions = root / "first-excluded.csv", root / "second-excluded.csv"
            first_report_path, second_report_path = root / "first.json", root / "second.json"

            first_report = build_cleaned_dataset(
                INPUT_PATH,
                first_output,
                first_exclusions,
                first_report_path,
                created_on=date(2026, 10, 18),
            )
            second_report = build_cleaned_dataset(
                INPUT_PATH,
                second_output,
                second_exclusions,
                second_report_path,
                created_on=date(2026, 10, 18),
            )

            self.assertEqual(first_output.read_bytes(), second_output.read_bytes())
            self.assertEqual(first_exclusions.read_bytes(), second_exclusions.read_bytes())
            self.assertEqual(first_report["counts"], second_report["counts"])
            counts = first_report["counts"]
            self.assertEqual(
                counts["original_count"],
                counts["missing_count"]
                + counts["invalid_count"]
                + counts["out_of_range_count"]
                + counts["exact_duplicate_count"]
                + counts["retained_count"],
            )
            self.assertEqual(json.loads(first_report_path.read_text(encoding="utf-8")), first_report)

    def test_committed_cleaned_artifacts_are_valid_unique_and_reproducible(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            root = Path(directory)
            regenerated_output = root / "cleaned.csv"
            regenerated_exclusions = root / "excluded.csv"
            regenerated_report = build_cleaned_dataset(
                INPUT_PATH,
                regenerated_output,
                regenerated_exclusions,
                root / "report.json",
                created_on=date(2026, 10, 18),
            )
            regenerated_output_bytes = regenerated_output.read_bytes()
            regenerated_exclusion_bytes = regenerated_exclusions.read_bytes()

        canonical_report = json.loads(CANONICAL_REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(regenerated_output_bytes, CANONICAL_OUTPUT_PATH.read_bytes())
        self.assertEqual(regenerated_exclusion_bytes, CANONICAL_EXCLUSIONS_PATH.read_bytes())
        self.assertEqual(regenerated_report["counts"], canonical_report["counts"])
        self.assertEqual(
            regenerated_report["outputs"]["cleaned"]["sha256"],
            hashlib.sha256(CANONICAL_OUTPUT_PATH.read_bytes()).hexdigest(),
        )

        with CANONICAL_OUTPUT_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            rows = list(reader)
        self.assertEqual(tuple(reader.fieldnames or ()), OUTPUT_FIELDS)
        sequences = [row["peptide_sequence"] for row in rows]
        self.assertEqual(len(sequences), len(set(sequences)))
        self.assertTrue(all(3 <= len(sequence) <= 50 for sequence in sequences))
        self.assertTrue(all(set(sequence) <= STANDARD_AMINO_ACIDS for sequence in sequences))

        with CANONICAL_EXCLUSIONS_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            exclusions_reader = csv.DictReader(csv_file)
            exclusions = list(exclusions_reader)
        self.assertEqual(tuple(exclusions_reader.fieldnames or ()), EXCLUSION_FIELDS)
        self.assertEqual(len(exclusions), canonical_report["outputs"]["exclusions"]["record_count"])


if __name__ == "__main__":
    unittest.main()
