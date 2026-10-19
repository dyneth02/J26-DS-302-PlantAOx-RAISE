"""Tests for Task 3.32 PP1 perturbation-count review."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.perturbation_count_review import (
    COUNT_REVIEW_FIELDS,
    DEFAULT_OUTPUT_PATH,
    DEFAULT_PERTURBATION_INPUT_PATH,
    DEFAULT_REPORT_PATH,
    DEFAULT_SUBJECT_INPUT_PATH,
    build_perturbation_count_review,
)


class PerturbationCountReviewTests(unittest.TestCase):
    def test_committed_report_has_expected_global_counts(self):
        report = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
        counts = report["counts"]

        self.assertEqual(counts["subject_count"], 20)
        self.assertEqual(counts["total_variant_count"], 449)
        self.assertEqual(
            counts["by_perturbation_type"],
            {"P1": 54, "P2": 150, "P3": 245},
        )
        self.assertTrue(all(report["validation"].values()))

    def test_per_subject_counts_reconcile_and_expected_zero_is_explained(self):
        with DEFAULT_OUTPUT_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            rows = list(reader)
            self.assertEqual(tuple(reader.fieldnames or ()), COUNT_REVIEW_FIELDS)

        self.assertEqual(len(rows), 20)
        for row in rows:
            actual = sum(int(row[f"actual_{kind}_count"]) for kind in ("p1", "p2", "p3"))
            self.assertEqual(actual, int(row["total_variant_count"]))
            self.assertEqual(row["counts_match_expected"], "true")
            self.assertEqual(row["unexpected_zero_types"], "")

        zero_rows = [row for row in rows if row["expected_zero_types"]]
        self.assertEqual(len(zero_rows), 1)
        self.assertEqual(zero_rows[0]["sequence_id"], "C3-ANOX-000205")
        self.assertEqual(zero_rows[0]["expected_zero_types"], "P2")
        self.assertEqual(zero_rows[0]["actual_p2_count"], "0")

    def test_no_sequence_dominates_pilot_variants(self):
        report = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
        dominance = report["dominance_review"]
        maximum = dominance["maximum_contributor"]

        self.assertEqual(dominance["dominant_sequence_count"], 0)
        self.assertEqual(dominance["dominant_sequence_ids"], [])
        self.assertEqual(maximum["sequence_id"], "C3-ANOX-000467")
        self.assertEqual(maximum["variant_count"], 64)
        self.assertAlmostEqual(maximum["variant_share"], 64 / 449)
        self.assertLessEqual(
            maximum["variant_share"],
            report["review_scope"]["dominance_threshold_fraction"],
        )

    def test_committed_artifacts_regenerate_identically(self):
        report = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(
            report["sources"]["subjects"]["sha256"],
            hashlib.sha256(DEFAULT_SUBJECT_INPUT_PATH.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            report["sources"]["perturbations"]["sha256"],
            hashlib.sha256(DEFAULT_PERTURBATION_INPUT_PATH.read_bytes()).hexdigest(),
        )
        self.assertEqual(
            report["output"]["sha256"],
            hashlib.sha256(DEFAULT_OUTPUT_PATH.read_bytes()).hexdigest(),
        )
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            temporary = Path(directory)
            generated = build_perturbation_count_review(
                output_path=temporary / "counts.csv",
                report_path=temporary / "report.json",
                created_on=date.fromisoformat(report["created_on"]),
            )
            self.assertEqual(
                (temporary / "counts.csv").read_bytes(),
                DEFAULT_OUTPUT_PATH.read_bytes(),
            )
            generated["output"]["path"] = report["output"]["path"]
            self.assertEqual(generated, report)


if __name__ == "__main__":
    unittest.main()
