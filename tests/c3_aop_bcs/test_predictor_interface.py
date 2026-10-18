"""Tests for Task 3.19 common predictor interface."""

from __future__ import annotations

import json
import math
from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.predictor_interface import (
    CallablePredictorAdapter,
    DEFAULT_INTERFACE_PATH,
    InvalidPredictorInputError,
    InvalidPredictorScoreError,
    PREDICTOR_INTERFACE_VERSION,
    Predictor,
    PredictorDescriptor,
    PredictorScoringError,
    PredictorUnavailableError,
    interface_definition,
    write_interface_document,
)


TEST_DIRECTORY = Path(__file__).parent


class PredictorInterfaceTests(unittest.TestCase):
    def setUp(self):
        self.descriptor = PredictorDescriptor(
            predictor_id="test_predictor",
            display_name="Test Predictor",
            version="1.0",
        )

    def test_callable_adapter_exposes_sequence_to_finite_float_operation(self):
        observed: list[str] = []

        def scorer(sequence: str) -> int:
            observed.append(sequence)
            return len(sequence)

        adapter = CallablePredictorAdapter(self.descriptor, scorer)
        score = adapter.score("ACDE")

        self.assertIsInstance(adapter, Predictor)
        self.assertEqual(adapter.descriptor, self.descriptor)
        self.assertEqual(observed, ["ACDE"])
        self.assertEqual(score, 4.0)
        self.assertIs(type(score), float)

    def test_different_predictor_architectures_share_the_same_boundary(self):
        composition_adapter = CallablePredictorAdapter(
            PredictorDescriptor("composition", "Composition", "1"),
            lambda sequence: sequence.count("W") / len(sequence),
        )

        class ModelObject:
            def predict_one(self, sequence: str) -> float:
                return 0.75 if "Y" in sequence else 0.25

        model = ModelObject()
        model_adapter = CallablePredictorAdapter(
            PredictorDescriptor("model_object", "Model Object", "2"),
            model.predict_one,
        )

        predictors: list[Predictor] = [composition_adapter, model_adapter]
        self.assertEqual([predictor.score("AWY") for predictor in predictors], [1 / 3, 0.75])

    def test_invalid_sequences_are_rejected_before_scorer_invocation(self):
        calls = 0

        def scorer(sequence: str) -> float:
            nonlocal calls
            calls += 1
            return 0.5

        adapter = CallablePredictorAdapter(self.descriptor, scorer)
        for invalid in (None, "", "acd", "AC D", "ABZ"):
            with self.subTest(invalid=invalid):
                with self.assertRaises(InvalidPredictorInputError):
                    adapter.score(invalid)  # type: ignore[arg-type]
        self.assertEqual(calls, 0)

    def test_non_numeric_boolean_and_non_finite_scores_are_rejected(self):
        invalid_scores = (None, "0.5", True, math.nan, math.inf, -math.inf)
        for invalid_score in invalid_scores:
            with self.subTest(invalid_score=invalid_score):
                adapter = CallablePredictorAdapter(
                    self.descriptor,
                    lambda sequence, value=invalid_score: value,
                )
                with self.assertRaises(InvalidPredictorScoreError):
                    adapter.score("ACD")

    def test_unavailable_and_failed_predictors_have_distinct_errors(self):
        unavailable = CallablePredictorAdapter(
            self.descriptor,
            lambda sequence: 0.5,
            availability_check=lambda: False,
        )
        with self.assertRaises(PredictorUnavailableError):
            unavailable.score("ACD")

        def failed_scorer(sequence: str) -> float:
            raise OSError("model process exited")

        failed = CallablePredictorAdapter(self.descriptor, failed_scorer)
        with self.assertRaises(PredictorScoringError) as context:
            failed.score("ACD")
        self.assertIsInstance(context.exception.__cause__, OSError)
        self.assertNotIn("ACD", str(context.exception))

    def test_availability_check_exceptions_are_normalized(self):
        def failed_check() -> bool:
            raise ConnectionError("service offline")

        adapter = CallablePredictorAdapter(
            self.descriptor,
            lambda sequence: 0.5,
            availability_check=failed_check,
        )
        with self.assertRaises(PredictorUnavailableError) as context:
            adapter.score("ACD")
        self.assertIsInstance(context.exception.__cause__, ConnectionError)

    def test_descriptor_and_constructor_validation(self):
        with self.assertRaises(ValueError):
            PredictorDescriptor("", "Predictor", "1")
        with self.assertRaises(ValueError):
            PredictorDescriptor(" predictor ", "Predictor", "1")
        with self.assertRaises(TypeError):
            CallablePredictorAdapter(self.descriptor, None)  # type: ignore[arg-type]
        with self.assertRaises(TypeError):
            CallablePredictorAdapter(
                self.descriptor,
                lambda sequence: 0.5,
                availability_check=True,  # type: ignore[arg-type]
            )

    def test_committed_interface_contract_is_byte_reproducible(self):
        committed = json.loads(DEFAULT_INTERFACE_PATH.read_text(encoding="utf-8"))
        self.assertEqual(committed, interface_definition())
        self.assertEqual(committed["interface_version"], PREDICTOR_INTERFACE_VERSION)
        self.assertEqual(
            committed["operation"]["signature"],
            "score(sequence: str) -> float",
        )

        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            temporary = Path(directory)
            first = write_interface_document(temporary / "first.json")
            second = write_interface_document(temporary / "second.json")
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first.read_bytes(), DEFAULT_INTERFACE_PATH.read_bytes())


if __name__ == "__main__":
    unittest.main()
