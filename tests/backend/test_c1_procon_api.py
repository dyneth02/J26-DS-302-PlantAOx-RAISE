from __future__ import annotations

import pytest

from backend.app.core.errors import ArtifactUnavailableError
from backend.app.services.c1_procon import artifacts as c1_artifacts

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


async def test_overview_reports_benchmark_and_negative_result(client):
    resp = await client.get("/api/v1/c1/overview")
    assert resp.status_code == 200
    body = resp.json()
    assert body["benchmark_fingerprint"] == "47d9c2a2fff63eb1"
    assert body["counts"]["peptides"] == 1389
    assert body["counts"]["homology_groups"] == 573
    assert body["counts"]["strict_pool"] == 669
    assert body["counts"]["strict_mc_active"] == 104
    assert body["counts"]["strict_frs_only"] == 565
    assert body["label_counts"] == {"FRS": 565, "FRS;MC": 86, "MC": 63, "GEN": 675}
    assert len(body["pipeline_steps"]) == 8
    assert "Negative result" in body["caveats"]["scientific_status"]
    assert any("no trained head beats" in f for f in body["headline_findings"])
    hero = {h["label"]: h["value"] for h in body["hero_stats"]}
    assert hero["unique peptides"] == "1,389"
    assert hero["trained runs beat the untrained embedding"] == "0 of 25"


async def test_dataset_exposes_the_source_and_tripeptide_confounds(client):
    resp = await client.get("/api/v1/c1/dataset")
    assert resp.status_code == 200
    body = resp.json()
    assert body["strict_pool"] == {"peptides": 669, "mc_active": 104, "frs_only": 565}
    sources = {s["source_group"]: s for s in body["source_by_class"]}
    # every FRS-only peptide comes from one database; part of the MC-active set is external literature
    assert sum(1 for s in sources.values() if s["frs_only"] > 0) == 1
    assert body["tripeptide_share"]["frs_only"] > 2 * body["tripeptide_share"]["mc_active"]
    assert abs(body["mean_length"]["frs_only"] - body["mean_length"]["mc_active"]) < 0.5
    assert any("does not mean inactive" in n for n in body["notes"])


async def test_retrieval_shows_trained_heads_below_untrained(client):
    resp = await client.get("/api/v1/c1/retrieval")
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "strict" and body["n_queries"] == 49
    assert body["trained_runs_total"] == 25
    assert body["trained_runs_above_untrained"] == 0
    ap = {r["representation"]: r["ap"] for r in body["representations"]}
    assert ap["Primary"] < ap["RAW 650M"] < ap["LENGTH"]
    assert abs(body["chance_ap"] - 0.17692) < 1e-4
    assert all(p["delta_ap"] < 0 for p in body["paired"] if p["comparison"].startswith("Primary vs untrained"))
    assert all(c["mean_cos_heldout"] >= 0 for c in body["collapse"])


async def test_probe_reports_null_band_and_leakage_inflation(client):
    resp = await client.get("/api/v1/c1/probe")
    assert resp.status_code == 200
    body = resp.json()
    assert 0.45 < body["null_band"]["auroc"] < 0.55
    grouped = {r["features"]: r["auroc"] for r in body["grouped"]}
    assert grouped["SOURCE"] > grouped["ESM-2 650M"]
    assert "RANDOM noise (seed 0)" not in grouped  # a single noise draw is not a chance reference
    assert 0.15 < body["leakage_inflation"]["ESM-2 650M"] < 0.22
    assert "not mechanism evidence" in body["evaluation_note"]


async def test_confounds_state_that_no_esm2_specific_signal_remains(client):
    resp = await client.get("/api/v1/c1/confounds")
    assert resp.status_code == 200
    body = resp.json()
    assert "no ESM-2-specific" in body["verdict"]
    strict = {r["features"]: r["auroc"] for r in body["strict"]}
    assert strict["AAC+LEN+SRC"] > strict["ESM-2 650M"]
    length_matched = {(r["pool"], r["features"]): r for r in body["length_matched"]}
    length_only = length_matched[("strict", "LENGTH")]
    assert length_only["auroc_mean"] < 0.5  # length signal removed by matching
    assert length_only["tripeptide_share_mc"] == pytest.approx(length_only["tripeptide_share_frs"])
    assert all(p["train_frac"] <= 1.0 for p in body["learning_curve"])


