from __future__ import annotations

import csv
from io import StringIO
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.c4_screen.artifacts import c4_data_dir


def test_health_and_meta(c4_client):
    assert c4_client.get("/api/v1/c4/health").json() == {"status": "ok", "component": "c4_screen"}
    response = c4_client.get("/api/v1/c4/meta")
    assert response.status_code == 200
    body = response.json()
    assert body["cloud"] == {"source": "mock_cloud", "n": 2, "status": "mock"}
    assert body["signal_sources"]["SIM_C1"] == "mock"
    assert body["output_manifest_hash"]
    assert any("MOCK" in warning for warning in body["warnings"])
    assert any("No retrieval metrics" in warning for warning in body["warnings"])


def test_funnel_tier_summary_and_sensitivity(c4_client):
    funnel = c4_client.get("/api/v1/c4/funnel")
    assert funnel.status_code == 200
    assert [row["plant"] for row in funnel.json()] == ["rice", "soybean"]
    assert all(row["embedded"] >= 0 for row in funnel.json())

    summary = c4_client.get("/api/v1/c4/tiers/summary?plant=rice")
    assert summary.status_code == 200
    body = summary.json()
    assert body["plant"] == "rice"
    assert {row["tier"] for row in body["overall"]} == {1, 3}
    assert body["by_length_bin"][0]["length_bin"] == "3-10"
    assert body["sensitivity_label"] == "sensitivity, not production"
    assert body["mean_centering_sensitivity"][0]["reference_source"] == "mock_cloud"


def test_ad_histogram_and_lengths(c4_client):
    histogram = c4_client.get("/api/v1/c4/ad/histogram?plant=rice&bins=8")
    assert histogram.status_code == 200
    body = histogram.json()
    assert len(body["cloud"]["counts"]) == len(body["candidates"]["counts"]) == 8
    assert body["t1"] == pytest.approx(.3)
    assert body["t2"] == pytest.approx(.4)
    assert body["cloud_source"] == "mock_cloud"

    lengths = c4_client.get("/api/v1/c4/lengths")
    assert lengths.status_code == 200
    by_length = {row["length"]: row for row in lengths.json()["distributions"]}
    assert by_length[3]["candidate_count"] == 1
    assert by_length[2]["cloud_count"] == 1


def test_candidate_filters_order_pagination_and_validation(c4_client):
    response = c4_client.get("/api/v1/c4/candidates?plant=rice&tier=3&len_min=3&len_max=5&cs_min=0&cs_max=0&q=WY&page=1&page_size=1")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["peptide_id"] == "p2"

    assert c4_client.get("/api/v1/c4/candidates?page_size=201").status_code == 422
    assert c4_client.get("/api/v1/c4/candidates?len_min=10&len_max=3").status_code == 422
    assert c4_client.get("/api/v1/c4/candidates?plant=tomato").status_code == 422


def test_candidate_evidence_card_and_404(c4_client):
    response = c4_client.get("/api/v1/c4/candidates/p1")
    assert response.status_code == 200
    body = response.json()
    assert body["sequence"] == "ACD"
    assert body["parent_accessions"] == ["PARENT1"]
    assert body["enzymes"] == ["pepsin_ph1.3>trypsin"]
    assert body["signal_sources"] == {"SIM_C1": "mock", "PROB_C2": "mock", "BCS": "mock"}
    assert body["injected_demo_case"] is True
    assert c4_client.get("/api/v1/c4/candidates/not-a-peptide").status_code == 404


def test_cards_exclude_tier_three_and_abstained_are_red_zero(c4_client):
    cards = c4_client.get("/api/v1/c4/cards/rice?limit=50")
    assert cards.status_code == 200
    assert all(card["tier"] in (1, 2) and card["flag"] in ("GREEN", "AMBER") for card in cards.json()["cards"])
    assert c4_client.get("/api/v1/c4/cards/rice?limit=51").status_code == 422

    abstained = c4_client.get("/api/v1/c4/abstained/rice?page=1&page_size=10")
    assert abstained.status_code == 200
    assert abstained.json()["total"] == 1
    item = abstained.json()["items"][0]
    assert (item["tier"], item["flag"], item["CS"]) == (3, "RED", 0)
    assert c4_client.get("/api/v1/c4/abstained/tomato").status_code == 422


def test_cards_csv_export(c4_client):
    response = c4_client.get("/api/v1/c4/export/cards.csv?plant=rice")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    rows = list(csv.DictReader(StringIO(response.text)))
    assert rows
    assert all(row["tier"] in ("1", "2") for row in rows)
    assert c4_client.get("/api/v1/c4/export/cards.csv?plant=tomato").status_code == 422


@pytest.mark.skipif(
    not all((c4_data_dir() / name).is_file() for name in (
        "candidates.parquet", "plant_membership.parquet", "c4_ad_tiers.parquet",
        "c4_ranked_candidates.parquet", "c4_output_manifest.json",
    )),
    reason="C4 frozen outputs are not present in this checkout",
)
def test_smoke_against_real_checkout_artifacts():
    with TestClient(app) as client:
        meta = client.get("/api/v1/c4/meta")
        assert meta.status_code == 200
        assert meta.json()["cloud"]["source"] == "mock_cloud"
        assert client.get("/api/v1/c4/funnel").status_code == 200
        assert client.get("/api/v1/c4/cards/rice?limit=5").status_code == 200
