"""Tests for Task 3.24 fixed score normalization."""

from __future__ import annotations

import csv
import hashlib
import math
from pathlib import Path
import unittest

from plantaox.c3_aop_bcs.score_normalization import (
    DEFAULT_NORMALIZATION_REPORT_PATH,
    EXPECTED_REAL_PREDICTORS,
    ScoreNormalizationError,
    load_normalization_registry,
    normalize_score,
    normalize_scores,
    render_normalization_report,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class ScoreNormalizationTests(unittest.TestCase):
    def test_all_real_predictor_families_have_explicit_contracts(self):
        registry = load_normalization_registry()
        predictor_ids = {row["predictor_id"] for row in registry["score_contracts"]}
        self.assertTrue(EXPECTED_REAL_PREDICTORS.issubset(predictor_ids))
        real_contracts = [
            row
            for row in registry["score_contracts"]
            if row["predictor_id"] in EXPECTED_REAL_PREDICTORS
        ]
        self.assertTrue(all(not row["experimental_allowed"] for row in real_contracts))

    def test_native_zero_to_one_scores_are_preserved(self):
        for value in (0.0, 0.125, 0.5, 1.0):
            result = normalize_score(value, "aopxsvm_positive_probability")
            self.assertEqual(result.native_score, value)
            self.assertEqual(result.usable_score, value)
            self.assertFalse(result.transformed)

    def test_identity_mapping_rejects_invalid_values(self):
        for value in (-0.001, 1.001, math.nan, math.inf, True, "0.5"):
            with self.subTest(value=value):
                with self.assertRaises(ScoreNormalizationError):
                    normalize_score(value, "multi_aop_probability")

    def test_two_step_mapping_is_fixed_clipping_and_retains_native_score(self):
        below = normalize_score(0.25, "pu_aop_m4_two_step_raw")
        above = normalize_score(1.411371111869812, "pu_aop_m4_two_step_raw")
        self.assertEqual((below.native_score, below.usable_score), (0.25, 0.25))
        self.assertEqual(above.native_score, 1.411371111869812)
        self.assertEqual(above.usable_score, 1.0)
        self.assertTrue(above.transformed)
        with self.assertRaises(ScoreNormalizationError):
            normalize_score(-0.01, "pu_aop_m4_two_step_raw")

    def test_mapping_is_independent_of_batch_membership(self):
        alone = normalize_scores([0.4], "aopxsvm_positive_probability")[0]
        mixed = normalize_scores([0.0, 0.4, 1.0], "aopxsvm_positive_probability")[1]
        clipped_alone = normalize_scores([1.2], "pu_aop_m4_two_step_raw")[0]
        clipped_mixed = normalize_scores([0.1, 1.2, 100.0], "pu_aop_m4_two_step_raw")[1]
        self.assertEqual(alone, mixed)
        self.assertEqual(clipped_alone, clipped_mixed)

    def test_committed_dummy_scores_confirm_the_usable_range(self):
        registry = load_normalization_registry()
        evidence = registry["operational_validation"]
        path = REPOSITORY_ROOT / evidence["source_path"]
        self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), evidence["source_sha256"])

        values: list[float] = []
        with path.open("r", encoding="utf-8", newline="") as csv_file:
            for row in csv.DictReader(csv_file):
                values.extend((float(row["original_score"]), float(row["perturbed_score"])))
        results = normalize_scores(values, evidence["validated_score_id"], registry)

        self.assertEqual(len(values), evidence["score_value_count"])
        self.assertEqual(min(values), evidence["native_min"])
        self.assertEqual(max(values), evidence["native_max"])
        self.assertEqual(min(result.usable_score for result in results), evidence["usable_min"])
        self.assertEqual(max(result.usable_score for result in results), evidence["usable_max"])
        self.assertEqual(sum(result.transformed for result in results), 0)
        self.assertTrue(all(0.0 <= result.usable_score <= 1.0 for result in results))

    def test_source_evidence_and_report_are_reproducible(self):
        registry = load_normalization_registry()
        for source in registry["source_evidence"]:
            path = REPOSITORY_ROOT / source["path"]
            self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), source["sha256"])
        self.assertEqual(
            DEFAULT_NORMALIZATION_REPORT_PATH.read_text(encoding="utf-8"),
            render_normalization_report(registry),
        )


if __name__ == "__main__":
    unittest.main()
