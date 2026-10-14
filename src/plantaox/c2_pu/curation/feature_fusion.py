"""Bucket 3.3 -- feature fusion and leakage-safe preprocessing.

Fuses Task 3.1's 15-descriptor table (``fr3_descriptor_table.parquet``)
with Task 3.2's 480-dim ESM-2 embedding cache (``fr3_embeddings.npz``)
into a single 495-dim raw feature matrix, schema ``fusion_v1``, column
order **[esm2_0..esm2_479, then the 15 descriptor_v1 names in their
frozen order]** -- matching the proposal's own "ESM-2 + 15-descriptor"
phrasing and never reordered without a new schema version.

Neither Task 3.1 nor Task 3.2 is recomputed here -- this module only
loads, validates, concatenates, and (for preprocessing) fits/applies
per-fold scalers. No cross-dataset statistic is ever fit on anything
other than one GraphPart fold's own training-positive rows.

**Leakage-safe scaling design (the one load-bearing methodological
decision in this task):** FR1 positives are the only pool with a fold
assignment (GraphPart, 834 retained / 371 excluded-for-homology). C1, C2,
the C3 union, and the external control have no fold membership of their
own -- they are PU-unlabeled or held out entirely, never "training
positives" for any fold. Mirroring the exact precedent already approved
and shipped in this project for the C3 fold-safe centroid
(``curation/c3.py``, AGENTS.md rule 5: "fit on the training partition
only and applied, not refit, elsewhere"), the per-fold scaler for fold k
is fit **exclusively on that fold's training-positive rows** (the 4 other
GraphPart folds' retained positives -- 710/700/697/661/568 sequences for
folds 0-4), then applied (transform only) to everything else under that
fold's experimental condition: fold k's own held-out positives, C1, C2,
fold k's C3 hard-challenge selection, and the external control. The same
physical C1/C2/C3 sequence is therefore transformed differently under
each fold's condition -- by design, not a bug: this is what "no feature-
space information leaks from a held-out positive or an unlabeled
candidate into the scaler" requires. GraphPart's 371 excluded-for-
homology positives are never included in any fold's training or held-out
set, consistent with Bucket 1.6/1.7.

An alternative (fit one global scaler on all 1,205 FR1 positives) was
considered and rejected: it would let fold k's own held-out positives
influence the statistics later used to transform those same held-out
positives at evaluation time -- a subtle but real leakage channel,
exactly analogous to the one the C3 centroid's fold-safe design already
exists to close.
"""

from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd

from plantaox.c2_pu.common.descriptors import DESCRIPTOR_NAMES

SCHEMA_VERSION = "fusion_v1"
ESM2_DIM = 480
N_DESCRIPTORS = len(DESCRIPTOR_NAMES)
FUSED_DIM = ESM2_DIM + N_DESCRIPTORS
ESM2_FEATURE_NAMES = tuple(f"esm2_{i}" for i in range(ESM2_DIM))
FUSED_FEATURE_NAMES = ESM2_FEATURE_NAMES + DESCRIPTOR_NAMES
assert len(FUSED_FEATURE_NAMES) == FUSED_DIM == 495


class FeatureAlignmentError(ValueError):
    """Raised when the descriptor table and embedding cache don't agree on
    peptide IDs, pool assignments, or row order -- never silently
    reconciled by sorting/reindexing."""


def load_and_validate_fusion_inputs(
    descriptor_df: pd.DataFrame, embedding_peptide_ids: np.ndarray, embedding_pools: np.ndarray
) -> None:
    """Hard-fail validation of one-to-one correspondence between the
    descriptor table and the embedding cache: identical peptide_id values
    in identical row order, identical pool assignments, and no duplicate
    peptide_id anywhere. Raises FeatureAlignmentError with specifics on
    any mismatch -- never reorders, reindexes, or drops rows to "fix" one.
    """
    descriptor_ids = descriptor_df["peptide_id"].tolist()
    embedding_ids = [str(x) for x in embedding_peptide_ids]

    if len(set(descriptor_ids)) != len(descriptor_ids):
        dupes = descriptor_df[descriptor_df.duplicated("peptide_id", keep=False)]["peptide_id"].tolist()
        raise FeatureAlignmentError(f"Descriptor table has duplicate peptide_id rows: {dupes[:10]}")

    if len(descriptor_ids) != len(embedding_ids):
        raise FeatureAlignmentError(
            f"Row count mismatch: descriptor table has {len(descriptor_ids)} rows, "
            f"embedding cache has {len(embedding_ids)} rows."
        )
    if descriptor_ids != embedding_ids:
        missing_from_embeddings = set(descriptor_ids) - set(embedding_ids)
        missing_from_descriptors = set(embedding_ids) - set(descriptor_ids)
        if missing_from_embeddings or missing_from_descriptors:
            raise FeatureAlignmentError(
                f"peptide_id sets differ -- in descriptor table only: "
                f"{list(missing_from_embeddings)[:10]}; in embedding cache only: "
                f"{list(missing_from_descriptors)[:10]}"
            )
        raise FeatureAlignmentError(
            "peptide_id sets match but ROW ORDER differs between the descriptor table "
            "and the embedding cache -- refusing to silently reorder one to match the "
            "other, since that would mask a real pipeline bug."
        )

    descriptor_pools = descriptor_df["pool"].tolist()
    embedding_pool_list = [str(x) for x in embedding_pools]
    if descriptor_pools != embedding_pool_list:
        mismatches = [
            (pid, dp, ep)
            for pid, dp, ep in zip(descriptor_ids, descriptor_pools, embedding_pool_list)
            if dp != ep
        ]
        raise FeatureAlignmentError(
            f"{len(mismatches)} peptide_id(s) have inconsistent pool assignment between "
            f"the descriptor table and the embedding cache: {mismatches[:10]}"
        )


