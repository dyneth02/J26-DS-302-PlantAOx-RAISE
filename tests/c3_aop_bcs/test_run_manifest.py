"""Tests for Task 3.35 PP1 run provenance."""

from __future__ import annotations

from datetime import date
import json
from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.run_manifest import (
    DEFAULT_REPORT_PATHS,
    DEFAULT_RESULT_PATHS,
    DEFAULT_OUTPUT_PATH,
    RUN_ID,
    RunManifestError,
    build_run_manifest,
    resolve_git_commit,
)


TEST_DIRECTORY = Path(__file__).resolve().parent
TEST_COMMIT = "a" * 40


class RunManifestTests(unittest.TestCase):
    def _build(self, output: Path) -> dict[str, object]:
        return build_run_manifest(
            code_commit=TEST_COMMIT,
            output_path=output,
            created_on=date(2026, 10, 19),
        )

    def test_manifest_records_frozen_protocol_and_run_identity(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            manifest = self._build(Path(directory) / "manifest.json")

        self.assertEqual(manifest["run_id"], RUN_ID)
        self.assertEqual(manifest["code"]["git_commit"], TEST_COMMIT)
        self.assertEqual(manifest["dataset"]["version"], "c3_aop_bcs_pp1_pilot_v1")
        self.assertEqual(manifest["predictor"]["version"], "1.0.0")
        self.assertEqual(manifest["configuration"]["random_seed"], 42)
        self.assertEqual(manifest["configuration"]["redox_residues"], ["W", "Y", "H", "M", "C"])
        self.assertEqual(manifest["configuration"]["primary_delta"], 0.05)
        self.assertEqual(manifest["configuration"]["blosum62"]["minimum_score"], 1)
        self.assertEqual(
            manifest["configuration"]["blosum62"]["tie_break"],
            "highest BLOSUM62 score, then alphabetical residue code ascending",
        )

    def test_counts_failures_and_classification_are_reconciled(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            manifest = self._build(Path(directory) / "manifest.json")

        self.assertEqual(manifest["counts"]["peptides"], 20)
        self.assertEqual(manifest["counts"]["perturbations_total"], 449)
        self.assertEqual(
            manifest["counts"]["perturbations_by_type"],
            {"P1": 54, "P2": 150, "P3": 245},
        )
        self.assertEqual(
            manifest["failures_and_missing_scores"]["rejected_full_pipeline_perturbations"], 0
        )
        self.assertEqual(
            manifest["failures_and_missing_scores"]["pilot_perturbations_without_finite_scores"], 0
        )
        self.assertTrue(manifest["classification"]["software_testing_only"])
        self.assertFalse(manifest["classification"]["scientific_result"])
        self.assertEqual(manifest["validation"]["status"], "PASS")

    def test_every_required_report_and_result_is_checksum_pinned(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            manifest = self._build(Path(directory) / "manifest.json")

        provenance = manifest["provenance"]
        self.assertEqual(set(provenance["source_reports"]), set(DEFAULT_REPORT_PATHS))
        self.assertEqual(set(provenance["versioned_results"]), set(DEFAULT_RESULT_PATHS))
        for collection in ("source_reports", "versioned_results"):
            for label, artifact in provenance[collection].items():
                with self.subTest(collection=collection, label=label):
                    self.assertRegex(artifact["sha256"], r"^[0-9a-f]{64}$")
                    self.assertGreater(artifact["size_bytes"], 0)

    def test_generation_is_byte_reproducible(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            temporary = Path(directory)
            first = temporary / "first.json"
            second = temporary / "second.json"
            self._build(first)
            self._build(second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(json.loads(first.read_text(encoding="utf-8"))["run_id"], RUN_ID)

    def test_committed_manifest_is_byte_reproducible(self):
        committed = json.loads(DEFAULT_OUTPUT_PATH.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            generated = Path(directory) / "manifest.json"
            build_run_manifest(
                code_commit=committed["code"]["git_commit"],
                output_path=generated,
                created_on=date.fromisoformat(committed["run_date"]),
            )
            self.assertEqual(generated.read_bytes(), DEFAULT_OUTPUT_PATH.read_bytes())

    def test_invalid_commit_and_incomplete_registries_are_rejected(self):
        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            output = Path(directory) / "manifest.json"
            with self.assertRaisesRegex(RunManifestError, "code_commit"):
                build_run_manifest(code_commit="short", output_path=output)
            with self.assertRaisesRegex(RunManifestError, "report path registry"):
                build_run_manifest(
                    code_commit=TEST_COMMIT,
                    output_path=output,
                    report_paths={"pilot_selection": DEFAULT_REPORT_PATHS["pilot_selection"]},
                )

    def test_current_git_commit_resolves_to_a_full_hash(self):
        self.assertRegex(resolve_git_commit(), r"^[0-9a-f]{40}$")


if __name__ == "__main__":
    unittest.main()
