"""Tests for curation/c3.py -- fold-safe centroid construction and ranking
(Bucket 2.3, C3 hard-challenge selection). The fold-safety property (a
fold's centroid never includes that fold's own positives) is the
methodological crux here and gets its own dedicated test.
"""

from __future__ import annotations

import numpy as np
import pytest

from plantaox.c2_pu.curation.c3 import (
    compute_fold_centroids,
    rank_candidates_for_fold,
    select_top_n_per_fold,
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
