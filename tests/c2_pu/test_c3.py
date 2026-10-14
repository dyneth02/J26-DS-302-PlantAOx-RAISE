"""Tests for curation/c3.py -- fold-safe centroid construction and ranking
(Bucket 2.3, C3 hard-challenge selection). The fold-safety property (a
fold's centroid never includes that fold's own positives) is the
methodological crux here and gets its own dedicated test.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from plantaox.c2_pu.curation.c3 import (
    compute_fold_centroids,
    load_fold_challenges,
    rank_candidates_for_fold,
    select_top_n_per_fold,
    validate_c3_fold_contract,
)


def test_compute_fold_centroids_excludes_the_held_out_fold_itself():
    # Fold 0's positive is an extreme outlier; if it leaked into fold 0's
    # own centroid, that centroid would be dragged toward it. It must not.
    embeddings = {
        "p0": np.array([100.0, 100.0]),  # fold 0 -- the held-out outlier
        "p1": np.array([1.0, 0.0]),  # fold 1
        "p2": np.array([0.0, 1.0]),  # fold 2
    }
    fold_of = {"p0": 0, "p1": 1, "p2": 2}
    centroids = compute_fold_centroids(embeddings, fold_of, n_folds=3)

    # Fold 0's centroid is fit on p1, p2 only -- must not reflect p0 at all.
    np.testing.assert_allclose(centroids[0], np.mean([[1.0, 0.0], [0.0, 1.0]], axis=0))
    # Fold 1's centroid is fit on p0, p2 -- DOES include the outlier (it's
    # not fold 1's own held-out positive), so it's dragged toward it.
    np.testing.assert_allclose(centroids[1], np.mean([[100.0, 100.0], [0.0, 1.0]], axis=0))


def test_compute_fold_centroids_raises_if_a_fold_has_no_training_positives():
    embeddings = {"p0": np.array([1.0, 0.0])}
    fold_of = {"p0": 0}
    with pytest.raises(ValueError, match="zero training positives"):
        compute_fold_centroids(embeddings, fold_of, n_folds=1)


def test_rank_candidates_for_fold_orders_by_descending_cosine_similarity():
    centroid = np.array([1.0, 0.0])
    candidates = {
        "near": np.array([1.0, 0.1]),  # nearly parallel -- high similarity
        "far": np.array([0.0, 1.0]),  # orthogonal -- zero similarity
        "opposite": np.array([-1.0, 0.0]),  # anti-parallel -- most negative
    }
    ranking = rank_candidates_for_fold(candidates, centroid, fold_id=0)
    assert ranking.peptide_ids == ["near", "far", "opposite"]
    assert ranking.similarities[0] > ranking.similarities[1] > ranking.similarities[2]


def test_rank_candidates_for_fold_handles_zero_vector_without_crashing():
    centroid = np.array([1.0, 0.0])
    candidates = {"zero": np.array([0.0, 0.0]), "normal": np.array([1.0, 0.0])}
    ranking = rank_candidates_for_fold(candidates, centroid, fold_id=0)
    assert set(ranking.peptide_ids) == {"zero", "normal"}
    assert all(np.isfinite(s) for s in ranking.similarities)


def test_select_top_n_per_fold_returns_correct_rank_and_truncates():
    from plantaox.c2_pu.curation.c3 import FoldRanking

    rankings = [
        FoldRanking(fold_id=0, peptide_ids=["a", "b", "c"], similarities=[0.9, 0.5, 0.1]),
        FoldRanking(fold_id=1, peptide_ids=["x", "y"], similarities=[0.8, 0.2]),
    ]
    selected = select_top_n_per_fold(rankings, n=2)
    assert selected[0] == [("a", 0.9, 1), ("b", 0.5, 2)]
    assert selected[1] == [("x", 0.8, 1), ("y", 0.2, 2)]  # fold 1 only has 2 -- no crash


def test_different_folds_produce_different_rankings_when_centroids_differ():
    # End-to-end sanity: two folds with genuinely different training
    # centroids should (generically) rank the same candidates differently.
    embeddings = {
        "p0": np.array([10.0, 0.0]),
        "p1": np.array([0.0, 10.0]),
        "p2": np.array([5.0, 5.0]),
    }
    fold_of = {"p0": 0, "p1": 1, "p2": 2}
    centroids = compute_fold_centroids(embeddings, fold_of, n_folds=3)
    candidates = {"c1": np.array([1.0, 0.0]), "c2": np.array([0.0, 1.0])}

    ranking_fold0 = rank_candidates_for_fold(candidates, centroids[0], fold_id=0)
    ranking_fold1 = rank_candidates_for_fold(candidates, centroids[1], fold_id=1)
    assert ranking_fold0.peptide_ids != ranking_fold1.peptide_ids


def _write_ranking_csv(path, rows):
    pd.DataFrame(rows, columns=["fold_id", "peptide_id", "sequence", "rank", "cosine_similarity"]).to_csv(
        path, index=False
    )


def test_load_fold_challenges_returns_only_that_folds_rows_sorted_by_rank(tmp_path):
    ranking_path = tmp_path / "ranking.csv"
    _write_ranking_csv(
        ranking_path,
        [
            (0, "p2", "AAA", 2, 0.5),
            (0, "p1", "BBB", 1, 0.9),
            (1, "p3", "CCC", 1, 0.8),
        ],
    )
    fold0 = load_fold_challenges(ranking_path, fold_id=0)
    assert list(fold0["peptide_id"]) == ["p1", "p2"]  # sorted by rank, not file order
    assert set(fold0["fold_id"]) == {0}

    fold1 = load_fold_challenges(ranking_path, fold_id=1)
    assert list(fold1["peptide_id"]) == ["p3"]


def test_load_fold_challenges_raises_on_unknown_fold_rather_than_returning_empty(tmp_path):
    ranking_path = tmp_path / "ranking.csv"
    _write_ranking_csv(ranking_path, [(0, "p1", "AAA", 1, 0.9)])
    with pytest.raises(ValueError, match="fold_id=99"):
        load_fold_challenges(ranking_path, fold_id=99)


def test_there_is_no_function_in_this_module_that_returns_all_folds_at_once():
    # Structural guard against the exact misuse Step 5 warns about: a
    # future helper that "conveniently" loads the whole union as one
    # fold's challenge set. If someone adds one, this test forces them to
    # consciously name it something that can't be mistaken for
    # load_fold_challenges and to update this test, rather than silently
    # letting a leakage-reintroducing shortcut slip in.
    import plantaox.c2_pu.curation.c3 as c3_module

    public_names = [n for n in dir(c3_module) if not n.startswith("_")]
    suspicious = [n for n in public_names if "all_fold" in n.lower() or "union" in n.lower()]
    assert suspicious == []


def _valid_fixture(n_folds=3, top_n=2):
    embeddings = {f"p{i}": np.array([float(i), float(i) * 2]) for i in range(9)}
    fold_of = {f"p{i}": i % n_folds for i in range(9)}
    ranking_rows = []
    fasta_ids = set()
    for fold_id in range(n_folds):
        for rank in range(1, top_n + 1):
            pid = f"cand_{fold_id}_{rank}"
            ranking_rows.append({"fold_id": fold_id, "peptide_id": pid, "rank": rank, "cosine_similarity": 1.0 / rank})
            fasta_ids.add(pid)
    return embeddings, fold_of, pd.DataFrame(ranking_rows), fasta_ids


def test_validate_c3_fold_contract_passes_on_a_well_formed_build():
    embeddings, fold_of, ranking_df, fasta_ids = _valid_fixture()
    result = validate_c3_fold_contract(embeddings, fold_of, ranking_df, fasta_ids, top_n_per_fold=2)
    assert result["fold_safety_verified"] is True
    assert result["n_folds"] == 3


def test_validate_c3_fold_contract_catches_wrong_row_count_per_fold():
    embeddings, fold_of, ranking_df, fasta_ids = _valid_fixture()
    ranking_df = ranking_df[~((ranking_df["fold_id"] == 0) & (ranking_df["rank"] == 2))]
    with pytest.raises(AssertionError, match="expected 2"):
        validate_c3_fold_contract(embeddings, fold_of, ranking_df, fasta_ids, top_n_per_fold=2)


def test_validate_c3_fold_contract_catches_fasta_ranking_mismatch():
    embeddings, fold_of, ranking_df, fasta_ids = _valid_fixture()
    fasta_ids = fasta_ids | {"phantom_sequence_not_in_ranking"}
    with pytest.raises(AssertionError, match="do not exactly match"):
        validate_c3_fold_contract(embeddings, fold_of, ranking_df, fasta_ids, top_n_per_fold=2)


def test_validate_c3_fold_contract_catches_duplicate_ranks():
    embeddings, fold_of, ranking_df, fasta_ids = _valid_fixture(top_n=3)
    # Fold 0's 3 rows get ranks [1, 1, 3] -- still spans 1..3 (so the
    # contiguity check alone wouldn't catch it), but rank 1 is duplicated
    # and rank 2 is missing.
    fold0_idx = ranking_df[ranking_df["fold_id"] == 0].index
    ranking_df.loc[fold0_idx, "rank"] = [1, 1, 3]
    with pytest.raises(AssertionError, match="duplicate ranks"):
        validate_c3_fold_contract(embeddings, fold_of, ranking_df, fasta_ids, top_n_per_fold=3)
