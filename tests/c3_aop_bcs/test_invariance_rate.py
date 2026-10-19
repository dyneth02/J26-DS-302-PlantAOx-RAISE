"""Tests for Task 3.28 P2 Invariance Rate."""

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
from plantaox.c3_aop_bcs.invariance_rate import (
    DEFAULT_OUTPUT_PATH,
    DEFAULT_REPORT_PATH,
    INVARIANCE_FIELDS,
    InvarianceRateError,
    build_invariance_rate_dataset,
    invariance_rate,
    is_invariant,
)


class InvarianceRateTests(unittest.TestCase):
    def test_strict_primary_delta_boundary(self):
        delta = load_research_config().primary_delta
        self.assertTrue(is_invariant(0.0, delta))
        self.assertTrue(is_invariant(math.nextafter(delta, 0.0), delta))
        self.assertFalse(is_invariant(delta, delta))
        self.assertFalse(is_invariant(math.nextafter(delta, 1.0), delta))

    def test_ir_formula_and_invalid_inputs(self):
        self.assertEqual(invariance_rate([True, True, False, True]), 0.75)
        with self.assertRaises(InvarianceRateError):
            invariance_rate([])
        with self.assertRaises(InvarianceRateError):
            invariance_rate([True, 1])
        for magnitude, delta in ((-0.1, 0.05), (math.nan, 0.05), (0.01, 0.0)):
            with self.subTest(magnitude=magnitude, delta=delta):
                with self.assertRaises(InvarianceRateError):
                    is_invariant(magnitude, delta)

    def test_committed_ir_rows_are_complete_p2_records(self):
        report = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
        with DEFAULT_OUTPUT_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            rows = list(reader)
            fields = tuple(reader.fieldnames or ())

        delta = load_research_config().primary_delta
        self.assertEqual(fields, INVARIANCE_FIELDS)
        self.assertEqual(len(rows), 150)
        self.assertEqual(report["definition"]["delta"], delta)
        self.assertTrue(report["predictor"]["software_testing_only"])
        self.assertFalse(report["predictor"]["scientific_result"])
        self.assertTrue(all(row["perturbation_type"] == "P2" for row in rows))
        for row in rows:
            expected = float(row["absolute_delta_score"]) < delta
            self.assertEqual(row["is_invariant"] == "true", expected)
        expected_rate = sum(row["is_invariant"] == "true" for row in rows) / len(rows)
        self.assertEqual(report["result"]["invariance_rate"], expected_rate)

    def test_committed_artifacts_regenerate_identically(self):
        report = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            hashlib.sha256(DEFAULT_OUTPUT_PATH.read_bytes()).hexdigest(),
            report["output"]["sha256"],
        )
        self.assertTrue(all(report["validation"].values()))

        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            temporary = Path(directory)
            generated = build_invariance_rate_dataset(
                output_path=temporary / "invariance.csv",
                report_path=temporary / "report.json",
                created_on=date.fromisoformat(report["created_on"]),
            )
            self.assertEqual(
                (temporary / "invariance.csv").read_bytes(),
                DEFAULT_OUTPUT_PATH.read_bytes(),
            )
            generated["output"]["path"] = report["output"]["path"]
            self.assertEqual(generated, report)


if __name__ == "__main__":
    unittest.main()
