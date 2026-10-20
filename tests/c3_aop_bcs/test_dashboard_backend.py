"""Contract tests for the C3-owned dashboard API and static frontend."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from fastapi.testclient import TestClient

from plantaox.c3_aop_bcs.dashboard_backend import (
    DashboardArtifactError,
    REPOSITORY_ROOT,
    SOURCE_PATHS,
    app,
    build_dashboard_payload,
)


class DashboardBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def test_health_reports_the_live_artifact_contract(self):
        health = self.client.get("/api/v1/c3/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()["status"], "ok")
        self.assertEqual(health.json()["component"], "c3_aop_bcs")
        self.assertEqual(health.json()["artifact_count"], 12)

        self.assertEqual(health.json()["api_version"], "c3-dashboard-api-v1")

    def test_dashboard_contract_is_built_from_authoritative_artifacts(self):
        response = self.client.get("/api/v1/c3/dashboard")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["apiVersion"], "c3-dashboard-api-v1")
        self.assertEqual(payload["overview"]["pilotSubjects"], 20)
        self.assertEqual(payload["overview"]["pilotVariants"], 449)
        self.assertEqual([row["pilotCount"] for row in payload["perturbations"]], [54, 150, 245])
        self.assertEqual(len(payload["examples"]), 6)
        self.assertEqual(len(payload["provenance"]["sourceArtifacts"]), 12)
        self.assertTrue(payload["classification"]["software_testing_only"])
        self.assertFalse(payload["classification"]["scientific_result"])
        self.assertTrue(all(row["status"] == "not_integrated" for row in payload["predictors"]))

    def test_sections_and_figures_are_available(self):
        metrics = self.client.get("/api/v1/c3/sections/metrics")
        self.assertEqual(metrics.status_code, 200)
        self.assertEqual(metrics.json()["section"], "metrics")
        self.assertAlmostEqual(metrics.json()["metrics"]["primaryDelta"], 0.05)

        payload = self.client.get("/api/v1/c3/dashboard").json()
        figure = self.client.get(payload["figures"][0]["file"])
        self.assertEqual(figure.status_code, 200)
        self.assertEqual(figure.headers["content-type"], "image/svg+xml")
        self.assertEqual(self.client.get("/api/v1/c3/sections/not-a-section").status_code, 422)
        self.assertEqual(self.client.get("/api/v1/c3/figures/not-a-figure.svg").status_code, 404)

    def test_missing_required_artifact_fails_closed(self):
        with TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            for relative_path in SOURCE_PATHS.values():
                source = REPOSITORY_ROOT / relative_path
                destination = temporary_root / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source.read_bytes())
            missing_path = temporary_root / SOURCE_PATHS["manifest"]
            missing_path.unlink()
            with self.assertRaisesRegex(DashboardArtifactError, "missing"):
                build_dashboard_payload(temporary_root)

    def test_tampered_scientific_classification_is_rejected(self):
        with TemporaryDirectory() as temporary_directory:
            temporary_root = Path(temporary_directory)
            for relative_path in SOURCE_PATHS.values():
                source = REPOSITORY_ROOT / relative_path
                destination = temporary_root / relative_path
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(source.read_bytes())
            manifest_path = temporary_root / SOURCE_PATHS["manifest"]
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["classification"]["scientific_result"] = True
            manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
            with self.assertRaisesRegex(DashboardArtifactError, "scientific"):
                build_dashboard_payload(temporary_root)


if __name__ == "__main__":
    unittest.main()