async def test_artifact_status_lists_every_expected_file(client):
    resp = await client.get("/api/v1/c1/artifacts/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["all_present"] is True and body["missing"] == []
    assert len(body["artifacts"]) == sum(len(v) for v in c1_artifacts.EXPECTED_ARTIFACTS.values())


async def test_missing_artifact_is_a_503_not_mock_data(client, monkeypatch):
    def _boom(relative, settings=None):
        raise ArtifactUnavailableError("missing for test", artifact_path="x")

    monkeypatch.setattr("backend.app.services.c1_procon.retrieval.read_csv", _boom)
    resp = await client.get("/api/v1/c1/retrieval")
    assert resp.status_code == 503
    assert resp.json()["error"] == "artifact_unavailable"


async def test_lookup_finds_a_benchmark_peptide_and_nearest_neighbours(client):
    resp = await client.get("/api/v1/c1/lookup", params={"sequence": "efqi "})  # case and spaces are normalised
    assert resp.status_code == 200
    body = resp.json()
    assert body["valid"] is True and body["in_benchmark"] is True and body["query"] == "EFQI"
    assert body["record"]["labels"] in {"FRS", "MC", "FRS;MC", "GEN"}
    assert abs(sum(body["composition"].values()) - 1.0) < 1e-9
    assert len(body["nearest"]) == 5 and all(n["sequence"] != "EFQI" for n in body["nearest"])
    assert body["nearest"][0]["cosine"] >= body["nearest"][-1]["cosine"]
    assert any("weak probe" in n for n in body["notes"])


async def test_lookup_rejects_non_canonical_residues_and_empty_input(client):
    bad = (await client.get("/api/v1/c1/lookup", params={"sequence": "AXZ1"})).json()
    assert bad["valid"] is False and "non-canonical" in bad["problems"][0] and bad["nearest"] == []
    empty = (await client.get("/api/v1/c1/lookup")).json()
    assert empty["valid"] is False and empty["problems"] == ["empty input"]


async def test_lookup_of_a_new_peptide_explains_that_scoring_is_offline(client):
    body = (await client.get("/api/v1/c1/lookup", params={"sequence": "W" * 50})).json()
    assert body["valid"] is True and body["in_benchmark"] is False and body["record"] is None
    assert any("outside the benchmark range" in n for n in body["notes"])
    assert any("not in the benchmark" in n for n in body["notes"])


async def test_embedding_shows_that_training_collapses_instead_of_separating_mechanisms(client):
    resp = await client.get("/api/v1/c1/embedding")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["points"]) == 1389
    spaces = {s["key"]: s for s in body["spaces"]}
    assert set(spaces) == {"esm2", "primary", "maxspread"}
    # untrained ESM-2: MC-active and FRS-only peptides are not separated
    assert abs(spaces["esm2"]["separation"]) < 0.02
    # the main trained head collapses: nearly every pair of peptides has cosine similarity ~1
    assert spaces["primary"]["all_pairs"] > 0.99
    # and its nearest neighbours are no better than chance at finding MC-active peptides
    chance = body["meta"]["chance_mc_neighbour_purity"]
    assert spaces["primary"]["mc_neighbour_purity"] <= chance
    assert body["meta"]["peptides_ge_10_aa"] + body["meta"]["peptides_lt_10_aa"] == 1389
    point = body["points"][0]
    assert set(point["coords"]) == {"esm2", "primary", "maxspread"} and len(point["coords"]["esm2"]) == 2
    counts = {c["pair_set"]: c["pairs"] for c in body["pair_counts"]}
    assert counts["positive_pairs"] == 10195 and counts["ablation_random_pairs"] == 10195
    assert len(body["pair_examples"]) == 6
    assert {e["mechanism"] for e in body["pair_examples"]} == {"MC", "FRS"}
