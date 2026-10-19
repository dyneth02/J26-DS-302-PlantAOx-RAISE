"""Tests for Task 3.25 deterministic PP1 pilot selection."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.config import load_research_config
from plantaox.c3_aop_bcs.perturbation_schema import PERTURBATION_FIELDS
from plantaox.c3_aop_bcs.pilot_subset import (
    DEFAULT_PERTURBATION_INPUT_PATH,
    DEFAULT_PERTURBATION_OUTPUT_PATH,
    DEFAULT_REPORT_PATH,
    DEFAULT_SUBJECT_INPUT_PATH,
    DEFAULT_SUBJECT_OUTPUT_PATH,
    LENGTH_BANDS,
    PILOT_SUBJECT_FIELDS,
    build_pp1_pilot_subset,
    select_pilot_subjects,
)


class PilotSubsetTests(unittest.TestCase):
    def test_committed_pilot_has_configured_size_and_required_coverage(self):
        config = load_research_config()
        report = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
        with DEFAULT_SUBJECT_OUTPUT_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            subjects = list(reader)
            fields = tuple(reader.fieldnames or ())

        self.assertEqual(fields, PILOT_SUBJECT_FIELDS)
        self.assertEqual(len(subjects), config.pilot_dataset_size)
        self.assertTrue(10 <= len(subjects) <= 30)
        self.assertEqual({row["selection_seed"] for row in subjects}, {str(config.random_seed)})
        self.assertEqual(set(report["coverage"]["redox_residue_subject_counts"]), set(config.redox_residues))
        self.assertTrue(all(report["coverage"]["redox_residue_subject_counts"].values()))
        self.assertEqual(
            set(report["coverage"]["redox_pattern_type_counts"]),
            {"single_type", "multiple_types"},
        )
        self.assertTrue(all(report["coverage"]["length_band_counts"][label] for label, _, _ in LENGTH_BANDS))

    def test_selection_is_independent_of_input_row_order(self):
        config = load_research_config()
        with DEFAULT_SUBJECT_INPUT_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            subjects = list(csv.DictReader(csv_file))
        variant_types: dict[str, set[str]] = {}
        with DEFAULT_PERTURBATION_INPUT_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            for row in csv.DictReader(csv_file):
                variant_types.setdefault(row["sequence_id"], set()).add(row["perturbation_type"])

        forward = select_pilot_subjects(subjects, variant_types, config)
        reverse = select_pilot_subjects(list(reversed(subjects)), variant_types, config)
        self.assertEqual(forward, reverse)

    def test_pilot_perturbations_are_complete_and_linked(self):
        with DEFAULT_SUBJECT_OUTPUT_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            subjects = {row["sequence_id"]: row for row in csv.DictReader(csv_file)}
        with DEFAULT_PERTURBATION_OUTPUT_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            perturbations = list(reader)
            fields = tuple(reader.fieldnames or ())

        self.assertEqual(fields, PERTURBATION_FIELDS)
        self.assertTrue(perturbations)
        self.assertEqual({row["perturbation_type"] for row in perturbations}, {"P1", "P2", "P3"})
        self.assertTrue(all(row["sequence_id"] in subjects for row in perturbations))
        self.assertTrue(
            all(
                row["original_sequence"] == subjects[row["sequence_id"]]["peptide_sequence"]
                for row in perturbations
            )
        )

    def test_committed_outputs_match_report_hashes_and_regenerate_identically(self):
        report = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            hashlib.sha256(DEFAULT_SUBJECT_OUTPUT_PATH.read_bytes()).hexdigest(),
            report["outputs"]["subjects"]["sha256"],
        )
        self.assertEqual(
            hashlib.sha256(DEFAULT_PERTURBATION_OUTPUT_PATH.read_bytes()).hexdigest(),
            report["outputs"]["perturbations"]["sha256"],
        )

        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            temporary = Path(directory)
            generated = build_pp1_pilot_subset(
                subject_output_path=temporary / "subjects.csv",
                perturbation_output_path=temporary / "perturbations.csv",
                report_path=temporary / "report.json",
                created_on=date.fromisoformat(report["created_on"]),
            )
            self.assertEqual((temporary / "subjects.csv").read_bytes(), DEFAULT_SUBJECT_OUTPUT_PATH.read_bytes())
            self.assertEqual(
                (temporary / "perturbations.csv").read_bytes(),
                DEFAULT_PERTURBATION_OUTPUT_PATH.read_bytes(),
            )
            generated["outputs"]["subjects"]["path"] = report["outputs"]["subjects"]["path"]
            generated["outputs"]["perturbations"]["path"] = report["outputs"]["perturbations"]["path"]
            self.assertEqual(generated, report)


if __name__ == "__main__":
    unittest.main()
