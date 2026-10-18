"""Tests for Task 3.21 PP1 predictor prioritization."""

from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest

from plantaox.c3_aop_bcs.predictor_priority import (
    DEFAULT_PRIORITY_REPORT_PATH,
    DEFAULT_PU_AOP_HANDOFF_PATH,
    PRIMARY_PREDICTORS,
    SECONDARY_PREDICTORS,
    PredictorPriorityPlanError,
    load_predictor_priority_plan,
    render_predictor_priority_report,
    render_pu_aop_handoff_request,
    validate_predictor_priority_plan,
    write_priority_documents,
)


TEST_DIRECTORY = Path(__file__).parent


class PredictorPriorityTests(unittest.TestCase):
    def test_requested_primary_and_secondary_scope_is_frozen(self):
        plan = load_predictor_priority_plan()
        priorities = plan["priorities"]

        self.assertEqual(
            {row["predictor_id"] for row in priorities if row["tier"] == "primary"},
            PRIMARY_PREDICTORS,
        )
        self.assertEqual(
            {row["predictor_id"] for row in priorities if row["tier"] == "secondary"},
            SECONDARY_PREDICTORS,
        )
        self.assertEqual(
            [row["predictor_id"] for row in sorted(priorities, key=lambda row: row["integration_order"])],
            ["aopxsvm", "anoxpepred", "pu_aop", "multi_aop", "aop_drl"],
        )

    def test_priority_statuses_remain_synchronized_with_access_registry(self):
        plan = load_predictor_priority_plan()
        self.assertTrue(all(row["integration_status"] == "not_integrated" for row in plan["priorities"]))
        self.assertFalse(plan["pp1_scope_policy"]["dummy_counts_as_real_predictor"])

        invalid = copy.deepcopy(plan)
        invalid["priorities"][0]["integration_status"] = "integrated"
        with self.assertRaisesRegex(PredictorPriorityPlanError, "disagrees"):
            validate_predictor_priority_plan(invalid)

    def test_pu_aop_cannot_be_ready_with_incomplete_handoff(self):
        plan = load_predictor_priority_plan()
        handoff = plan["pu_aop_handoff"]
        self.assertFalse(handoff["ready_for_c3_integration"])
        self.assertTrue(
            any(
                item["required"] and item["status"] != "verified_for_handoff"
                for item in handoff["requirements"]
            )
        )

        invalid = copy.deepcopy(plan)
        invalid["pu_aop_handoff"]["ready_for_c3_integration"] = True
        with self.assertRaisesRegex(PredictorPriorityPlanError, "remain unverified"):
            validate_predictor_priority_plan(invalid)

    def test_every_predictor_has_an_actionable_access_issue(self):
        plan = load_predictor_priority_plan()
        issue_predictors = {issue["predictor_id"] for issue in plan["unresolved_access_issues"]}
        self.assertEqual(issue_predictors, PRIMARY_PREDICTORS | SECONDARY_PREDICTORS)
        self.assertTrue(all(issue["exit_criterion"] for issue in plan["unresolved_access_issues"]))

    def test_committed_priority_documents_are_reproducible(self):
        plan = load_predictor_priority_plan()
        expected_report = render_predictor_priority_report(plan).encode("utf-8")
        expected_handoff = render_pu_aop_handoff_request(plan).encode("utf-8")
        self.assertEqual(DEFAULT_PRIORITY_REPORT_PATH.read_bytes(), expected_report)
        self.assertEqual(DEFAULT_PU_AOP_HANDOFF_PATH.read_bytes(), expected_handoff)

        with tempfile.TemporaryDirectory(dir=TEST_DIRECTORY) as directory:
            report, handoff = write_priority_documents(
                report_path=Path(directory) / "scope.md",
                handoff_path=Path(directory) / "handoff.md",
            )
            self.assertEqual(report.read_bytes(), expected_report)
            self.assertEqual(handoff.read_bytes(), expected_handoff)


if __name__ == "__main__":
    unittest.main()
