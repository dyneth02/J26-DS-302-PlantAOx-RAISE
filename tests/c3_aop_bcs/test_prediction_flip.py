"""Tests for Task 3.27 prediction flips and PFR."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.prediction_flip import (
    DEFAULT_OUTPUT_PATH,
    DEFAULT_REPORT_PATH,
    DUMMY_DECISION_THRESHOLD,
    PREDICTION_FLIP_FIELDS,
    PredictionFlipError,
    build_prediction_flip_dataset,
    classify_score,
    detect_prediction_flip,
    prediction_flip_rate,
)


class PredictionFlipTests(unittest.TestCase):
    def test_inclusive_threshold_classification_and_flip_directions(self):
        self.assertEqual(classify_score(0.5, 0.5), 1)
        self.assertEqual(classify_score(math.nextafter(0.5, 0.0), 0.5), 0)

        downward = detect_prediction_flip(0.6, 0.4, 0.5)
        upward = detect_prediction_flip(0.4, 0.5, 0.5)
        stable = detect_prediction_flip(0.5, 0.7, 0.5)
        self.assertEqual(
            (downward.original_class, downward.perturbed_class, downward.direction),
            (1, 0, "positive_to_negative"),
        )
        self.assertEqual(
            (upward.original_class, upward.perturbed_class, upward.direction),
            (0, 1, "negative_to_positive"),
        )
        self.assertFalse(stable.flipped)
        self.assertEqual(stable.direction, "none")

    def test_pfr_formula_and_invalid_inputs(self):
        self.assertEqual(prediction_flip_rate([True, False, True, False]), 0.5)
        with self.assertRaises(PredictionFlipError):
            prediction_flip_rate([])
        with self.assertRaises(PredictionFlipError):
            prediction_flip_rate([True, 1])
        for score, threshold in ((math.nan, 0.5), (1.1, 0.5), (0.5, -0.1)):
            with self.subTest(score=score, threshold=threshold):
                with self.assertRaises(PredictionFlipError):
                    classify_score(score, threshold)

    def test_committed_flip_rows_and_pfr_are_complete(self):
        report = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
        with DEFAULT_OUTPUT_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            rows = list(reader)
            fields = tuple(reader.fieldnames or ())

        self.assertEqual(fields, PREDICTION_FLIP_FIELDS)
        self.assertEqual(len(rows), 449)
        self.assertEqual(report["decision_rule"]["threshold"], DUMMY_DECISION_THRESHOLD)
        self.assertEqual(report["decision_rule"]["comparator"], "greater_than_or_equal")
        self.assertTrue(report["predictor"]["software_testing_only"])
        self.assertFalse(report["predictor"]["scientific_result"])
        self.assertEqual(
            sum(group["perturbation_count"] for group in report["pfr"]["by_perturbation_type"].values()),
            449,
        )
        for row in rows:
            original_class = int(float(row["original_usable_score"]) >= DUMMY_DECISION_THRESHOLD)
            perturbed_class = int(float(row["perturbed_usable_score"]) >= DUMMY_DECISION_THRESHOLD)
            self.assertEqual(int(row["original_class"]), original_class)
            self.assertEqual(int(row["perturbed_class"]), perturbed_class)
            self.assertEqual(row["prediction_flip"] == "true", original_class != perturbed_class)

    def test_committed_artifacts_regenerate_identically(self):
        report = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            hashlib.sha256(DEFAULT_OUTPUT_PATH.read_bytes()).hexdigest(),
            report["output"]["sha256"],
        )
        self.assertTrue(all(report["validation"].values()))

        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            temporary = Path(directory)
            generated = build_prediction_flip_dataset(
                output_path=temporary / "flips.csv",
                report_path=temporary / "report.json",
                created_on=date.fromisoformat(report["created_on"]),
            )
            self.assertEqual(
                (temporary / "flips.csv").read_bytes(),
                DEFAULT_OUTPUT_PATH.read_bytes(),
            )
            generated["output"]["path"] = report["output"]["path"]
            self.assertEqual(generated, report)


if __name__ == "__main__":
    unittest.main()
