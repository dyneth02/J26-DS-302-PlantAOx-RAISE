"""Tests for Task 3.31 configurable delta-sensitivity support."""

from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.config import load_research_config
from plantaox.c3_aop_bcs.delta_sensitivity import (
    DEFAULT_INPUT_PATH,
    DEFAULT_REPORT_PATH,
    DeltaSensitivityError,
    build_delta_sensitivity_report,
    calculate_delta_sensitivity,
)
from plantaox.c3_aop_bcs.delta_score import DELTA_SCORE_FIELDS


def _row(variant_id: str, perturbation_type: str, magnitude: float) -> dict[str, str]:
    row = {field: "" for field in DELTA_SCORE_FIELDS}
    row.update(
        {
            "variant_id": variant_id,
            "perturbation_type": perturbation_type,
            "absolute_delta_score": repr(magnitude),
            "predictor_id": "test_predictor",
            "predictor_version": "1.0",
            "scoring_method": "test_method",
            "software_testing_only": "true",
            "score_contract_id": "test_contract",
            "normalization_mapping": "identity",
        }
    )
    return row


class DeltaSensitivityTests(unittest.TestCase):
    def test_three_thresholds_recalculate_ir_fsr_and_bcs(self):
        rows = [
            _row("p1-low", "P1", 0.01),
            _row("p1-middle", "P1", 0.04),
            _row("p1-high", "P1", 0.08),
            _row("p2-low", "P2", 0.01),
            _row("p2-middle", "P2", 0.04),
            _row("p2-high", "P2", 0.08),
        ]
        results = calculate_delta_sensitivity(rows, (0.02, 0.05, 0.10), 0.05)

        self.assertEqual([result["delta"] for result in results], [0.02, 0.05, 0.10])
        self.assertEqual([result["is_primary"] for result in results], [False, True, False])
        self.assertEqual([result["p2_invariant_count"] for result in results], [1, 2, 3])
        self.assertEqual(
            [result["p1_insufficient_response_count"] for result in results],
            [1, 2, 3],
        )
        self.assertAlmostEqual(results[0]["preliminary_bcs"], 2 / 9)
        self.assertAlmostEqual(results[1]["preliminary_bcs"], 2 / 9)
        self.assertEqual(results[2]["preliminary_bcs"], 0.0)

    def test_threshold_contract_rejects_invalid_sets(self):
        rows = [_row("p1", "P1", 0.01), _row("p2", "P2", 0.01)]
        invalid_cases = (
            ((), 0.05),
            ((0.05, 0.02), 0.05),
            ((0.02, 0.02), 0.02),
            ((0.02, 0.10), 0.05),
            ((0.0, 0.05), 0.05),
        )
        for deltas, primary in invalid_cases:
            with self.subTest(deltas=deltas, primary=primary):
                with self.assertRaises(DeltaSensitivityError):
                    calculate_delta_sensitivity(rows, deltas, primary)

    def test_equality_is_excluded_at_each_configured_threshold(self):
        for delta in (0.02, 0.05, 0.10):
            with self.subTest(delta=delta):
                rows = [
                    _row("p1-equal", "P1", delta),
                    _row("p2-equal", "P2", delta),
                ]
                result = calculate_delta_sensitivity(rows, (delta,), delta)[0]
                self.assertEqual(result["p1_insufficient_response_count"], 0)
                self.assertEqual(result["p2_invariant_count"], 0)

    def test_committed_report_uses_frozen_thresholds_and_primary(self):
        report = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
        config = load_research_config()
        results = report["threshold_results"]

        self.assertEqual(report["definition"]["configured_deltas"], [0.02, 0.05, 0.10])
        self.assertEqual(report["definition"]["configured_deltas"], list(config.sensitivity_deltas))
        self.assertEqual(report["definition"]["primary_delta"], config.primary_delta)
        self.assertEqual(sum(result["is_primary"] for result in results), 1)
        self.assertEqual(
            next(result["delta"] for result in results if result["is_primary"]),
            0.05,
        )
        self.assertTrue(report["predictor"]["software_testing_only"])
        self.assertFalse(report["predictor"]["scientific_result"])
        self.assertTrue(all(report["validation"].values()))

    def test_committed_report_regenerates_identically(self):
        report = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            report["source"]["sha256"],
            hashlib.sha256(DEFAULT_INPUT_PATH.read_bytes()).hexdigest(),
        )
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            generated = build_delta_sensitivity_report(
                report_path=Path(directory) / "sensitivity.json",
                created_on=date.fromisoformat(report["created_on"]),
            )
            self.assertEqual(generated, report)


if __name__ == "__main__":
    unittest.main()
