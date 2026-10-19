import json

import numpy as np
import pandas as pd
import pytest

from plantaox.c4_screen.ad import assign_tiers, calibrate_ad
from plantaox.c4_screen.cards import _reliability_flag, make_cards
from plantaox.c4_screen.cloud import build_reference_meta
from plantaox.c4_screen.dashboard import build_summary, write_dashboard
from plantaox.c4_screen.embed_import import EmbeddingImportError, import_embeddings, row_sequence_sha256
from plantaox.c4_screen.score import score_candidates, weight_sweep
from plantaox.c4_screen.signals import generate_and_validate_mock_signals, validate_and_join_signals


def test_import_reports_all_missing_handoff_files(tmp_path):
    with pytest.raises(EmbeddingImportError, match="candidate embeddings") as err:
        import_embeddings(tmp_path / "candidates.parquet", tmp_path / "embeddings", expected_n=2, dim=4)
    assert "reference cloud sequences" in str(err.value)


def test_import_validates_order_hash_and_finite_values(tmp_path):
    root = tmp_path / "embeddings"
    root.mkdir()
    candidates = pd.DataFrame({"peptide_id": ["p1", "p2"], "sequence": ["ACD", "EFG"]})
    candidates.to_parquet(tmp_path / "candidates.parquet", index=False)
    candidates.to_parquet(root / "c4_embedding_index.parquet", index=False)
    matrix = np.arange(8, dtype=np.float16).reshape(2, 4)
    cloud = np.arange(2000, dtype=np.float16).reshape(500, 4) + 1
    np.save(root / "c4_esm2_t33_650M.npy", matrix)
    np.save(root / "ref_cloud.npy", cloud)
    pd.DataFrame({"id": [f"c{i}" for i in range(500)], "sequence": [f"A{i}" for i in range(500)],
                  "evidence_tier": "U", "source": "mock_cloud", "is_plant": False}).to_csv(root / "ref_cloud_sequences.csv", index=False)
    manifest = {"model": "esm2_t33_650M_UR50D", "dim": 4, "n": 2,
                "row_id_sha256": row_sequence_sha256(candidates.sequence)}
    (root / "c4_embedding_manifest.json").write_text(json.dumps(manifest))
    imported = import_embeddings(tmp_path / "candidates.parquet", root, expected_n=2, dim=4)
    assert imported[2].dtype == np.float32 and imported[2].shape == (2, 4)
    assert imported[4].dtype == np.float32 and imported[4].shape == (500, 4)
    changed = pd.DataFrame({"peptide_id": ["p2", "p1"], "sequence": ["EFG", "ACD"]})
    changed.to_parquet(root / "c4_embedding_index.parquet", index=False)
    with pytest.raises(EmbeddingImportError, match="order does not exactly match"):
        import_embeddings(tmp_path / "candidates.parquet", root, expected_n=2, dim=4)


def test_cloud_metadata_requires_supplied_mock_cloud(tmp_path):
    source = tmp_path / "ref.csv"
    pd.DataFrame({"id": [f"id{i}" for i in range(500)], "sequence": ["ACD"] * 500,
                  "evidence_tier": "U", "source": "mock_cloud", "is_plant": "false"}).to_csv(source, index=False)
    with pytest.raises(ValueError, match="unique"):
        build_reference_meta(source)


def test_ad_assignment_marks_unembedded_and_calibrates_leave_one_out():
    rng = np.random.default_rng(42)
    cloud = rng.normal(size=(500, 4)).astype(np.float32)
    candidates = pd.DataFrame({"peptide_id": ["p1", "p2"], "sequence": ["ACD", "EFG"]})
    index = candidates.iloc[:1].copy()
    vectors = np.array([[1, 0, 0, 0]], dtype=np.float32)
    tiers, params, dists = assign_tiers(candidates, index, vectors, cloud)
    assert len(dists) == 500 and params["n_cloud"] == 500
    assert tiers.embedded.tolist() == [True, False]
    assert pd.isna(tiers.iloc[1].tier) and pd.isna(tiers.iloc[1].d_norm)
    assert tiers.cloud_source.eq("mock_cloud").all()
    assert calibrate_ad(cloud)[0]["definition"].startswith("leave-one-out")


