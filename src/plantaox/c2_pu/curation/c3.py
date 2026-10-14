"""Bucket 2.3 (FR2/C3) -- fold-safe ESM-2 centroid construction and
candidate-to-centroid ranking for hard-challenge selection.

**Fold-safety is the entire point of this module** (confirmed explicitly
with the project owner, 2026-10-14, and already required by AGENTS.md
rule 5): a candidate's eligibility for fold *k*'s hard-challenge pool must
be decided using a positive-pool centroid fit on the OTHER four training
folds only, never on fold *k*'s own (held-out) positives. If a single
global centroid (built from all 834 positives) were used instead, then at
evaluation time -- MCC(C3 test) in RNIS -- the model would be scored on C3
examples whose "hardness" was partly *chosen because* of their similarity
to the very positives being held out that round. That correlation is a
selection-leakage channel distinct from (and not caught by) ordinary
sequence-identity/homology leakage checks, since it survives even when no
C3 sequence exactly or near-exactly matches a held-out positive.

Concretely: for 5-fold GraphPart splits, this module produces 5 *different*
centroids and 5 *different* rankings of the same candidate universe --
fold k's ranking only ever used positives from the other 4 folds.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


def compute_fold_centroids(
    positive_embeddings: dict[str, np.ndarray], fold_of: dict[str, int], n_folds: int
) -> dict[int, np.ndarray]:
    """One centroid per fold id in ``range(n_folds)``, each the mean of every
    positive embedding whose fold is NOT that id (i.e. the training folds for
    that fold's held-out round). Raises if a fold would end up with zero
    training positives (fit on nothing) rather than silently returning a
    NaN/zero centroid.
    """
    centroids: dict[int, np.ndarray] = {}
    for fold_id in range(n_folds):
        training_vectors = [
            vec for pid, vec in positive_embeddings.items() if fold_of[pid] != fold_id
        ]
        if not training_vectors:
            raise ValueError(f"Fold {fold_id} has zero training positives -- cannot fit a centroid.")
        centroids[fold_id] = np.mean(np.stack(training_vectors), axis=0)
    return centroids


def _cosine_similarity(matrix: np.ndarray, vector: np.ndarray) -> np.ndarray:
    matrix_norms = np.linalg.norm(matrix, axis=1)
    vector_norm = np.linalg.norm(vector)
    denom = matrix_norms * vector_norm
    denom = np.where(denom == 0, np.finfo(float).eps, denom)
    return (matrix @ vector) / denom


@dataclass(frozen=True)
class FoldRanking:
    fold_id: int
    peptide_ids: list[str]  # sorted by descending similarity (hardest first)
    similarities: list[float]


def rank_candidates_for_fold(
    candidate_embeddings: dict[str, np.ndarray], centroid: np.ndarray, fold_id: int
) -> FoldRanking:
    """Rank every candidate by cosine similarity to one fold's training-only
    centroid, descending (closest to the positive centroid = hardest)."""
    peptide_ids = list(candidate_embeddings.keys())
    matrix = np.stack([candidate_embeddings[pid] for pid in peptide_ids])
    similarities = _cosine_similarity(matrix, centroid)
    order = np.argsort(-similarities)
    return FoldRanking(
        fold_id=fold_id,
        peptide_ids=[peptide_ids[i] for i in order],
        similarities=[float(similarities[i]) for i in order],
    )


def select_top_n_per_fold(rankings: list[FoldRanking], n: int) -> dict[int, list[tuple[str, float, int]]]:
    """Top-``n`` (peptide_id, similarity, rank [1-indexed]) per fold ranking."""
    return {
        ranking.fold_id: [
            (pid, sim, rank)
            for rank, (pid, sim) in enumerate(
                zip(ranking.peptide_ids[:n], ranking.similarities[:n]), start=1
            )
        ]
        for ranking in rankings
    }
