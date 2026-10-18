"""Tests for Task 3.14 P3 random-control substitutions."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.config import STANDARD_AMINO_ACIDS, load_research_config
from plantaox.c3_aop_bcs.p3_random_controls import (
    RANDOM_SELECTION_ALGORITHM,
    build_p3_dataset,
    generate_p3_records,
    select_random_substitution,
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
OUTPUT_PATH = DATA_DIRECTORY / "p3_random_control_variants_v1.csv"
REPORT_PATH = DATA_DIRECTORY / "p3_random_controls_report_v1.json"


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


class P3RandomControlTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_research_config()

    def test_one_valid_single_position_variant_is_generated_per_annotation(self):
        redox = set(self.config.redox_residues)
        annotations = _annotations("test", "AWDG", redox)
        records = generate_p3_records(
            annotations,
            self.config.redox_residues,
            self.config.random_seed,
        )

        self.assertEqual(len(records), len(annotations))
        self.assertEqual([record.position for record in records], [1, 2, 3, 4])
        for record in records:
            self.assertEqual(record.perturbation_type, "P3")
            self.assertIn(record.substituted_residue, STANDARD_AMINO_ACIDS)
            self.assertNotEqual(record.substituted_residue, record.original_residue)
            self.assertEqual(record.random_seed, self.config.random_seed)
            self.assertIsNone(record.blosum62_score)
            metadata = json.loads(record.random_metadata)
            self.assertEqual(metadata["selection_algorithm"], RANDOM_SELECTION_ALGORITHM)
            self.assertEqual(metadata["candidate_count"], 19)
            self.assertTrue(0 <= metadata["candidate_index"] < 19)
            self.assertEqual(len(metadata["derived_seed_sha256"]), 64)
            self.assertEqual(len(record.original_sequence), len(record.perturbed_sequence))
            self.assertEqual(
                sum(
                    original != perturbed
                    for original, perturbed in zip(
                        record.original_sequence,
                        record.perturbed_sequence,
                    )
                ),
                1,
            )

    def test_choices_are_reproducible_per_position_and_change_with_seed(self):
        redox = set(self.config.redox_residues)
        annotations = _annotations("test", "AWDG", redox)
        first = generate_p3_records(annotations, self.config.redox_residues, 42)
        second = generate_p3_records(annotations, self.config.redox_residues, 42)
        reversed_records = generate_p3_records(
            reversed(annotations),
            self.config.redox_residues,
            42,
        )
        different_seed = generate_p3_records(
            annotations,
            self.config.redox_residues,
            43,
        )

        first_by_position = {record.position: record.as_dict() for record in first}
        reversed_by_position = {
            record.position: record.as_dict() for record in reversed_records
        }
        self.assertEqual(
            [record.as_dict() for record in first],
            [record.as_dict() for record in second],
        )
        self.assertEqual(first_by_position, reversed_by_position)
        self.assertNotEqual(
            [record.substituted_residue for record in first],
            [record.substituted_residue for record in different_seed],
        )

    def test_selector_validates_seed_and_position_inputs(self):
        with self.assertRaisesRegex(ValueError, "master_seed"):
            select_random_substitution("test", "AWD", 1, "A", -1)
        with self.assertRaisesRegex(ValueError, "position"):
            select_random_substitution("test", "AWD", 0, "A", 42)
        with self.assertRaisesRegex(ValueError, "does not match"):
            select_random_substitution("test", "AWD", 1, "W", 42)

    def test_generator_rejects_annotation_mismatches_and_duplicates(self):
        redox = set(self.config.redox_residues)
        mismatch = _annotations("test", "ADW", redox)
        mismatch[1]["residue"] = "E"
        with self.assertRaisesRegex(ValueError, "residue mismatch"):
            generate_p3_records(
                mismatch,
                self.config.redox_residues,
                self.config.random_seed,
            )

        wrong_class = _annotations("test", "ADW", redox)
        wrong_class[0]["residue_class"] = REDOX_CLASS
        with self.assertRaisesRegex(ValueError, "class mismatch"):
            generate_p3_records(
                wrong_class,
                self.config.redox_residues,
                self.config.random_seed,
            )

        duplicate = _annotations("test", "ADW", redox)
        duplicate.append(dict(duplicate[0]))
        with self.assertRaisesRegex(ValueError, "Duplicate annotation"):
            generate_p3_records(
                duplicate,
                self.config.redox_residues,
                self.config.random_seed,
            )

    def test_build_is_byte_deterministic_and_records_master_seed(self):
        redox = set(self.config.redox_residues)
        rows = _annotations("one", "ADW", redox)
        rows += _annotations("two", "FPY", redox)
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
                output = temporary / f"{run}-p3.csv"
                report = build_p3_dataset(
                    input_path=input_path,
                    output_path=output,
                    report_path=temporary / f"{run}-report.json",
                    config=self.config,
                    created_on=date(2026, 10, 18),
                )
                generated.append((output.read_bytes(), report))

        self.assertEqual(generated[0][0], generated[1][0])
        self.assertEqual(generated[0][1]["counts"], generated[1][1]["counts"])
        self.assertEqual(generated[0][1]["counts"]["generated_variant_count"], 6)
        self.assertEqual(
            generated[0][1]["p3_rule"]["master_random_seed"],
            self.config.random_seed,
        )
        self.assertEqual(
            generated[0][1]["outputs"]["p3_variants"]["sha256"],
            generated[1][1]["outputs"]["p3_variants"]["sha256"],
        )

    def test_committed_variants_cover_every_annotated_position_once(self):
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(report["dataset_version"], "c3_aop_bcs_p3_random_control_v1")
        self.assertEqual(
            report["p3_rule"]["master_random_seed"],
            self.config.random_seed,
        )
        self.assertEqual(
            report["p3_rule"]["selection_algorithm"],
            RANDOM_SELECTION_ALGORITHM,
        )

        with INPUT_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            annotations = list(csv.DictReader(csv_file))
        with OUTPUT_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            output_reader = csv.DictReader(csv_file)
            output_rows = list(output_reader)

        self.assertEqual(tuple(output_reader.fieldnames or ()), PERTURBATION_FIELDS)
        expected = {
            (row["sequence_id"], int(row["residue_position"]))
            for row in annotations
        }
        observed = {(row["sequence_id"], int(row["position"])) for row in output_rows}
        self.assertEqual(observed, expected)
        self.assertEqual(len(output_rows), len(expected))
        self.assertEqual(len(output_rows), report["counts"]["generated_variant_count"])

        for row in output_rows:
            record = PerturbationRecord.from_mapping(row)
            self.assertEqual(record.perturbation_type, "P3")
            self.assertEqual(record.random_seed, self.config.random_seed)
            self.assertIn(record.substituted_residue, STANDARD_AMINO_ACIDS)
            self.assertNotEqual(record.substituted_residue, record.original_residue)
            self.assertEqual(len(record.original_sequence), len(record.perturbed_sequence))

        artifact = report["outputs"]["p3_variants"]
        self.assertEqual(
            hashlib.sha256(OUTPUT_PATH.read_bytes()).hexdigest(),
            artifact["sha256"],
        )


if __name__ == "__main__":
    unittest.main()
