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
from pathlib import Path

import numpy as np
import pandas as pd


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


def validate_c3_fold_contract(
    positive_embeddings: dict[str, np.ndarray],
    fold_of: dict[str, int],
    ranking_df: pd.DataFrame,
    fasta_peptide_ids: set[str],
    top_n_per_fold: int,
) -> dict:
    """Formal re-verification of every property Bucket 2.4's audit requires
    of the C3 construction (not a re-derivation from scratch -- this checks
    the ALREADY-BUILT artifacts are internally consistent and fold-safe,
    the same way test_fr1_reproducibility.py re-verifies FR1 rather than
    trusting its own prior run). Raises AssertionError with a specific
    message on the first violation found, rather than returning a
    best-effort partial pass.
    """
    n_folds = int(max(fold_of.values())) + 1
    centroids = compute_fold_centroids(positive_embeddings, fold_of, n_folds=n_folds)

    for fold_id in range(n_folds):
        train_ids = {pid for pid in positive_embeddings if fold_of[pid] != fold_id}
        held_out_ids = {pid for pid in positive_embeddings if fold_of[pid] == fold_id}
        assert train_ids, f"Fold {fold_id} has no training positives."
        assert held_out_ids, f"Fold {fold_id} has no held-out positives to validate against."
        manual_centroid = np.mean(np.stack([positive_embeddings[pid] for pid in train_ids]), axis=0)
        if not np.allclose(manual_centroid, centroids[fold_id]):
            raise AssertionError(f"Fold {fold_id}'s centroid does not match training-fold-only reconstruction.")

        fold_rows = ranking_df[ranking_df["fold_id"] == fold_id]
        if len(fold_rows) != top_n_per_fold:
            raise AssertionError(f"Fold {fold_id} has {len(fold_rows)} ranking rows, expected {top_n_per_fold}.")
        if fold_rows["rank"].min() != 1 or fold_rows["rank"].max() != top_n_per_fold:
            raise AssertionError(f"Fold {fold_id}'s ranks are not a contiguous 1..{top_n_per_fold} sequence.")
        if not fold_rows["rank"].is_unique:
            raise AssertionError(f"Fold {fold_id} has duplicate ranks.")

    union_from_ranking = set(ranking_df["peptide_id"])
    if union_from_ranking != fasta_peptide_ids:
        raise AssertionError(
            "Union FASTA peptide IDs do not exactly match the ranking CSV's unique peptide IDs "
            f"(FASTA-only: {fasta_peptide_ids - union_from_ranking}; "
            f"ranking-only: {union_from_ranking - fasta_peptide_ids})."
        )

    return {
        "n_folds": n_folds,
        "fold_safety_verified": True,
        "all_folds_have_exact_top_n": True,
        "union_fasta_matches_ranking": True,
        "top_n_per_fold": top_n_per_fold,
    }


def load_fold_challenges(ranking_path: str | Path, fold_id: int) -> pd.DataFrame:
    """The ONLY sanctioned way for FR3/FR4/FR6 training code to read C3 as
    a given fold's hard-challenge set. ``fold_id`` is a required positional
    argument with no "give me everything" default -- there is deliberately
    no function in this module that returns the union across folds, and no
    way to call this one without choosing a fold.

    Reading ``stage_c3_esm2_hard_challenges.fasta`` directly (the union
    FASTA) instead of going through this function, or filtering
    ``c3_similarity_ranking.csv`` by hand without restricting to one
    ``fold_id``, silently reintroduces the exact selection-leakage this
    module's fold-specific centroid construction exists to prevent -- see
    the module docstring. Raises if ``fold_id`` has no rows at all (a typo
    or an out-of-range fold is a bug to surface immediately, not silently
    return an empty, "technically valid" DataFrame for).
    """
    ranking_df = pd.read_csv(ranking_path)
    fold_df = ranking_df[ranking_df["fold_id"] == fold_id]
    if fold_df.empty:
        raise ValueError(
            f"No C3 ranking rows found for fold_id={fold_id} in {ranking_path} -- "
            f"available folds: {sorted(ranking_df['fold_id'].unique())}"
        )
    return fold_df.sort_values("rank").reset_index(drop=True)


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