def build_raw_fused_matrix(descriptor_df: pd.DataFrame, embedding_matrix: np.ndarray) -> np.ndarray:
    """Concatenate [esm2 (480), descriptors (15)] -> (n, 495) float32, in
    the exact row order of ``descriptor_df``. Caller must have already run
    ``load_and_validate_fusion_inputs``."""
    descriptor_block = descriptor_df[list(DESCRIPTOR_NAMES)].to_numpy(dtype=np.float32)
    return np.concatenate([embedding_matrix.astype(np.float32), descriptor_block], axis=1)


def fit_scaler(training_rows: np.ndarray) -> dict[str, np.ndarray]:
    """Per-column z-score scaler fit on ``training_rows`` only (n_train, 495).
    Zero-variance columns get std=1.0 (matches scikit-learn's own
    StandardScaler convention) so transform never divides by zero or
    produces NaN/Inf for a column that happens to be constant within one
    fold's small training partition.
    """
    mean = training_rows.mean(axis=0)
    std = training_rows.std(axis=0, ddof=0)
    std_safe = np.where(std < 1e-12, 1.0, std)
    return {"mean": mean.astype(np.float64), "std": std_safe.astype(np.float64)}


def apply_scaler(rows: np.ndarray, scaler: dict[str, np.ndarray]) -> np.ndarray:
    """Transform only -- never refits. Safe to call on training, held-out,
    or any unlabeled-pool rows under a given fold's scaler."""
    return (rows.astype(np.float64) - scaler["mean"]) / scaler["std"]


def compute_fold_training_peptide_ids(
    record_map_df: pd.DataFrame, fold_id: int
) -> tuple[list[str], list[str]]:
    """Returns (training_peptide_ids, held_out_peptide_ids) for FR1
    positives under GraphPart fold ``fold_id``: training = the 4 OTHER
    retained folds; held-out = this fold's own retained positives.
    Positives GraphPart excluded for cross-fold homology (graphpart_
    retained=False) are in neither list, for either fold.
    """
    fr1 = record_map_df[record_map_df["pool"] == "FR1_positives"]
    retained = fr1[fr1["graphpart_retained"] == True]  # noqa: E712 (pandas bool column)
    training = retained[retained["graphpart_fold"] != fold_id]["peptide_id"].tolist()
    held_out = retained[retained["graphpart_fold"] == fold_id]["peptide_id"].tolist()
    return training, held_out


def compute_all_fold_scalers(
    peptide_ids: list[str],
    fused_matrix: np.ndarray,
    record_map_df: pd.DataFrame,
    n_folds: int = 5,
) -> dict[int, dict]:
    """One leakage-safe scaler per GraphPart fold, each fit exclusively on
    that fold's training-positive rows (see module docstring). Returns
    {fold_id: {"mean": ..., "std": ..., "training_peptide_ids": [...],
    "n_training_samples": int, "held_out_peptide_ids": [...]}}.
    """
    id_to_row = {pid: i for i, pid in enumerate(peptide_ids)}
    fold_scalers: dict[int, dict] = {}
    for fold_id in range(n_folds):
        training_ids, held_out_ids = compute_fold_training_peptide_ids(record_map_df, fold_id)
        if not training_ids:
            raise ValueError(f"Fold {fold_id} has zero training-positive peptide_ids -- refusing to fit an empty scaler.")
        training_rows = fused_matrix[[id_to_row[pid] for pid in training_ids]]
        scaler = fit_scaler(training_rows)
        fold_scalers[fold_id] = {
            **scaler,
            "training_peptide_ids": sorted(training_ids),
            "held_out_peptide_ids": sorted(held_out_ids),
            "n_training_samples": len(training_ids),
        }
    return fold_scalers


def peptide_id_order_sha256(peptide_ids: list[str]) -> str:
    return hashlib.sha256("\n".join(peptide_ids).encode("utf-8")).hexdigest()