def test_mock_signals_join_by_sequence_and_scoring_invariants(tmp_path):
    candidates = pd.DataFrame({"peptide_id": ["p1", "p2", "p3"],
        "sequence": ["ACD", "EFGH", "IKLMN"], "provenance": ["[]"] * 3,
        "length": [3, 4, 5]})
    tiers = pd.DataFrame({"peptide_id": candidates.peptide_id, "sequence": candidates.sequence,
        "d_AD": [0.05, 0.2, 0.8], "d_norm": [0.1, 0.4, 1.0], "tier": [1, 2, 3],
        "embedded": [True] * 3, "cloud_source": ["mock_cloud"] * 3})
    tier_input = tmp_path / "tiers.parquet"
    tiers[["sequence", "d_norm", "tier"]].to_parquet(tier_input, index=False)
    signals = tmp_path / "signals"
    generate_and_validate_mock_signals(tier_input, signals, seed=42, inject=1)
    repeated = tmp_path / "signals_repeat"
    generate_and_validate_mock_signals(tier_input, repeated, seed=42, inject=1)
    for name in ("c1_sim.parquet", "c2_prob.parquet", "c3_bcs.json", "MOCK_MANIFEST.json"):
        assert (signals / name).read_bytes() == (repeated / name).read_bytes()
    joined, bcs = validate_and_join_signals(tiers, signals)
    assert bcs["source"] == "mock"
    assert set(joined.SIM_C1_source) == {"mock"} and set(joined.PROB_C2_source) == {"mock"}
    memberships = pd.DataFrame({"peptide_id": candidates.peptide_id, "plant": ["olive"] * 3})
    config = {"weights": {"w1": .5, "w2": .5}}
    ranked = score_candidates(joined, memberships, candidates, config)
    assert ranked.loc[ranked.tier == 3, "CS"].eq(0).all()
    assert ranked.CS.between(0, 1).all()
    s1 = ranked.loc[ranked.sequence == "ACD", "CS"].iloc[0]
    s2 = ranked.loc[ranked.sequence == "EFGH", "CS"].iloc[0]
    assert .5 * joined.loc[joined.sequence == "ACD", "SIM_C1"].iloc[0] + .5 * joined.loc[joined.sequence == "ACD", "PROB_C2"].iloc[0] * .9 == pytest.approx(s1)
    assert s1 >= 0 and s2 >= 0


def test_score_decreases_with_greater_ad_distance_when_other_signals_are_fixed():
    joined = pd.DataFrame({"peptide_id": ["p1", "p2"], "sequence": ["ACD", "EFG"],
        "d_norm": [.1, .8], "tier": [1, 1], "embedded": [True, True], "SIM_C1": [.6, .6],
        "PROB_C2": [.8, .8], "SIM_C1_source": ["mock", "mock"],
        "PROB_C2_source": ["mock", "mock"], "cloud_source": ["mock_cloud", "mock_cloud"]})
    candidates = pd.DataFrame({"peptide_id": ["p1", "p2"], "sequence": ["ACD", "EFG"]})
    memberships = pd.DataFrame({"peptide_id": ["p1", "p2"], "plant": ["olive", "olive"]})
    ranked = score_candidates(joined, memberships, candidates, {"weights": {"w1": .5, "w2": .5}})
    by_sequence = ranked.set_index("sequence").CS
    assert by_sequence["ACD"] > by_sequence["EFG"]


def test_weight_sweep_runs_and_synthetic_planted_set_ranks_above_random():
    # Test-only 2,000-row sandbox; these constructed records are not project outputs.
    rng = np.random.default_rng(42)
    n, planted, dim = 2000, 20, 16
    alphabet = "ACDEFGHIKLMNPQRSTVWY"
    def encode(i):
        chars = []
        for _ in range(6):
            chars.append(alphabet[i % len(alphabet)])
            i //= len(alphabet)
        return "".join(chars)
    sequences = [encode(i) for i in range(n)]
    ids = [f"p{i:04d}" for i in range(n)]
    center = np.r_[1.0, np.zeros(dim - 1)]
    cloud = (center + rng.normal(0, .01, size=(80, dim))).astype(np.float32)
    # The first 20 planted positives are close to the synthetic cloud centroid;
    # the remaining candidates point away from it and serve as random negatives.
    vectors = np.vstack([center + rng.normal(0, .005, size=(planted, dim)),
                         -center + rng.normal(0, .05, size=(n-planted, dim))]).astype(np.float32)
    candidates = pd.DataFrame({"peptide_id": ids, "sequence": sequences})
    tiers, _, _ = assign_tiers(candidates, candidates.copy(), vectors, cloud, cloud_source="mock_cloud")
    joined = tiers.copy()
    joined["SIM_C1"] = np.r_[rng.uniform(.85, 1, planted), rng.uniform(0, .4, n-planted)]
    joined["PROB_C2"] = np.r_[rng.uniform(.85, 1, planted), rng.uniform(0, .4, n-planted)]
    joined["SIM_C1_source"] = "mock"
    joined["PROB_C2_source"] = "mock"
    memberships = pd.DataFrame({"peptide_id": ids, "plant": "synthetic"})
    default = {"weights": {"w1": .5, "w2": .5}}
    results = weight_sweep(joined, memberships, candidates, default)
    assert set(results) == {.25, .5, .75}
    assert default["weights"] == {"w1": .5, "w2": .5}
    for ranked in results.values():
        assert ranked.CS.between(0, 1).all()
        assert ranked.loc[ranked.tier == 3, "CS"].eq(0).all()
        top = set(ranked.nsmallest(planted, "rank").peptide_id)
        assert top == set(ids[:planted])


