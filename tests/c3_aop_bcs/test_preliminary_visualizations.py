"""Tests for Task 3.34 preliminary PP1 visualizations."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from xml.etree import ElementTree

from plantaox.c3_aop_bcs.preliminary_visualizations import (
    DEFAULT_BCS_PATH,
    DEFAULT_DELTA_PATH,
    DEFAULT_DISTRIBUTION_PATH,
    DEFAULT_EXAMPLE_PATH,
    DEFAULT_FLIP_COMPARISON_PATH,
    DEFAULT_FSR_PATH,
    DEFAULT_IR_PATH,
    DEFAULT_METRIC_DATA_PATH,
    DEFAULT_METRIC_TABLE_PATH,
    DEFAULT_PFR_PATH,
    DEFAULT_REPORT_PATH,
    DEFAULT_SCORE_EXAMPLES_PATH,
    METRIC_DATA_FIELDS,
    WARNING,
    build_preliminary_visualizations,
)


class PreliminaryVisualizationTests(unittest.TestCase):
    def test_all_requested_figures_are_valid_and_visibly_labelled(self):
        figure_paths = (
            DEFAULT_DISTRIBUTION_PATH,
            DEFAULT_SCORE_EXAMPLES_PATH,
            DEFAULT_METRIC_TABLE_PATH,
            DEFAULT_FLIP_COMPARISON_PATH,
        )
        for path in figure_paths:
            with self.subTest(path=path.name):
                root = ElementTree.fromstring(path.read_text(encoding="utf-8"))
                self.assertTrue(root.tag.endswith("svg"))
                self.assertIn(WARNING, "".join(root.itertext()))

    def test_manifest_uses_expected_generated_results(self):
        report = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
        self.assertEqual(report["data_summary"]["delta_score_record_count"], 449)
        self.assertEqual(
            report["data_summary"]["perturbation_counts"],
            {"P1": 54, "P2": 150, "P3": 245},
        )
        self.assertEqual(report["data_summary"]["inspected_example_count"], 6)
        self.assertEqual(report["data_summary"]["primary_delta"], 0.05)
        self.assertTrue(report["classification"]["pilot_preliminary"])
        self.assertTrue(report["classification"]["software_testing_only"])
        self.assertFalse(report["classification"]["scientific_result"])
        self.assertTrue(all(report["validation"].values()))

    def test_metric_summary_table_matches_primary_reports(self):
        ir = json.loads(DEFAULT_IR_PATH.read_text(encoding="utf-8"))
        fsr = json.loads(DEFAULT_FSR_PATH.read_text(encoding="utf-8"))
        bcs = json.loads(DEFAULT_BCS_PATH.read_text(encoding="utf-8"))
        with DEFAULT_METRIC_DATA_PATH.open("r", encoding="utf-8", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            rows = list(reader)
            self.assertEqual(tuple(reader.fieldnames or ()), METRIC_DATA_FIELDS)
        self.assertEqual([row["metric"] for row in rows], ["IR", "FSR", "BCS"])
        self.assertEqual(float(rows[0]["value"]), ir["result"]["invariance_rate"])
        self.assertEqual(float(rows[1]["value"]), fsr["result"]["false_sensitivity_rate"])
        self.assertEqual(float(rows[2]["value"]), bcs["result"]["preliminary_bcs"])

    def test_committed_outputs_regenerate_identically(self):
        report = json.loads(DEFAULT_REPORT_PATH.read_text(encoding="utf-8"))
        source_paths = {
            "delta_scores": DEFAULT_DELTA_PATH,
            "manual_examples": DEFAULT_EXAMPLE_PATH,
            "invariance_rate": DEFAULT_IR_PATH,
            "false_sensitivity_rate": DEFAULT_FSR_PATH,
            "preliminary_bcs": DEFAULT_BCS_PATH,
            "prediction_flips": DEFAULT_PFR_PATH,
        }
        for label, path in source_paths.items():
            self.assertEqual(
                report["sources"][label]["sha256"],
                hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        with tempfile.TemporaryDirectory(dir=Path(__file__).parent) as directory:
            temporary = Path(directory)
            generated = build_preliminary_visualizations(
                output_directory=temporary / "figures",
                report_path=temporary / "report.json",
                created_on=date.fromisoformat(report["created_on"]),
            )
            for label, details in report["outputs"].items():
                committed = Path(details["path"])
                if not committed.is_absolute():
                    committed = DEFAULT_REPORT_PATH.parents[3] / committed
                regenerated = temporary / "figures" / committed.name
                self.assertEqual(regenerated.read_bytes(), committed.read_bytes())
                generated["outputs"][label]["path"] = details["path"]
            self.assertEqual(generated, report)


if __name__ == "__main__":
    unittest.main()
