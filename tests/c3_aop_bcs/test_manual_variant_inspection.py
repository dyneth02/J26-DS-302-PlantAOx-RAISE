"""Tests for Task 3.33 manually inspected PP1 examples."""

from __future__ import annotations

from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.manual_variant_inspection import (
    DEFAULT_INPUT_PATH,
    DEFAULT_MARKDOWN_PATH,
    DEFAULT_REPORT_PATH,
    REPRESENTATIVE_VARIANT_IDS,
    build_manual_variant_inspection,
    render_examples_markdown,
)


class ManualVariantInspectionTests(unittest.TestCase):
    def test_committed_evidence_has_representative_examples(self):
        report = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
        examples = report["examples"]

        self.assertEqual(
            tuple(example["variant_id"] for example in examples),
            REPRESENTATIVE_VARIANT_IDS,
        )
        self.assertEqual(len(examples), 6)
        self.assertEqual(
            [example["perturbation_type"] for example in examples],
            ["P1", "P1", "P2", "P2", "P3", "P3"],
        )
        self.assertEqual(
            [example["blosum62_score"] for example in examples[2:4]],
            [2, 3],
        )
        self.assertTrue(all(report["validation"].values()))

    def test_every_example_passes_mutation_and_score_checks(self):
        report = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
        for example in report["examples"]:
            with self.subTest(variant_id=example["variant_id"]):
                self.assertEqual(example["changed_positions"], [example["position"]])
                self.assertTrue(all(example["checks"].values()))
                self.assertEqual(example["inspection_status"], "PASS")

    def test_markdown_is_safe_and_matches_report(self):
        report = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
        markdown = DEFAULT_MARKDOWN_PATH.read_text(encoding="utf-8")

        self.assertEqual(markdown, render_examples_markdown(report))
        self.assertIn("Software-testing evidence only", markdown)
        self.assertIn("not scientific AOP results", markdown)
        for variant_id in REPRESENTATIVE_VARIANT_IDS:
            self.assertIn(variant_id, markdown)

    def test_committed_artifacts_regenerate_identically(self):
        report = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            report["source"]["sha256"],
            hashlib.sha256(DEFAULT_INPUT_PATH.read_bytes()).hexdigest(),
        )
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            temporary = Path(directory)
            generated = build_manual_variant_inspection(
                report_path=temporary / "inspection.json",
                markdown_path=temporary / "inspection.md",
                created_on=date.fromisoformat(report["created_on"]),
            )
            self.assertEqual(generated, report)
            self.assertEqual(
                (temporary / "inspection.md").read_bytes(),
                DEFAULT_MARKDOWN_PATH.read_bytes(),
            )


if __name__ == "__main__":
    unittest.main()
