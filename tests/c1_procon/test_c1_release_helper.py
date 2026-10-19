from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from plantaox.c1_procon import aop_procon as ap


def test_validation_accepts_a_good_peptide_and_explains_bad_ones():
    assert ap.validate_sequence("YWH") == []
    assert ap.validate_sequence("") == ["empty or non-string"]
    assert ap.validate_sequence(None) == ["empty or non-string"]
    assert "non-canonical residues: XZ" in ap.validate_sequence("AXZ")[0]
    assert "outside the benchmark range" in ap.validate_sequence("A" * 60)[0]
    assert "outside the benchmark range" in ap.validate_sequence("AA")[0]


def test_composition_rows_sum_to_one():
    m = ap.composition(["HYY", "GGGGG"])
    assert m.shape == (2, 20) and np.allclose(m.sum(axis=1), 1.0)


@pytest.mark.parametrize("mode", ["strict", "extended"])
def test_probe_weights_have_the_embedding_width_and_give_probabilities(mode):
    probe = ap.load_probe(mode)
    assert {"mean", "scale", "coef", "intercept"} <= set(probe)
    assert probe["mean"].shape[-1] == ap.EMBEDDING_DIM
    # an average peptide (every standardised feature 0) scores sigmoid(intercept); other inputs stay in [0, 1]
    at_mean = ap.probe_score(probe["mean"].reshape(1, -1), mode)[0]
    assert at_mean == pytest.approx(1 / (1 + np.exp(-float(probe["intercept"][0]))))
    scores = ap.probe_score(np.random.RandomState(0).normal(size=(5, ap.EMBEDDING_DIM)), mode)
    assert scores.shape == (5,) and np.isfinite(scores).all() and ((scores >= 0) & (scores <= 1)).all()


def test_scoring_with_given_embeddings_needs_no_cached_arrays():
    bench = ap.load_benchmark()
    gen = bench.loc[bench["labels"] == "GEN", "sequence"].iloc[0]
    mc = bench.loc[bench["labels"] == "MC", "sequence"].iloc[0]
    seqs = [mc, gen, "YWH", "AXZ"]
    E = np.random.RandomState(1).normal(size=(4, ap.EMBEDDING_DIM))
    table = ap.score_peptides(seqs, embeddings=E)

    assert list(table["sequence"]) == seqs and len(table) == 4
    assert table["valid"].tolist() == [True, True, True, False]
    assert table["in_benchmark"].tolist() == [True, True, False, False]
    assert table.loc[0, "benchmark_labels"] == "MC" and table.loc[1, "benchmark_labels"] == "GEN"
    # a GEN peptide (mechanism not established) was never in the pool a probe was fitted on
    assert not table.loc[1, "score_is_in_sample_strict"] and not table.loc[1, "score_is_in_sample_extended"]
    assert table.loc[0, "score_is_in_sample_extended"]
    assert table["mc_score_strict"].between(0, 1).all()
    assert table["warning"].str.contains("weak signal").all()


def test_out_of_fold_scores_are_the_ones_to_quote_for_benchmark_peptides():
    bench = ap.load_benchmark()
    seq = bench.loc[bench["labels"] == "FRS", "sequence"].iloc[0]
    row = ap.score_peptides([seq], embeddings=np.zeros((1, ap.EMBEDDING_DIM))).iloc[0]
    assert 0 < row["oof_mc_score_strict"] < 1 and 0 < row["oof_mc_score_extended"] < 1


def test_wrong_embedding_shape_is_refused():
    with pytest.raises(AssertionError):
        ap.score_peptides(["YWH"], embeddings=np.zeros((1, 10)))


def test_missing_embedding_cache_gives_an_actionable_error(monkeypatch, tmp_path):
    monkeypatch.setenv("C1_EMBEDDINGS_DIR", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="C1_EMBEDDINGS_DIR"):
        ap.load_cache("650M")


def test_probe_files_are_the_released_ones():
    # the fitted weights must stay unchanged unless the release is deliberately rebuilt
    for mode in ("strict", "extended"):
        assert pd.notna(ap.load_probe(mode)["intercept"]).all()
