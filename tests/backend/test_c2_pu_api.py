from __future__ import annotations

import pytest

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_overview_reports_frozen_release(client):
    resp = await client.get("/api/v1/c2/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert body["freeze_id"] == "c2_pp1_freeze_v1"
    assert body["release_tag"] == "c2-pp1-v1"
    assert "not established" in body["caveats"]["scientific_status"]


async def test_fr1_summary_matches_frozen_counts(client):
    resp = await client.get("/api/v1/c2/fr1/summary")
    assert resp.status_code == 200
    body = resp.json()
    assert body["positive_pool_provisional"] == 1205
    assert body["evidence_tiers"] == {"e1": 670, "e2": 535, "total": 1205}
    assert body["graphpart_retained"] == 834


async def test_fr2_pools_counts(client):
    resp = await client.get("/api/v1/c2/fr2/pools")
    assert resp.status_code == 200
    body = resp.json()
    pools = {p["pool"]: p for p in body["pools"]}
    assert pools["C1"]["unique_sequence_count"] == 3788
    assert pools["C3"]["record_count"] == 2325
    assert body["c3_selected_per_fold"] == 2000


async def test_fr2_c3_fold_returns_exactly_2000_rows_and_is_sorted_by_rank(client):
    resp = await client.get("/api/v1/c2/fr2/c3-folds/0")
    assert resp.status_code == 200
    body = resp.json()
    assert body["n_rows"] == 2000
    ranks = [row["rank"] for row in body["top_examples"]]
    assert ranks == sorted(ranks)


async def test_fr2_c3_fold_rejects_out_of_range_fold(client):
    resp = await client.get("/api/v1/c2/fr2/c3-folds/99")
    assert resp.status_code == 422  # path constraint (lt=5) rejects before reaching the service


async def test_fr3_examples_cover_every_pool_role(client):
    resp = await client.get("/api/v1/c2/fr3/examples")
    assert resp.status_code == 200
    body = resp.json()
    assert body["fold_id"] == 0
    roles = {ex["role"] for ex in body["examples"]}
    assert "C1" in roles and "C2" in roles and "FR1_positive_fold0_training" in roles
    for example in body["examples"]:
        assert example["descriptors"] is not None
        assert len(example["descriptors"]) == 15


async def test_fr3_features_unknown_peptide_is_404(client):
    resp = await client.get("/api/v1/c2/fr3/features/does-not-exist")
    assert resp.status_code == 404


async def test_fr3_features_known_peptide(client):
    resp = await client.get("/api/v1/c2/fr3/features/C1-00174EE65A")
    assert resp.status_code == 200
    assert resp.json()["peptide_id"] == "C1-00174EE65A"


async def test_fr4_evaluation_reports_all_five_models_with_negative_mcc(client):
    resp = await client.get("/api/v1/c2/fr4/evaluation")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["models"]) == 5
    assert all(model["mcc"] < 0 for model in body["models"])
    assert all(model["auroc"] < 0.5 for model in body["models"])
    assert "not a measured false-positive rate" in body["challenge_behavior_note"]


async def test_fr4_curriculum_has_three_stages_in_order(client):
    resp = await client.get("/api/v1/c2/fr4/curriculum")
    assert resp.status_code == 200
    body = resp.json()
    assert body["stage_order"] == ["C1", "C2", "C3"]
    assert [s["training_pool"] for s in body["stages"]] == ["C1", "C2", "C3"]


async def test_artifact_status_reports_full_inventory(client):
    resp = await client.get("/api/v1/c2/artifacts/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_tracked"] == 170
    assert body["present_count"] + body["missing_count"] == 170
