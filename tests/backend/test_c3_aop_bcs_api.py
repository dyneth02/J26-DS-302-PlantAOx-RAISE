from __future__ import annotations

import pytest

from plantaox.c3_aop_bcs.dashboard_backend import DashboardArtifactError

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_health_reports_the_validated_c3_run(client):
    response = await client.get("/api/v1/c3/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "component": "c3_aop_bcs",
        "api_version": "c3-dashboard-api-v1",
        "run_id": "c3_aop_bcs_pp1_dummy_pilot_run_v1",
        "artifact_count": 12,
    }


async def test_dashboard_preserves_the_artifact_backed_contract(client):
    response = await client.get("/api/v1/c3/dashboard")
    assert response.status_code == 200
    payload = response.json()
    assert payload["overview"] == {
        "pilotSubjects": 20,
        "pilotVariants": 449,
        "fullEligibleSubjects": 734,
        "fullVariants": 10036,
    }
    assert [item["pilotCount"] for item in payload["perturbations"]] == [54, 150, 245]
    assert payload["chartData"]["source"]["recordCount"] == 449
    assert len(payload["chartData"]["absoluteDeltaDistribution"]) == 10
    assert [item["type"] for item in payload["chartData"]["predictionFlips"]] == ["P1", "P2", "P3"]
    assert {item["perturbation_type"] for item in payload["examples"]} == {"P1", "P2", "P3"}
    assert payload["classification"]["software_testing_only"] is True
    assert payload["classification"]["scientific_result"] is False
    assert payload["classification"]["real_predictor_scoring_completed"] is False


async def test_sections_and_allow_listed_figures_are_available(client):
    metrics = await client.get("/api/v1/c3/sections/metrics")
    assert metrics.status_code == 200
    assert metrics.json()["metrics"]["primaryDelta"] == pytest.approx(0.05)

    dashboard = (await client.get("/api/v1/c3/dashboard")).json()
    figure = await client.get(dashboard["figures"][0]["file"])
    assert figure.status_code == 200
    assert figure.headers["content-type"] == "image/svg+xml"
    assert (await client.get("/api/v1/c3/figures/not-allowed.svg")).status_code == 404
    assert (await client.get("/api/v1/c3/sections/not-a-section")).status_code == 422


async def test_artifact_failures_use_the_shared_503_contract(client, monkeypatch):
    def fail_closed(*_args, **_kwargs):
        raise DashboardArtifactError("C3 evidence failed validation")

    monkeypatch.setattr(
        "backend.app.services.c3_aop_bcs.dashboard.build_dashboard_payload", fail_closed
    )
    response = await client.get("/api/v1/c3/dashboard")
    assert response.status_code == 503
    assert response.json() == {
        "error": "artifact_unavailable",
        "detail": "C3 evidence failed validation",
        "artifact_path": None,
    }
