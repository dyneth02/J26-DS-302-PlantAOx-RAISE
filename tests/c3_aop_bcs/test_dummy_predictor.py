"""Tests for Task 3.22 non-experimental dummy/smoke-test predictor."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.dummy_predictor import (
    DEFAULT_DUMMY_DEFINITION_PATH,
    DUMMY_PREDICTOR_ID,
    DUMMY_PREDICTOR_VERSION,
    DummySmokeTestPredictor,
    dummy_predictor_definition,
    write_dummy_predictor_definition,
)
from plantaox.c3_aop_bcs.predictor_interface import (
    InvalidPredictorInputError,
    Predictor,
)


TEST_DIRECTORY = Path(__file__).parent


class DummySmokeTestPredictorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.predictor = DummySmokeTestPredictor()

    def test_implements_common_interface_and_returns_deterministic_float(self):
        first = self.predictor.score("ACD")
        second = DummySmokeTestPredictor().score("ACD")

        self.assertIsInstance(self.predictor, Predictor)
        self.assertIs(type(first), float)
        self.assertEqual(first, second)
        self.assertAlmostEqual(first, 14 / 120)
        self.assertEqual(self.predictor.descriptor.predictor_id, DUMMY_PREDICTOR_ID)
        self.assertEqual(self.predictor.descriptor.version, DUMMY_PREDICTOR_VERSION)

    def test_scores_are_bounded_and_single_substitutions_are_observable(self):
        sequences = ("A", "Y", "ACDEFGHIKLMNPQRSTVWY", "WAA", "AAA")
        scores = [self.predictor.score(sequence) for sequence in sequences]

        self.assertTrue(all(0.0 <= score <= 1.0 for score in scores))
        self.assertNotEqual(self.predictor.score("WAA"), self.predictor.score("AAA"))

    def test_common_interface_rejects_invalid_inputs(self):
        for invalid in ("", "acd", "ABZ", "AC D"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(InvalidPredictorInputError):
                    self.predictor.score(invalid)

    def test_safety_labels_prohibit_scientific_and_experimental_use(self):
        definition = dummy_predictor_definition()
        classification = definition["classification"]

        self.assertTrue(self.predictor.software_testing_only)
        self.assertFalse(self.predictor.scientific_aop_predictor)
        self.assertFalse(self.predictor.experimental_results_allowed)
        self.assertEqual(
            classification,
            {
                "software_testing_only": True,
                "scientific_aop_predictor": False,
                "experimental_results_allowed": False,
            },
        )
        self.assertEqual(definition["scoring_method"]["biological_basis"], "none")
        self.assertIn(
            "satisfying the PP1 real-predictor requirement",
            definition["prohibited_uses"],
        )

    def test_committed_definition_is_byte_reproducible(self):
        committed = json.loads(DEFAULT_DUMMY_DEFINITION_PATH.read_text(encoding="utf-8"))
        self.assertEqual(committed, dummy_predictor_definition())

        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            generated = write_dummy_predictor_definition(
                Path(directory) / "dummy_predictor.json"
            )
            self.assertEqual(
                generated.read_bytes(),
                DEFAULT_DUMMY_DEFINITION_PATH.read_bytes(),
            )


if __name__ == "__main__":
    unittest.main()
