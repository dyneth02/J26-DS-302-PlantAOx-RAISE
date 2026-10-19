"""Tests for Task 3.30 preliminary Behavioural Consistency Score."""

from __future__ import annotations

from datetime import date
import hashlib
import json
import math
from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.preliminary_bcs import (
    DEFAULT_FSR_REPORT_PATH,
    DEFAULT_IR_REPORT_PATH,
    DEFAULT_REPORT_PATH,
    PreliminaryBCSError,
    build_preliminary_bcs_report,
    calculate_bcs,
)


class PreliminaryBCSTests(unittest.TestCase):
    def test_formula_matches_manual_examples(self):
        self.assertEqual(calculate_bcs(1.0, 0.0), 1.0)
        self.assertAlmostEqual(calculate_bcs(0.8, 0.25), 0.6)
        self.assertEqual(calculate_bcs(0.0, 0.5), 0.0)
        self.assertEqual(calculate_bcs(1.0, 1.0), 0.0)

    def test_invalid_rates_are_rejected(self):
        invalid_pairs = (
            (-0.01, 0.2),
            (1.01, 0.2),
            (0.8, -0.01),
            (0.8, 1.01),
            (math.nan, 0.2),
            (True, 0.2),
        )
        for ir, fsr in invalid_pairs:
            with self.subTest(ir=ir, fsr=fsr):
                with self.assertRaises(PreliminaryBCSError):
                    calculate_bcs(ir, fsr)

    def test_committed_report_contains_valid_preliminary_result(self):
        report = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
        ir_report = json.loads(DEFAULT_IR_REPORT_PATH.read_text(encoding="utf-8"))
        fsr_report = json.loads(DEFAULT_FSR_REPORT_PATH.read_text(encoding="utf-8"))
        ir = ir_report["result"]["invariance_rate"]
        fsr = fsr_report["result"]["false_sensitivity_rate"]

        self.assertEqual(report["definition"]["formula"], "BCS = IR * (1 - FSR)")
        self.assertEqual(report["result"]["preliminary_bcs"], ir * (1.0 - fsr))
        self.assertGreaterEqual(report["result"]["preliminary_bcs"], 0.0)
        self.assertLessEqual(report["result"]["preliminary_bcs"], 1.0)
        self.assertTrue(report["result"]["preliminary_pilot_value"])
        self.assertTrue(report["result"]["software_testing_only"])
        self.assertFalse(report["result"]["scientific_result"])
        self.assertTrue(all(report["validation"].values()))

    def test_committed_report_regenerates_identically(self):
        report = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            report["sources"]["invariance_rate_report"]["sha256"],
            hashlib.sha256(DEFAULT_IR_REPORT_PATH.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            report["sources"]["false_sensitivity_rate_report"]["sha256"],
            hashlib.sha256(DEFAULT_FSR_REPORT_PATH.read_bytes()).hexdigest(),
        )

        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            generated = build_preliminary_bcs_report(
                report_path=Path(directory) / "bcs.json",
                created_on=date.fromisoformat(report["created_on"]),
            )
            self.assertEqual(generated, report)


if __name__ == "__main__":
    unittest.main()
