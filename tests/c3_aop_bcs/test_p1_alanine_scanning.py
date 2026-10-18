"""Tests for Task 3.11 P1 alanine scanning."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.config import load_research_config
from plantaox.c3_aop_bcs.p1_alanine_scanning import (
    build_p1_dataset,
    generate_p1_records,
)
from plantaox.c3_aop_bcs.perturbation_schema import (
    PERTURBATION_FIELDS,
    PerturbationRecord,
)
from plantaox.c3_aop_bcs.residue_annotation import (
    NON_REDOX_CLASS,
    OUTPUT_FIELDS as ANNOTATION_FIELDS,
    REDOX_CLASS,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
TEST_DIRECTORY = Path(__file__).parent
DATA_DIRECTORY = REPOSITORY_ROOT / "data" / "processed" / "c3_aop_bcs"
INPUT_PATH = DATA_DIRECTORY / "residue_annotations_v1.csv"
OUTPUT_PATH = DATA_DIRECTORY / "p1_alanine_variants_v1.csv"
REPORT_PATH = DATA_DIRECTORY / "p1_alanine_scanning_report_v1.json"


def _annotations(sequence_id: str, sequence: str, redox: set[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    redox_count = sum(residue in redox for residue in sequence)
    for position, residue in enumerate(sequence, start=1):
        row = {field: "" for field in ANNOTATION_FIELDS}
        row.update(
            sequence_id=sequence_id,
            peptide_sequence=sequence,
            sequence_length=str(len(sequence)),
            redox_residue_count=str(redox_count),
            residue_position=str(position),
            residue=residue,
            residue_class=REDOX_CLASS if residue in redox else NON_REDOX_CLASS,
            peptide_redox_position_count=str(redox_count),
        )
        rows.append(row)
    return rows


class P1AlanineScanningTests(unittest.TestCase):
    def test_one_independent_alanine_variant_is_generated_per_redox_position(self):
        redox = {"W", "Y", "H", "M", "C"}
        records = generate_p1_records(_annotations("test", "AWCH", redox), tuple(redox))

        self.assertEqual([record.position for record in records], [2, 3, 4])
        self.assertEqual([record.original_residue for record in records], ["W", "C", "H"])
        self.assertEqual([record.perturbed_sequence for record in records], ["AACH", "AWAH", "AWCA"])
        for record in records:
            self.assertEqual(record.substituted_residue, "A")
            self.assertEqual(record.perturbation_type, "P1")
            self.assertEqual(len(record.original_sequence), len(record.perturbed_sequence))
            self.assertEqual(
                sum(a != b for a, b in zip(record.original_sequence, record.perturbed_sequence)),
                1,
            )

    def test_generator_rejects_annotation_mismatches_and_duplicates(self):
        redox = ("W", "Y", "H", "M", "C")
        mismatch = _annotations("test", "AW", set(redox))
        mismatch[1]["residue"] = "Y"
        with self.assertRaisesRegex(ValueError, "residue mismatch"):
            generate_p1_records(mismatch, redox)

        duplicate = _annotations("test", "AW", set(redox))
        duplicate.append(dict(duplicate[-1]))
        with self.assertRaisesRegex(ValueError, "Duplicate annotation"):
            generate_p1_records(duplicate, redox)

    def test_build_is_byte_deterministic_and_counts_reconcile(self):
        config = load_research_config()
        rows = _annotations("one", "AW", set(config.redox_residues))
        rows += _annotations("two", "HMC", set(config.redox_residues))
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            temporary = Path(directory)
            input_path = temporary / "annotations.csv"
            with input_path.open("w", encoding="utf-8", newline="") as csv_file:
                writer = csv.DictWriter(
                    csv_file,
                    fieldnames=ANNOTATION_FIELDS,
                    lineterminator="\n",
                )
                writer.writeheader()
                writer.writerows(rows)

            generated: list[tuple[bytes, dict[str, object]]] = []
            for run in ("first", "second"):
                output = temporary / f"{run}-p1.csv"
                report = build_p1_dataset(
                    input_path=input_path,
                    output_path=output,
                    report_path=temporary / f"{run}-report.json",
                    config=config,
                    created_on=date(2026, 10, 18),
                )
                generated.append((output.read_bytes(), report))

        self.assertEqual(generated[0][0], generated[1][0])
        self.assertEqual(generated[0][1]["counts"], generated[1][1]["counts"])
        self.assertEqual(generated[0][1]["counts"]["generated_variant_count"], 4)
        self.assertEqual(
            generated[0][1]["outputs"]["p1_variants"]["sha256"],
            generated[1][1]["outputs"]["p1_variants"]["sha256"],
        )

    def test_committed_variants_cover_every_redox_annotation_once(self):
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(report["dataset_version"], "c3_aop_bcs_p1_alanine_v1")
        self.assertEqual(report["p1_rule"]["eligible_original_residues"], ["W", "Y", "H", "M", "C"])

        with INPUT_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            annotations = list(csv.DictReader(csv_file))
        with OUTPUT_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            output_reader = csv.DictReader(csv_file)
            output_rows = list(output_reader)

        self.assertEqual(tuple(output_reader.fieldnames or ()), PERTURBATION_FIELDS)
        expected = {
            (row["sequence_id"], int(row["residue_position"]))
            for row in annotations
            if row["residue_class"] == REDOX_CLASS
        }
        observed = {(row["sequence_id"], int(row["position"])) for row in output_rows}
        self.assertEqual(observed, expected)
        self.assertEqual(len(output_rows), len(expected))
        self.assertEqual(len(output_rows), report["counts"]["generated_variant_count"])

        for row in output_rows:
            record = PerturbationRecord.from_mapping(row)
            self.assertEqual(record.perturbation_type, "P1")
            self.assertIn(record.original_residue, set(report["p1_rule"]["eligible_original_residues"]))
            self.assertEqual(record.substituted_residue, "A")
            self.assertEqual(len(record.original_sequence), len(record.perturbed_sequence))

        artifact = report["outputs"]["p1_variants"]
        self.assertEqual(
            hashlib.sha256(OUTPUT_PATH.read_bytes()).hexdigest(),
            artifact["sha256"],
        )


if __name__ == "__main__":
    unittest.main()
