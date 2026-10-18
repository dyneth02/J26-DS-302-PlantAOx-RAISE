"""Tests for Task 3.13 P2 BLOSUM62-conservative substitutions."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.blosum62 import (
    MINIMUM_CONSERVATIVE_SCORE,
    load_blosum62,
    select_conservative_substitution,
)
from plantaox.c3_aop_bcs.config import load_research_config
from plantaox.c3_aop_bcs.p2_conservative_substitutions import (
    build_p2_dataset,
    generate_p2_records,
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
OUTPUT_PATH = DATA_DIRECTORY / "p2_conservative_variants_v1.csv"
REPORT_PATH = DATA_DIRECTORY / "p2_conservative_substitutions_report_v1.json"


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


class P2ConservativeSubstitutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_research_config()
        cls.matrix = load_blosum62()

    def test_variants_are_generated_only_for_selectable_non_redox_positions(self):
        redox = set(self.config.redox_residues)
        records = generate_p2_records(
            _annotations("test", "ADGWH", redox),
            self.matrix,
            self.config.redox_residues,
        )

        self.assertEqual([record.position for record in records], [1, 2])
        self.assertEqual(
            [
                (record.original_residue, record.substituted_residue, record.blosum62_score)
                for record in records
            ],
            [("A", "S", 1), ("D", "E", 2)],
        )
        for record in records:
            self.assertEqual(record.perturbation_type, "P2")
            self.assertNotIn(record.original_residue, redox)
            self.assertNotEqual(record.substituted_residue, "A")
            self.assertNotIn(record.substituted_residue, redox)
            self.assertGreaterEqual(record.blosum62_score, MINIMUM_CONSERVATIVE_SCORE)
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

    def test_generator_rejects_annotation_mismatches_and_duplicates(self):
        redox = set(self.config.redox_residues)
        mismatch = _annotations("test", "ADW", redox)
        mismatch[1]["residue"] = "E"
        with self.assertRaisesRegex(ValueError, "residue mismatch"):
            generate_p2_records(mismatch, self.matrix, self.config.redox_residues)

        wrong_class = _annotations("test", "ADW", redox)
        wrong_class[0]["residue_class"] = REDOX_CLASS
        with self.assertRaisesRegex(ValueError, "class mismatch"):
            generate_p2_records(wrong_class, self.matrix, self.config.redox_residues)

        duplicate = _annotations("test", "ADW", redox)
        duplicate.append(dict(duplicate[0]))
        with self.assertRaisesRegex(ValueError, "Duplicate annotation"):
            generate_p2_records(duplicate, self.matrix, self.config.redox_residues)

    def test_build_is_byte_deterministic_and_counts_skipped_positions(self):
        redox = set(self.config.redox_residues)
        rows = _annotations("one", "ADGW", redox)
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
                output = temporary / f"{run}-p2.csv"
                report = build_p2_dataset(
                    input_path=input_path,
                    output_path=output,
                    report_path=temporary / f"{run}-report.json",
                    config=self.config,
                    matrix=self.matrix,
                    created_on=date(2026, 10, 18),
                )
                generated.append((output.read_bytes(), report))

        self.assertEqual(generated[0][0], generated[1][0])
        self.assertEqual(generated[0][1]["counts"], generated[1][1]["counts"])
        self.assertEqual(generated[0][1]["counts"]["input_non_redox_position_count"], 5)
        self.assertEqual(generated[0][1]["counts"]["generated_variant_count"], 2)
        self.assertEqual(
            generated[0][1]["counts"]["skipped_no_candidate_position_count"],
            3,
        )
        self.assertEqual(
            generated[0][1]["outputs"]["p2_variants"]["sha256"],
            generated[1][1]["outputs"]["p2_variants"]["sha256"],
        )

    def test_committed_variants_cover_each_selectable_non_redox_position_once(self):
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(report["dataset_version"], "c3_aop_bcs_p2_conservative_v1")
        self.assertEqual(report["p2_rule"]["minimum_blosum62_score"], 1)
        self.assertEqual(report["p2_rule"]["no_candidate_action"], "skip_position")

        with INPUT_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            annotations = list(csv.DictReader(csv_file))
        with OUTPUT_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            output_reader = csv.DictReader(csv_file)
            output_rows = list(output_reader)

        self.assertEqual(tuple(output_reader.fieldnames or ()), PERTURBATION_FIELDS)
        expected: dict[tuple[str, int], tuple[str, int]] = {}
        for row in annotations:
            if row["residue_class"] != NON_REDOX_CLASS:
                continue
            selection = select_conservative_substitution(
                row["residue"],
                self.matrix,
                self.config.redox_residues,
            )
            if selection is not None:
                expected[(row["sequence_id"], int(row["residue_position"]))] = (
                    selection.residue,
                    selection.score,
                )

        observed = {
            (row["sequence_id"], int(row["position"])): (
                row["substituted_residue"],
                int(row["blosum62_score"]),
            )
            for row in output_rows
        }
        self.assertEqual(observed, expected)
        self.assertEqual(len(output_rows), len(expected))
        self.assertEqual(len(output_rows), report["counts"]["generated_variant_count"])

        redox = set(self.config.redox_residues)
        for row in output_rows:
            record = PerturbationRecord.from_mapping(row)
            self.assertEqual(record.perturbation_type, "P2")
            self.assertNotIn(record.original_residue, redox)
            self.assertNotEqual(record.substituted_residue, "A")
            self.assertNotIn(record.substituted_residue, redox)
            self.assertGreaterEqual(record.blosum62_score, 1)
            self.assertEqual(len(record.original_sequence), len(record.perturbed_sequence))

        artifact = report["outputs"]["p2_variants"]
        self.assertEqual(
            hashlib.sha256(OUTPUT_PATH.read_bytes()).hexdigest(),
            artifact["sha256"],
        )


if __name__ == "__main__":
    unittest.main()
