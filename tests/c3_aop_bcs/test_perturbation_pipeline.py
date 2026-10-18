"""Tests for Task 3.15 combined perturbation pipeline."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.blosum62 import load_blosum62
from plantaox.c3_aop_bcs.config import load_research_config
from plantaox.c3_aop_bcs.p1_alanine_scanning import generate_p1_records
from plantaox.c3_aop_bcs.perturbation_pipeline import (
    REJECTION_FIELDS,
    build_combined_perturbation_dataset,
    validate_and_partition_records,
)
from plantaox.c3_aop_bcs.perturbation_schema import (
    PERTURBATION_FIELDS,
    PERTURBATION_SCHEMA_VERSION,
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
OUTPUT_PATH = DATA_DIRECTORY / "combined_perturbations_v1.csv"
REJECTION_PATH = DATA_DIRECTORY / "combined_perturbation_rejections_v1.csv"
REPORT_PATH = DATA_DIRECTORY / "combined_perturbation_pipeline_report_v1.json"
P1_PATH = DATA_DIRECTORY / "p1_alanine_variants_v1.csv"
P2_PATH = DATA_DIRECTORY / "p2_conservative_variants_v1.csv"
P3_PATH = DATA_DIRECTORY / "p3_random_control_variants_v1.csv"


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


def _read_csv(path: Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        rows = list(reader)
        return tuple(reader.fieldnames or ()), rows


class CombinedPerturbationPipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.config = load_research_config()
        cls.matrix = load_blosum62()

    def test_validator_accepts_valid_records_and_rejects_semantic_violations(self):
        redox = set(self.config.redox_residues)
        annotations = _annotations("test", "AWD", redox)
        valid = generate_p1_records(annotations, self.config.redox_residues)[0]
        invalid_p1 = PerturbationRecord(
            schema_version=PERTURBATION_SCHEMA_VERSION,
            variant_id="invalid-p1",
            sequence_id="test",
            original_sequence="AWD",
            position=1,
            original_residue="A",
            substituted_residue="D",
            perturbed_sequence="DWD",
            perturbation_type="P1",
        )
        invalid_p2 = PerturbationRecord(
            schema_version=PERTURBATION_SCHEMA_VERSION,
            variant_id="invalid-p2",
            sequence_id="test",
            original_sequence="AWD",
            position=1,
            original_residue="A",
            substituted_residue="D",
            perturbed_sequence="DWD",
            perturbation_type="P2",
            blosum62_score=1,
        )
        invalid_p3 = PerturbationRecord(
            schema_version=PERTURBATION_SCHEMA_VERSION,
            variant_id="invalid-p3",
            sequence_id="test",
            original_sequence="AWD",
            position=3,
            original_residue="D",
            substituted_residue="E",
            perturbed_sequence="AWE",
            perturbation_type="P3",
            random_seed=self.config.random_seed,
            random_metadata="{}",
        )

        accepted, rejected = validate_and_partition_records(
            [valid, invalid_p1, invalid_p2, invalid_p3],
            annotations,
            self.config,
            self.matrix,
        )

        self.assertEqual(accepted, [valid])
        reasons = {item.record.variant_id: item.reason for item in rejected}
        self.assertIn("p1_position_not_redox", reasons["invalid-p1"])
        self.assertIn("p1_replacement_not_alanine", reasons["invalid-p1"])
        self.assertIn("p2_replacement_not_selected_candidate", reasons["invalid-p2"])
        self.assertTrue(
            "p3_replacement_not_seed_derived" in reasons["invalid-p3"]
            or "p3_random_metadata_mismatch" in reasons["invalid-p3"]
        )

    def test_validator_rejects_duplicate_variant_identifiers(self):
        annotations = _annotations("test", "AWD", set(self.config.redox_residues))
        valid = generate_p1_records(annotations, self.config.redox_residues)[0]
        accepted, rejected = validate_and_partition_records(
            [valid, valid],
            annotations,
            self.config,
            self.matrix,
        )
        self.assertEqual(accepted, [valid])
        self.assertEqual(len(rejected), 1)
        self.assertEqual(rejected[0].reason, "duplicate_variant_id")

    def test_combined_build_is_byte_deterministic_and_counts_reconcile(self):
        redox = set(self.config.redox_residues)
        rows = _annotations("one", "AWDG", redox)
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

            generated: list[tuple[bytes, bytes, dict[str, object]]] = []
            for run in ("first", "second"):
                output = temporary / f"{run}-combined.csv"
                rejection = temporary / f"{run}-rejections.csv"
                report = build_combined_perturbation_dataset(
                    input_path=input_path,
                    output_path=output,
                    rejection_path=rejection,
                    report_path=temporary / f"{run}-report.json",
                    config=self.config,
                    matrix=self.matrix,
                    created_on=date(2026, 10, 18),
                )
                generated.append((output.read_bytes(), rejection.read_bytes(), report))

        self.assertEqual(generated[0][0], generated[1][0])
        self.assertEqual(generated[0][1], generated[1][1])
        self.assertEqual(generated[0][2]["counts"], generated[1][2]["counts"])
        counts = generated[0][2]["counts"]
        self.assertEqual(
            counts["generated_by_perturbation_type"],
            {"P1": 1, "P2": 2, "P3": 4},
        )
        self.assertEqual(counts["accepted_variant_count"], 7)
        self.assertEqual(counts["rejected_variant_count"], 0)

    def test_committed_combined_output_matches_all_individual_outputs(self):
        report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
        combined_fields, combined_rows = _read_csv(OUTPUT_PATH)
        rejection_fields, rejection_rows = _read_csv(REJECTION_PATH)
        individual_rows: list[dict[str, str]] = []
        for path in (P1_PATH, P2_PATH, P3_PATH):
            fields, rows = _read_csv(path)
            self.assertEqual(fields, PERTURBATION_FIELDS)
            individual_rows.extend(rows)

        self.assertEqual(combined_fields, PERTURBATION_FIELDS)
        self.assertEqual(rejection_fields, REJECTION_FIELDS)
        self.assertEqual(combined_rows, individual_rows)
        self.assertEqual(rejection_rows, [])
        self.assertEqual(report["pipeline_version"], "c3_aop_bcs_perturbation_pipeline_v1")
        self.assertEqual(
            report["dataset_version"],
            "c3_aop_bcs_combined_perturbations_v1",
        )
        self.assertEqual(
            report["counts"]["generated_by_perturbation_type"],
            {"P1": 1180, "P2": 3276, "P3": 5580},
        )
        self.assertEqual(report["counts"]["accepted_variant_count"], 10036)
        self.assertEqual(report["counts"]["rejected_variant_count"], 0)

        for row in combined_rows:
            PerturbationRecord.from_mapping(row)

        self.assertEqual(
            hashlib.sha256(OUTPUT_PATH.read_bytes()).hexdigest(),
            report["outputs"]["accepted_perturbations"]["sha256"],
        )
        self.assertEqual(
            hashlib.sha256(REJECTION_PATH.read_bytes()).hexdigest(),
            report["outputs"]["rejected_perturbations"]["sha256"],
        )


if __name__ == "__main__":
    unittest.main()
