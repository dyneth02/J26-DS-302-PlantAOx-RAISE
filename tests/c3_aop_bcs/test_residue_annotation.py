"""Tests for Task 3.9 residue-position annotation."""

from __future__ import annotations

from collections import defaultdict
import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.config import load_research_config
from plantaox.c3_aop_bcs.redox_eligibility import OUTPUT_FIELDS as ELIGIBLE_FIELDS
from plantaox.c3_aop_bcs.residue_annotation import (
    NON_REDOX_CLASS,
    OUTPUT_FIELDS,
    REDOX_CLASS,
    annotate_residue_positions,
    build_residue_annotation_dataset,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
TEST_DIRECTORY = Path(__file__).parent
DATA_DIRECTORY = REPOSITORY_ROOT / "data" / "processed" / "c3_aop_bcs"
INPUT_PATH = DATA_DIRECTORY / "redox_eligible_sequences_v1.csv"
OUTPUT_PATH = DATA_DIRECTORY / "residue_annotations_v1.csv"
REPORT_PATH = DATA_DIRECTORY / "residue_annotation_report_v1.json"


def _record(sequence_id: str, sequence: str, redox_count: int) -> dict[str, str]:
    record = {field: "" for field in ELIGIBLE_FIELDS}
    record.update(
        sequence_id=sequence_id,
        peptide_sequence=sequence,
        source="test-source",
        sequence_length=str(len(sequence)),
        redox_residue_count=str(redox_count),
    )
    return record


class ResidueAnnotationTests(unittest.TestCase):
    def test_annotations_are_one_based_complete_and_classified(self):
        annotations, counts = annotate_residue_positions(
            [_record("peptide-one", "AWCY", 3)],
            ("W", "Y", "H", "M", "C"),
        )

        self.assertEqual([row["residue_position"] for row in annotations], [1, 2, 3, 4])
        self.assertEqual([row["residue"] for row in annotations], list("AWCY"))
        self.assertEqual(
            [row["residue_class"] for row in annotations],
            [NON_REDOX_CLASS, REDOX_CLASS, REDOX_CLASS, REDOX_CLASS],
        )
        self.assertTrue(all(row["peptide_redox_position_count"] == 3 for row in annotations))
        self.assertTrue(all(row["source"] == "test-source" for row in annotations))
        self.assertEqual(
            counts,
            {
                "peptide_count": 1,
                "annotation_count": 4,
                "redox_position_count": 3,
                "non_redox_position_count": 1,
            },
        )

    def test_annotation_rejects_ineligible_or_inconsistent_input(self):
        with self.assertRaisesRegex(ValueError, "ineligible"):
            annotate_residue_positions(
                [_record("no-redox", "ADEF", 0)],
                ("W", "Y", "H", "M", "C"),
            )
        with self.assertRaisesRegex(ValueError, "Redox count mismatch"):
            annotate_residue_positions(
                [_record("wrong-count", "AW", 2)],
                ("W", "Y", "H", "M", "C"),
            )

    def test_build_is_byte_deterministic(self):
        config = load_research_config()
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            temporary = Path(directory)
            input_path = temporary / "eligible.csv"
            with input_path.open("w", encoding="utf-8", newline="") as csv_file:
                writer = csv.DictWriter(
                    csv_file,
                    fieldnames=ELIGIBLE_FIELDS,
                    lineterminator="\n",
                )
                writer.writeheader()
                writer.writerows(
                    [_record("one", "AW", 1), _record("two", "HMC", 3)]
                )

            generated: list[tuple[bytes, dict[str, object]]] = []
            for run in ("first", "second"):
                output = temporary / f"{run}-annotations.csv"
                report = build_residue_annotation_dataset(
                    input_path=input_path,
                    output_path=output,
                    report_path=temporary / f"{run}-report.json",
                    config=config,
                    created_on=date(2026, 10, 18),
                )
                generated.append((output.read_bytes(), report))

        self.assertEqual(generated[0][0], generated[1][0])
        self.assertEqual(generated[0][1]["counts"], generated[1][1]["counts"])
        self.assertEqual(
            generated[0][1]["outputs"]["residue_annotations"]["sha256"],
            generated[1][1]["outputs"]["residue_annotations"]["sha256"],
        )

    def test_committed_annotations_reconstruct_every_source_peptide(self):
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(report["dataset_version"], "c3_aop_bcs_residue_annotations_v1")
        self.assertEqual(report["annotation_rule"]["position_index_base"], 1)
        self.assertEqual(report["annotation_rule"]["redox_residues"], ["W", "Y", "H", "M", "C"])

        with INPUT_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            input_rows = list(csv.DictReader(csv_file))
        with OUTPUT_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            output_reader = csv.DictReader(csv_file)
            output_rows = list(output_reader)

        self.assertEqual(tuple(output_reader.fieldnames or ()), OUTPUT_FIELDS)
        self.assertEqual(len(input_rows), report["counts"]["peptide_count"])
        self.assertEqual(len(output_rows), report["counts"]["annotation_count"])
        self.assertEqual(
            sum(int(row["sequence_length"]) for row in input_rows),
            len(output_rows),
        )

        by_sequence: dict[str, list[dict[str, str]]] = defaultdict(list)
        for row in output_rows:
            by_sequence[row["sequence_id"]].append(row)
        input_by_id = {row["sequence_id"]: row for row in input_rows}
        self.assertEqual(set(by_sequence), set(input_by_id))

        redox = set(report["annotation_rule"]["redox_residues"])
        observed_redox_count = 0
        for sequence_id, source in input_by_id.items():
            rows = by_sequence[sequence_id]
            self.assertEqual(
                [int(row["residue_position"]) for row in rows],
                list(range(1, len(source["peptide_sequence"]) + 1)),
            )
            self.assertEqual("".join(row["residue"] for row in rows), source["peptide_sequence"])
            expected_redox_count = sum(residue in redox for residue in source["peptide_sequence"])
            observed_redox_count += expected_redox_count
            self.assertTrue(
                all(int(row["peptide_redox_position_count"]) == expected_redox_count for row in rows)
            )
            for row in rows:
                expected_class = REDOX_CLASS if row["residue"] in redox else NON_REDOX_CLASS
                self.assertEqual(row["residue_class"], expected_class)
                for field in ELIGIBLE_FIELDS:
                    self.assertEqual(row[field], source[field])

        self.assertEqual(observed_redox_count, report["counts"]["redox_position_count"])
        artifact = report["outputs"]["residue_annotations"]
        self.assertEqual(
            hashlib.sha256(OUTPUT_PATH.read_bytes()).hexdigest(),
            artifact["sha256"],
        )


if __name__ == "__main__":
    unittest.main()
