import json

import numpy as np
import pandas as pd
import pytest

from plantaox.c4_screen.ad import assign_tiers, calibrate_ad
from plantaox.c4_screen.cards import _reliability_flag, make_cards
from plantaox.c4_screen.cloud import build_reference_meta
from plantaox.c4_screen.dashboard import build_summary, write_dashboard
from plantaox.c4_screen.embed_import import EmbeddingImportError, import_embeddings, row_sequence_sha256
from plantaox.c4_screen.score import score_candidates
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
    assert "MOCK CLOUD" in html.read_text(encoding="utf-8") and "__PAYLOAD__" not in html.read_text(encoding="utf-8")
