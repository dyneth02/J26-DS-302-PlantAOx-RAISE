"""Tests for Task 3.23 cached and resumable predictor scoring."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.dummy_predictor import (
    DUMMY_PREDICTOR_ID,
    DUMMY_SCORING_METHOD,
    DummySmokeTestPredictor,
)
from plantaox.c3_aop_bcs.perturbation_schema import (
    PERTURBATION_FIELDS,
    PERTURBATION_SCHEMA_VERSION,
    PerturbationRecord,
)
from plantaox.c3_aop_bcs.predictor_interface import (
    CallablePredictorAdapter,
    PredictorDescriptor,
    PredictorScoringError,
)
from plantaox.c3_aop_bcs.predictor_scoring import (
    CACHE_FIELDS,
    DEFAULT_CACHE_PATH,
    DEFAULT_INPUT_PATH,
    DEFAULT_OUTPUT_PATH,
    DEFAULT_REPORT_PATH,
    SCORED_PERTURBATION_FIELDS,
    PredictorScoreCacheError,
    build_scored_perturbation_dataset,
)


TEST_DIRECTORY = Path(__file__).parent


def _record(variant_id: str, position: int, replacement: str, kind: str) -> PerturbationRecord:
    original = "AWD"
    perturbed = original[: position - 1] + replacement + original[position:]
    kwargs: dict[str, object] = {}
    if kind == "P2":
        kwargs["blosum62_score"] = 1
    elif kind == "P3":
        kwargs.update(random_seed=42, random_metadata="{}")
    return PerturbationRecord(
        schema_version=PERTURBATION_SCHEMA_VERSION,
        variant_id=variant_id,
        sequence_id="sequence-one",
        original_sequence=original,
        position=position,
        original_residue=original[position - 1],
        substituted_residue=replacement,
        perturbed_sequence=perturbed,
        perturbation_type=kind,
        **kwargs,
    )


def _write_perturbations(path: Path, records: list[PerturbationRecord]) -> None:
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=PERTURBATION_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows(record.as_dict() for record in records)


class PredictorScoringTests(unittest.TestCase):
    def test_scores_original_once_and_all_p1_p2_p3_variants(self):
        records = [
            _record("p1", 2, "A", "P1"),
            _record("p2", 3, "E", "P2"),
            _record("p3", 1, "C", "P3"),
        ]
        calls: list[str] = []
        predictor = CallablePredictorAdapter(
            PredictorDescriptor("counting", "Counting test predictor", "1"),
            lambda sequence: calls.append(sequence) or len(sequence) / 10,
        )
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            temporary = Path(directory)
            input_path = temporary / "input.csv"
            output_path = temporary / "scores.csv"
            cache_path = temporary / "cache.csv"
            _write_perturbations(input_path, records)
            result = build_scored_perturbation_dataset(
                predictor,
                "length_test_score",
                input_path,
                output_path,
                cache_path,
                temporary / "report.json",
                checkpoint_interval=1,
                created_on=date(2026, 10, 19),
                dataset_version="test_scores_v1",
            )
            with output_path.open("r", encoding="utf-8", newline="") as csv_file:
                reader = csv.DictReader(csv_file)
                output_rows = list(reader)
                output_fields = tuple(reader.fieldnames or ())

        self.assertEqual(calls.count("AWD"), 1)
        self.assertEqual(set(calls), {"AWD", "AAD", "AWE", "CWD"})
        self.assertEqual(output_fields, SCORED_PERTURBATION_FIELDS)
        self.assertEqual([row["perturbation_type"] for row in output_rows], ["P1", "P2", "P3"])
        self.assertTrue(all(row["original_score"] == "0.29999999999999999" for row in output_rows))
        self.assertEqual(result.report["predictor"]["version"], "1")
        self.assertEqual(result.report["predictor"]["scoring_method"], "length_test_score")
        self.assertEqual(result.scores_computed, 4)

    def test_complete_cache_resumes_without_predictor_calls(self):
        records = [_record("p1", 2, "A", "P1")]
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            temporary = Path(directory)
            input_path = temporary / "input.csv"
            output_path = temporary / "scores.csv"
            cache_path = temporary / "cache.csv"
            report_path = temporary / "report.json"
            _write_perturbations(input_path, records)
            first = build_scored_perturbation_dataset(
                DummySmokeTestPredictor(),
                DUMMY_SCORING_METHOD,
                input_path,
                output_path,
                cache_path,
                report_path,
                created_on=date(2026, 10, 19),
            )
            first_output = output_path.read_bytes()
            first_cache = cache_path.read_bytes()

            class MustNotRunDummy(DummySmokeTestPredictor):
                def _score_validated(self, sequence: str) -> float:
                    raise AssertionError("fully cached sequence was rescored")

            resumed = build_scored_perturbation_dataset(
                MustNotRunDummy(),
                DUMMY_SCORING_METHOD,
                input_path,
                output_path,
                cache_path,
                report_path,
                created_on=date(2026, 10, 19),
            )
            resumed_output = output_path.read_bytes()
            resumed_cache = cache_path.read_bytes()

        self.assertEqual(first.scores_computed, 2)
        self.assertEqual(resumed.scores_computed, 0)
        self.assertEqual(resumed.cache_hits, 2)
        self.assertEqual(resumed_output, first_output)
        self.assertEqual(resumed_cache, first_cache)

    def test_failed_run_checkpoints_and_later_resumes(self):
        records = [
            _record("p1", 2, "A", "P1"),
            _record("p2", 3, "E", "P2"),
            _record("p3", 1, "C", "P3"),
        ]
        calls = 0

        def interrupted(sequence: str) -> float:
            nonlocal calls
            calls += 1
            if calls == 3:
                raise RuntimeError("simulated interruption")
            return len(sequence) / 10

        descriptor = PredictorDescriptor("resume_test", "Resume test", "1")
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            temporary = Path(directory)
            input_path = temporary / "input.csv"
            cache_path = temporary / "cache.csv"
            _write_perturbations(input_path, records)
            with self.assertRaises(PredictorScoringError):
                build_scored_perturbation_dataset(
                    CallablePredictorAdapter(descriptor, interrupted),
                    "resume_test_method",
                    input_path,
                    temporary / "failed.csv",
                    cache_path,
                    temporary / "failed.json",
                    checkpoint_interval=1,
                )
            resumed_calls: list[str] = []
            resumed = build_scored_perturbation_dataset(
                CallablePredictorAdapter(
                    descriptor,
                    lambda sequence: resumed_calls.append(sequence) or len(sequence) / 10,
                ),
                "resume_test_method",
                input_path,
                temporary / "complete.csv",
                cache_path,
                temporary / "complete.json",
                checkpoint_interval=1,
            )

        self.assertEqual(resumed.initial_cache_entries, 2)
        self.assertEqual(resumed.scores_computed, 2)
        self.assertEqual(len(resumed_calls), 2)

    def test_cache_rejects_predictor_provenance_mismatch(self):
        records = [_record("p1", 2, "A", "P1")]
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            temporary = Path(directory)
            input_path = temporary / "input.csv"
            cache_path = temporary / "cache.csv"
            _write_perturbations(input_path, records)
            build_scored_perturbation_dataset(
                DummySmokeTestPredictor(),
                DUMMY_SCORING_METHOD,
                input_path,
                temporary / "scores.csv",
                cache_path,
                temporary / "report.json",
            )
            with self.assertRaisesRegex(PredictorScoreCacheError, "scoring_method"):
                build_scored_perturbation_dataset(
                    DummySmokeTestPredictor(),
                    "different_method",
                    input_path,
                    temporary / "scores-2.csv",
                    cache_path,
                    temporary / "report-2.json",
                )

    def test_committed_dummy_scoring_artifacts_are_complete_and_traceable(self):
        report = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
        with DEFAULT_OUTPUT_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            rows = list(reader)
            fields = tuple(reader.fieldnames or ())
        with DEFAULT_CACHE_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            cache_reader = csv.DictReader(csv_file)
            cache_rows = list(cache_reader)
            cache_fields = tuple(cache_reader.fieldnames or ())

        self.assertEqual(fields, SCORED_PERTURBATION_FIELDS)
        self.assertEqual(cache_fields, CACHE_FIELDS)
        self.assertEqual(len(rows), 10036)
        self.assertEqual(report["counts"]["original_peptide_count"], 734)
        self.assertEqual(report["counts"]["perturbations_by_type"], {"P1": 1180, "P2": 3276, "P3": 5580})
        self.assertEqual(report["predictor"]["predictor_id"], DUMMY_PREDICTOR_ID)
        self.assertTrue(report["predictor"]["software_testing_only"])
        self.assertTrue(all(row["software_testing_only"] == "true" for row in rows))
        self.assertEqual(len(cache_rows), report["cache"]["final_entries"])
        self.assertEqual(hashlib.sha256(DEFAULT_INPUT_PATH.read_bytes()).hexdigest(), report["source"]["sha256"])
        self.assertEqual(hashlib.sha256(DEFAULT_OUTPUT_PATH.read_bytes()).hexdigest(), report["output"]["sha256"])
        self.assertEqual(hashlib.sha256(DEFAULT_CACHE_PATH.read_bytes()).hexdigest(), report["cache"]["sha256"])


if __name__ == "__main__":
    unittest.main()
