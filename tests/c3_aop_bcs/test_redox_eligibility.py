"""Tests for Task 3.8 redox-residue eligibility filtering."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.config import load_research_config
from plantaox.c3_aop_bcs.identity_deduplication import REPRESENTATIVE_FIELDS
from plantaox.c3_aop_bcs.redox_eligibility import (
    EXCLUSION_FIELDS,
    EXCLUSION_REASON,
    OUTPUT_FIELDS,
    build_redox_eligible_dataset,
    detect_redox_residues,
    filter_redox_eligible_records,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
TEST_DIRECTORY = Path(__file__).parent
DATA_DIRECTORY = REPOSITORY_ROOT / "data" / "processed" / "c3_aop_bcs"
INPUT_PATH = DATA_DIRECTORY / "cd_hit_representatives_90_v1.csv"
OUTPUT_PATH = DATA_DIRECTORY / "redox_eligible_sequences_v1.csv"
EXCLUSIONS_PATH = DATA_DIRECTORY / "redox_eligibility_exclusions_v1.csv"
REPORT_PATH = DATA_DIRECTORY / "redox_eligibility_report_v1.json"


def _record(sequence_id: str, sequence: str) -> dict[str, str]:
    record = {field: "" for field in REPRESENTATIVE_FIELDS}
    record.update(sequence_id=sequence_id, peptide_sequence=sequence)
    return record


class RedoxEligibilityTests(unittest.TestCase):
    def test_detection_counts_occurrences_and_preserves_config_order(self):
        count, present = detect_redox_residues("MCYWWH", ("W", "Y", "H", "M", "C"))
        self.assertEqual(count, 6)
        self.assertEqual(present, ("W", "Y", "H", "M", "C"))

    def test_filter_retains_only_eligible_records_and_preserves_provenance(self):
        records = [
            {**_record("eligible", "ACDEW"), "source": "source-a"},
            {**_record("excluded", "ADEFK"), "source": "source-b"},
        ]
        eligible, exclusions, counts = filter_redox_eligible_records(
            records,
            ("W", "Y", "H", "M", "C"),
        )

        self.assertEqual([record["sequence_id"] for record in eligible], ["eligible"])
        self.assertEqual(eligible[0]["source"], "source-a")
        self.assertEqual(eligible[0]["redox_residue_count"], 2)
        self.assertEqual(eligible[0]["redox_residues_present"], "WC")
        self.assertEqual(exclusions[0]["source"], "source-b")
        self.assertEqual(exclusions[0]["exclusion_reason"], EXCLUSION_REASON)
        self.assertEqual(
            counts,
            {
                "input_count": 2,
                "eligible_count": 1,
                "rejected_no_redox_residue_count": 1,
            },
        )

    def test_build_is_byte_deterministic(self):
        config = load_research_config()
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            temporary = Path(directory)
            input_path = temporary / "input.csv"
            with input_path.open("w", encoding="utf-8", newline="") as csv_file:
                writer = csv.DictWriter(
                    csv_file,
                    fieldnames=REPRESENTATIVE_FIELDS,
                    lineterminator="\n",
                )
                writer.writeheader()
                writer.writerows([_record("one", "WYH"), _record("two", "ADEF")])

            generated: list[tuple[bytes, bytes, dict[str, object]]] = []
            for run in ("first", "second"):
                output = temporary / f"{run}-eligible.csv"
                exclusions = temporary / f"{run}-exclusions.csv"
                report = build_redox_eligible_dataset(
                    input_path=input_path,
                    output_path=output,
                    exclusions_path=exclusions,
                    report_path=temporary / f"{run}-report.json",
                    config=config,
                    created_on=date(2026, 10, 18),
                )
                generated.append((output.read_bytes(), exclusions.read_bytes(), report))

        self.assertEqual(generated[0][:2], generated[1][:2])
        self.assertEqual(generated[0][2]["counts"], generated[1][2]["counts"])
        self.assertEqual(
            generated[0][2]["outputs"]["eligible"]["sha256"],
            generated[1][2]["outputs"]["eligible"]["sha256"],
        )
        self.assertEqual(
            generated[0][2]["outputs"]["exclusions"]["sha256"],
            generated[1][2]["outputs"]["exclusions"]["sha256"],
        )

    def test_committed_artifacts_are_complete_traceable_and_eligible(self):
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(report["dataset_version"], "c3_aop_bcs_redox_eligible_v1")
        self.assertEqual(report["eligibility_rule"]["redox_residues"], ["W", "Y", "H", "M", "C"])

        with INPUT_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            input_rows = list(csv.DictReader(csv_file))
        with OUTPUT_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            eligible_reader = csv.DictReader(csv_file)
            eligible_rows = list(eligible_reader)
        with EXCLUSIONS_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            exclusions_reader = csv.DictReader(csv_file)
            exclusion_rows = list(exclusions_reader)

        counts = report["counts"]
        self.assertEqual(tuple(eligible_reader.fieldnames or ()), OUTPUT_FIELDS)
        self.assertEqual(tuple(exclusions_reader.fieldnames or ()), EXCLUSION_FIELDS)
        self.assertEqual(len(input_rows), counts["input_count"])
        self.assertEqual(len(eligible_rows), counts["eligible_count"])
        self.assertEqual(len(exclusion_rows), counts["rejected_no_redox_residue_count"])
        self.assertEqual(len(eligible_rows) + len(exclusion_rows), len(input_rows))

        redox = set(report["eligibility_rule"]["redox_residues"])
        self.assertTrue(all(set(row["peptide_sequence"]) & redox for row in eligible_rows))
        self.assertTrue(all(not (set(row["peptide_sequence"]) & redox) for row in exclusion_rows))
        self.assertTrue(all(row["exclusion_reason"] == EXCLUSION_REASON for row in exclusion_rows))

        input_by_id = {row["sequence_id"]: row for row in input_rows}
        for row in eligible_rows + exclusion_rows:
            source = input_by_id[row["sequence_id"]]
            for field in REPRESENTATIVE_FIELDS:
                self.assertEqual(row[field], source[field])

        for artifact in report["outputs"].values():
            artifact_path = REPOSITORY_ROOT / artifact["path"]
            self.assertEqual(
                hashlib.sha256(artifact_path.read_bytes()).hexdigest(),
                artifact["sha256"],
            )


if __name__ == "__main__":
    unittest.main()
