"""Tests for Task 3.26 per-perturbation DeltaScore calculation."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.delta_score import (
    DEFAULT_OUTPUT_PATH,
    DEFAULT_REPORT_PATH,
    DELTA_SCORE_FIELDS,
    DeltaScoreError,
    build_delta_score_dataset,
    calculate_delta_score,
)


class DeltaScoreTests(unittest.TestCase):
    def test_hand_checked_signed_and_absolute_examples(self):
        examples = (
            (0.8, 0.3, 0.5, 0.5),
            (0.25, 0.4, -0.15, 0.15),
            (0.6, 0.6, 0.0, 0.0),
        )
        for original, perturbed, expected_delta, expected_absolute in examples:
            with self.subTest(original=original, perturbed=perturbed):
                delta, absolute = calculate_delta_score(original, perturbed)
                self.assertAlmostEqual(delta, expected_delta)
                self.assertAlmostEqual(absolute, expected_absolute)

    def test_rejects_non_numeric_or_non_finite_scores(self):
        for original, perturbed in (
            (True, 0.2),
            ("0.5", 0.2),
            (math.nan, 0.2),
            (0.5, math.inf),
        ):
            with self.subTest(original=original, perturbed=perturbed):
                with self.assertRaises(DeltaScoreError):
                    calculate_delta_score(original, perturbed)

    def test_committed_pilot_delta_scores_are_complete_and_correct(self):
        report = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
        with DEFAULT_OUTPUT_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            rows = list(reader)
            fields = tuple(reader.fieldnames or ())

        self.assertEqual(fields, DELTA_SCORE_FIELDS)
        self.assertEqual(len(rows), 449)
        self.assertEqual(report["counts"]["unique_subject_count"], 20)
        self.assertEqual(
            report["counts"]["by_perturbation_type"],
            {"P1": 54, "P2": 150, "P3": 245},
        )
        self.assertTrue(report["predictor"]["software_testing_only"])
        self.assertFalse(report["predictor"]["scientific_result"])
        self.assertTrue(all(row["software_testing_only"] == "true" for row in rows))
        for row in rows:
            original = float(row["original_usable_score"])
            perturbed = float(row["perturbed_usable_score"])
            delta = float(row["delta_score"])
            absolute = float(row["absolute_delta_score"])
            self.assertAlmostEqual(delta, original - perturbed, places=15)
            self.assertAlmostEqual(absolute, abs(delta), places=15)

    def test_committed_artifacts_regenerate_identically(self):
        report = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            hashlib.sha256(DEFAULT_OUTPUT_PATH.read_bytes()).hexdigest(),
            report["output"]["sha256"],
        )
        self.assertTrue(all(report["validation"].values()))

        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            temporary = Path(directory)
            generated = build_delta_score_dataset(
                output_path=temporary / "delta.csv",
                report_path=temporary / "report.json",
                created_on=date.fromisoformat(report["created_on"]),
            )
            self.assertEqual(
                (temporary / "delta.csv").read_bytes(),
                DEFAULT_OUTPUT_PATH.read_bytes(),
            )
            generated["output"]["path"] = report["output"]["path"]
            self.assertEqual(generated, report)


if __name__ == "__main__":
    unittest.main()