def test_sequence_key_real_signal_swap_in_procedure(tmp_path):
    # Synthetic real-source contract fixture; no biological result is asserted.
    seqs = ["ACDE", "FGHI"]
    tiers = pd.DataFrame({"peptide_id": ["p1", "p2"], "sequence": seqs,
        "d_AD": [.01, .02], "d_norm": [.1, .2], "tier": [1, 2], "embedded": [True, True],
        "cloud_source": ["mock_cloud"] * 2})
    pd.DataFrame({"sequence": seqs, "SIM_C1": [.7, .6], "source": ["real"] * 2}).to_parquet(
        tmp_path / "c1_sim.parquet", index=False)
    pd.DataFrame({"sequence": seqs, "PROB_C2": [.8, .5], "evidence_tier": ["E1", "E2"],
        "source": ["real"] * 2}).to_parquet(tmp_path / "c2_prob.parquet", index=False)
    (tmp_path / "c3_bcs.json").write_text(json.dumps({"source": "real", "strata": []}), encoding="utf-8")
    joined, bcs = validate_and_join_signals(tiers, tmp_path)
    assert bcs["source"] == "real"
    assert joined.SIM_C1_source.eq("real").all() and joined.PROB_C2_source.eq("real").all()


def test_cards_flags_summary_and_dashboard_are_mock_labelled(tmp_path):
    assert [_reliability_flag(x, .5, .7) for x in (.49, .5, .69, .7)] == ["LOW", "MEDIUM", "MEDIUM", "HIGH"]
    ranked = pd.DataFrame({"peptide_id": ["p1", "p2", "p3"], "sequence": ["ACD", "EFGH", "IKLMN"],
        "plant": ["olive"] * 3, "tier": [1, 2, 3], "CS": [.8, .4, 0.], "rank": [1, 2, 3],
        "d_AD": [.1, .4, 1.], "SIM_C1": [.8, .4, .9], "PROB_C2": [.7, .5, .95],
        "evidence_tier": ["U"] * 3, "SIM_C1_source": ["mock"] * 3, "PROB_C2_source": ["mock"] * 3,
        "length": [3, 4, 5], "provenance": ["[]"] * 3})
    config = {"plants": {"olive": {"scientific_name": "Olea europaea"}},
              "bcs_flag": {"low_below": .5, "high_at_or_above": .7}}
    mock_manifest = {"injected_demo_cases": ["IKLMN"]}
    bcs = {"source": "mock", "strata": [{"mechanism": "ALL", "length_bin": "3-10", "BCS": .44}]}
    cards = make_cards(ranked, config, mock_manifest, bcs, tmp_path / "cards.json")
    assert cards["cloud_source"] == "mock_cloud"
    assert cards["plants"]["olive"]["top_50"][0]["BCS_flag"] == "LOW"
    assert cards["plants"]["olive"]["abstained"][0]["flag"] == "RED"
    tiers = pd.DataFrame({"peptide_id": ["p1", "p2", "p3"], "sequence": ["ACD", "EFGH", "IKLMN"],
        "d_AD": [.1, .4, 1.], "d_norm": [.1, .4, 1.], "tier": [1, 2, 3], "embedded": [True] * 3,
        "plant": ["olive"] * 3})
    candidates = ranked[["peptide_id", "sequence"]].copy()
    cloud_meta = pd.DataFrame({"id": [f"c{i}" for i in range(500)], "sequence": ["ACD"] * 500,
        "evidence_tier": ["U"] * 500, "source": ["mock_cloud"] * 500, "is_plant": [False] * 500})
    funnel_path = tmp_path / "funnel.csv"
    pd.DataFrame({"plant": ["olive"], "raw_fragments": [3]}).to_csv(funnel_path, index=False)
    params = {"cloud_source": "mock_cloud", "t1": .2, "t2": .5}
    summary = build_summary(funnel_path, tiers, candidates, cloud_meta, params, {"SIM_C1": "mock"})
    html = write_dashboard(summary, cards, tmp_path / "dashboard.html")
    assert summary["cloud"]["mock"] is True and summary["embedded_count"] == 3
    assert sum(summary["d_AD_histogram"]["bins"]) == 3
    assert "MOCK CLOUD" in html.read_text(encoding="utf-8") and "__PAYLOAD__" not in html.read_text(encoding="utf-8")
