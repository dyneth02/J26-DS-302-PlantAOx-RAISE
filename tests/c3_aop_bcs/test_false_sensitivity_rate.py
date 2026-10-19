"""Tests for Task 3.29 P1 False Sensitivity Rate."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.config import load_research_config
from plantaox.c3_aop_bcs.false_sensitivity_rate import (
    DEFAULT_OUTPUT_PATH,
    DEFAULT_REPORT_PATH,
    FSR_FIELDS,
    FalseSensitivityRateError,
    build_false_sensitivity_rate_dataset,
    false_sensitivity_rate,
    is_insufficient_response,
)


class FalseSensitivityRateTests(unittest.TestCase):
    def test_strict_primary_delta_boundary(self):
        delta = load_research_config().primary_delta
        self.assertTrue(is_insufficient_response(0.0, delta))
        self.assertTrue(is_insufficient_response(math.nextafter(delta, 0.0), delta))
        self.assertFalse(is_insufficient_response(delta, delta))
        self.assertFalse(is_insufficient_response(math.nextafter(delta, 1.0), delta))

    def test_fsr_formula_and_invalid_inputs(self):
        self.assertEqual(false_sensitivity_rate([True, False, True, False]), 0.5)
        with self.assertRaises(FalseSensitivityRateError):
            false_sensitivity_rate([])
        with self.assertRaises(FalseSensitivityRateError):
            false_sensitivity_rate([True, 1])
        for magnitude, delta in ((-0.1, 0.05), (math.nan, 0.05), (0.01, 0.0)):
            with self.subTest(magnitude=magnitude, delta=delta):
                with self.assertRaises(FalseSensitivityRateError):
                    is_insufficient_response(magnitude, delta)

    def test_committed_fsr_rows_are_complete_p1_records(self):
        report = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
        with DEFAULT_OUTPUT_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            rows = list(reader)
            fields = tuple(reader.fieldnames or ())

        delta = load_research_config().primary_delta
        self.assertEqual(fields, FSR_FIELDS)
        self.assertEqual(len(rows), 54)
        self.assertEqual(report["definition"]["delta"], delta)
        self.assertTrue(report["predictor"]["software_testing_only"])
        self.assertFalse(report["predictor"]["scientific_result"])
        self.assertTrue(all(row["perturbation_type"] == "P1" for row in rows))
        for row in rows:
            expected = float(row["absolute_delta_score"]) < delta
            self.assertEqual(row["insufficient_response"] == "true", expected)
        expected_rate = sum(
            row["insufficient_response"] == "true" for row in rows
        ) / len(rows)
        self.assertEqual(report["result"]["false_sensitivity_rate"], expected_rate)

    def test_committed_artifacts_regenerate_identically(self):
        report = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            hashlib.sha256(DEFAULT_OUTPUT_PATH.read_bytes()).hexdigest(),
            report["output"]["sha256"],
        )
        self.assertTrue(all(report["validation"].values()))

        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            temporary = Path(directory)
            generated = build_false_sensitivity_rate_dataset(
                output_path=temporary / "fsr.csv",
                report_path=temporary / "report.json",
                created_on=date.fromisoformat(report["created_on"]),
            )
            self.assertEqual(
                (temporary / "fsr.csv").read_bytes(),
                DEFAULT_OUTPUT_PATH.read_bytes(),
            )
            generated["output"]["path"] = report["output"]["path"]
            self.assertEqual(generated, report)


if __name__ == "__main__":
    unittest.main()
