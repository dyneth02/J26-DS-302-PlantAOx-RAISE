"""Tests for the Component 2 five-model handoff audit owned by C3."""

from __future__ import annotations

import copy
import hashlib
from pathlib import Path
import unittest

from plantaox.c3_aop_bcs.pu_aop_audit import (
    DEFAULT_REPORT_PATH,
    EXPECTED_MODEL_IDS,
    PuAopAuditError,
    load_pu_aop_audit,
    render_pu_aop_audit_report,
    validate_pu_aop_audit,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class PuAopAuditTests(unittest.TestCase):
    def test_audit_covers_exactly_five_frozen_models(self):
        audit = load_pu_aop_audit()
        self.assertEqual({model["model_id"] for model in audit["models"]}, EXPECTED_MODEL_IDS)
        self.assertTrue(
            all(not model["checkpoint_available_in_current_checkout"] for model in audit["models"])
        )
        self.assertTrue(all(model["c3_integration_status"] == "not_integrated" for model in audit["models"]))

    def test_source_evidence_hashes_match_component_2_without_writing_it(self):
        audit = load_pu_aop_audit()
        for source in audit["source_evidence"]:
            source_path = REPOSITORY_ROOT / source["path"]
            digest = hashlib.sha256(source_path.read_bytes()).hexdigest()
            self.assertEqual(digest, source["sha256"], source["path"])

    def test_integration_claim_is_rejected_while_gate_is_blocked(self):
        audit = load_pu_aop_audit()
        invalid = copy.deepcopy(audit)
        invalid["models"][0]["c3_integration_status"] = "integrated"
        with self.assertRaisesRegex(PuAopAuditError, "reference score"):
            validate_pu_aop_audit(invalid)

    def test_pu_bagging_discrepancy_is_explicit(self):
        audit = load_pu_aop_audit()
        model = next(model for model in audit["models"] if model["model_id"] == "M5")
        self.assertEqual(model["accepted_run_n_estimators"], 10)
        self.assertIn("100", model["configuration_discrepancy"])
        self.assertTrue(
            any(item["id"] == "C2-HANDOFF-05" for item in audit["missing_or_unresolved"])
        )

    def test_committed_report_is_reproducible(self):
        audit = load_pu_aop_audit()
        self.assertEqual(
            DEFAULT_REPORT_PATH.read_text(encoding="utf-8"),
            render_pu_aop_audit_report(audit),
        )


if __name__ == "__main__":
    unittest.main()
