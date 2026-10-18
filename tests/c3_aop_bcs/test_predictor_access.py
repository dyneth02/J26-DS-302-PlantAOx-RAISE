"""Tests for Task 3.20 predictor accessibility records."""

from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.predictor_access import (
    DEFAULT_ACCESS_REGISTRY_PATH,
    DEFAULT_ACCESS_TABLE_PATH,
    EXPECTED_PREDICTOR_IDS,
    PREDICTOR_ACCESS_SCHEMA_VERSION,
    PredictorAccessRegistryError,
    load_predictor_access_registry,
    render_predictor_access_table,
    validate_predictor_access_registry,
    write_predictor_access_table,
)


TEST_DIRECTORY = Path(__file__).parent


class PredictorAccessTests(unittest.TestCase):
    def test_registry_covers_every_required_predictor_and_access_field(self):
        registry = load_predictor_access_registry()

        self.assertEqual(registry["schema_version"], PREDICTOR_ACCESS_SCHEMA_VERSION)
        self.assertEqual(
            tuple(record["predictor_id"] for record in registry["predictors"]),
            EXPECTED_PREDICTOR_IDS,
        )
        for record in registry["predictors"]:
            with self.subTest(predictor=record["predictor_id"]):
                self.assertTrue(record["code_model_availability"]["summary"])
                self.assertTrue(record["expected_input"]["summary"])
                self.assertTrue(record["output"]["summary"])
                self.assertIsInstance(record["batch_scoring"]["possible"], bool)
                self.assertTrue(record["license_access"]["summary"])
                self.assertTrue(record["integration"]["status"])
                self.assertTrue(record["sources"])

    def test_no_predictor_is_claimed_integrated_without_real_score_evidence(self):
        registry = load_predictor_access_registry()

        for record in registry["predictors"]:
            with self.subTest(predictor=record["predictor_id"]):
                self.assertEqual(record["integration"]["status"], "not_integrated")
                self.assertFalse(record["integration"]["real_score_verified"])
                self.assertIsNone(record["integration"]["score_evidence"])

        invalid = copy.deepcopy(registry)
        invalid["predictors"][0]["integration"]["status"] = "integrated"
        with self.assertRaisesRegex(
            PredictorAccessRegistryError, "cannot be integrated without real score evidence"
        ):
            validate_predictor_access_registry(invalid)

    def test_operational_limitations_are_recorded(self):
        records = {
            record["predictor_id"]: record for record in load_predictor_access_registry()["predictors"]
        }

        self.assertFalse(records["aop_drl"]["batch_scoring"]["possible"])
        self.assertIn("non-commercial", records["aop_drl"]["license_access"]["summary"].lower())
        self.assertFalse(
            load_predictor_access_registry()["environment_observations"][
                "pu_aop_required_ignored_artifacts_present_in_current_checkout"
            ]
        )

    def test_committed_markdown_table_is_reproducible(self):
        registry = load_predictor_access_registry(DEFAULT_ACCESS_REGISTRY_PATH)
        expected = render_predictor_access_table(registry).encode("utf-8")
        self.assertEqual(DEFAULT_ACCESS_TABLE_PATH.read_bytes(), expected)

        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            output = write_predictor_access_table(
                DEFAULT_ACCESS_REGISTRY_PATH,
                Path(directory) / "predictor_access_status.md",
            )
            self.assertEqual(output.read_bytes(), expected)


if __name__ == "__main__":
    unittest.main()
