"""Bucket 4.1 -- fold-aware data interface (Task 4.1 §C).

Thin orchestration over the ALREADY-ACCEPTED ``common/feature_cache.py``
loader -- this module does not reimplement cache loading, scaling, or
C3 fold-membership resolution. It adds exactly what Task 4.1 asks for on
top: column-slicing by feature representation, a training-side-only
validation split, evidence-tier attachment, and defense-in-depth
identity/sequence-overlap checks across every returned subset.

**Framing discipline:** C1, C2, and the C3 fold-challenge selection are
returned as plain, unlabeled feature pools -- never assigned a binary
"negative" label or merged into one combined array here. Whether/how a
given baseline (PN, nnPU, ...) treats them as negatives is a Task 4.2+
training-objective decision, strictly outside this module's job.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

from plantaox.c2_pu.common.feature_cache import (
    get_c3_fold_challenge_rows,
    get_held_out_rows,
    get_pool_rows,
    get_training_rows,
    load_fold_feature_cache,
)
from plantaox.c2_pu.experiment_config import FEATURE_DIMENSIONS, ExperimentConfig

ESM_SLICE = slice(0, 480)
DESCRIPTOR_SLICE = slice(480, 495)


class DataLeakageError(ValueError):
    """Raised when any two subsets this module returns share a peptide_id
    or an identical sequence -- never silently tolerated."""


class WrongFoldError(ValueError):
    """Raised when a requested fold_id doesn't match the loaded cache's
    own fold_id -- a wrong cache/selection combination."""


@dataclass(frozen=True)
class PoolData:
    pool: str
    peptide_ids: np.ndarray
    sequences: np.ndarray
    features: np.ndarray  # (n, feature_dim), float32, finite
    evidence_tier: np.ndarray | None = None

    def __post_init__(self):
        n = len(self.peptide_ids)
        if len(self.sequences) != n or len(self.features) != n:
            raise ValueError(f"{self.pool}: peptide_ids/sequences/features length mismatch")
        if len(set(self.peptide_ids.tolist())) != n:
            raise DataLeakageError(f"{self.pool}: duplicate peptide_id(s) within this subset")
        if self.features.dtype != np.float32:
            raise ValueError(f"{self.pool}: features dtype must be float32, got {self.features.dtype}")
        if not np.isfinite(self.features).all():
            raise ValueError(f"{self.pool}: non-finite value(s) in features")


@dataclass(frozen=True)
class ExperimentData:
    fold_id: int
    feature_representation: str
    feature_dim: int
    train_positive: PoolData
    validation_positive: PoolData
    held_out_positive: PoolData
    c1: PoolData
    c2: PoolData
    c3_fold_challenges: PoolData
    external_control: PoolData
    leakage_report: dict


def _slice_features(features: np.ndarray, representation: str) -> np.ndarray:
    """``features`` is always the full fused (495-dim) matrix -- "esm" and
    "descriptors" are post-hoc column slices of that SAME scaled matrix,
    never an alternate storage format or an independently-refit scaling.
    Validates the input is actually 495-wide before slicing, rather than
    silently returning whatever columns happen to exist for a malformed
    (e.g. already-sliced, or wrong-schema) input array.
    """
    expected_width = FEATURE_DIMENSIONS["fused"]
    if features.shape[1] != expected_width:
        raise ValueError(
            f"Expected the full {expected_width}-dim fused matrix before slicing by "
            f"feature_representation, got {features.shape[1]} columns."
        )
    if representation == "fused":
        return features
    if representation == "esm":
        return features[:, ESM_SLICE]
    if representation == "descriptors":
        return features[:, DESCRIPTOR_SLICE]
    raise ValueError(f"Unknown feature_representation {representation!r}")


def _evidence_tier_lookup(record_map_df: pd.DataFrame) -> dict[str, str]:
    fr1 = record_map_df[record_map_df["pool"] == "FR1_positives"]
    return dict(zip(fr1["peptide_id"], fr1["evidence_tier"]))


def _split_training_validation(
    training_peptide_ids: list[str], validation_fraction: float, seed: int
) -> tuple[list[str], list[str]]:
    """Deterministic shuffle-and-split of the TRAINING-side positive IDs
    only -- GraphPart's held-out fold is never touched here, and this
    uses its own local ``random.Random`` instance so it doesn't consume
    from (or get perturbed by) any global seed state.
    """
    ids = sorted(training_peptide_ids)
    rng = random.Random(seed)
    rng.shuffle(ids)
    n_val = max(1, round(len(ids) * validation_fraction))
    if n_val >= len(ids):
        raise ValueError(
            f"validation_fraction={validation_fraction} leaves zero training rows "
            f"({len(ids)} training IDs, {n_val} requested for validation)."
        )
    return ids[n_val:], ids[:n_val]


def _assert_no_cross_subset_overlap(subsets: dict[str, PoolData]) -> dict:
    """Pairwise peptide_id AND sequence overlap check across every
    returned subset -- raises DataLeakageError with full detail on the
    first violation found, and otherwise returns a small report
    confirming the checks ran and what they covered.
    """
    names = list(subsets.keys())
    checked_pairs = []
    for i, name_a in enumerate(names):
        for name_b in names[i + 1 :]:
            ids_a = set(subsets[name_a].peptide_ids.tolist())
            ids_b = set(subsets[name_b].peptide_ids.tolist())
            id_overlap = ids_a & ids_b
            if id_overlap:
                raise DataLeakageError(f"peptide_id overlap between {name_a!r} and {name_b!r}: {sorted(id_overlap)[:10]}")

            seqs_a = set(subsets[name_a].sequences.tolist())
            seqs_b = set(subsets[name_b].sequences.tolist())
            seq_overlap = seqs_a & seqs_b
            if seq_overlap:
                raise DataLeakageError(
                    f"repeated-sequence leakage between {name_a!r} and {name_b!r} "
                    f"(same sequence under different peptide_ids): {sorted(seq_overlap)[:5]}"
                )
            checked_pairs.append(f"{name_a}<->{name_b}")
    return {"pairs_checked": checked_pairs, "overlap_found": False}


def build_experiment_data(
    config: ExperimentConfig,
    cache_path: Path,
    cache_manifest_entry: dict,
    fusion_scaler_entry: dict,
    record_map_df: pd.DataFrame,
    c3_ranking_path: Path,
) -> ExperimentData:
    """Build every subset a Task-4.2+ training script needs for
    ``config.fold_id``, from the already-accepted fold-specific scaled
    cache -- no scaler refitting, no embedding/descriptor recomputation,
    no frozen-dataset regeneration anywhere in this function.
    """
    cache = load_fold_feature_cache(cache_path, cache_manifest_entry)
    if cache["fold_id"] != config.fold_id:
        raise WrongFoldError(
            f"Requested fold_id={config.fold_id} but the loaded cache's own fold_id is "
            f"{cache['fold_id']} -- refusing this wrong cache/selection combination."
        )

    sequence_lookup = dict(zip(record_map_df["peptide_id"], record_map_df["sequence"]))
    evidence_lookup = _evidence_tier_lookup(record_map_df)

    def _pool_data(pool_name: str, peptide_ids: list[str], features: np.ndarray, with_evidence: bool = False) -> PoolData:
        peptide_ids_arr = np.asarray(peptide_ids)
        sequences = np.asarray([sequence_lookup[pid] for pid in peptide_ids])
        sliced = _slice_features(features.astype(np.float32), config.feature_representation)
        evidence_tier = (
            np.asarray([evidence_lookup[pid] for pid in peptide_ids]) if with_evidence else None
        )
        return PoolData(pool=pool_name, peptide_ids=peptide_ids_arr, sequences=sequences, features=sliced, evidence_tier=evidence_tier)

    training_ids = fusion_scaler_entry["training_peptide_ids"]
    held_out_ids = fusion_scaler_entry["held_out_peptide_ids"]
    train_only_ids, validation_ids = _split_training_validation(training_ids, config.validation_fraction, config.eval_seed)

    _, train_rows = get_training_rows(cache, train_only_ids)
    _, val_rows = get_training_rows(cache, validation_ids)  # same pool, just a different ID subset
    _, held_out_rows = get_held_out_rows(cache, held_out_ids)

    train_positive = _pool_data("FR1_positives_train", train_only_ids, train_rows, with_evidence=True)
    validation_positive = _pool_data("FR1_positives_validation", validation_ids, val_rows, with_evidence=True)
    held_out_positive = _pool_data("FR1_positives_held_out", held_out_ids, held_out_rows, with_evidence=True)

    c1_ids, c1_rows = get_pool_rows(cache, "C1")
    c2_ids, c2_rows = get_pool_rows(cache, "C2")
    c1 = _pool_data("C1", c1_ids.tolist(), c1_rows)
    c2 = _pool_data("C2", c2_ids.tolist(), c2_rows)

    c3_ids, c3_rows, _c3_df = get_c3_fold_challenge_rows(cache, c3_ranking_path, config.fold_id)
    c3_fold_challenges = _pool_data(f"C3_fold{config.fold_id}", c3_ids.tolist(), c3_rows)

    ext_ids, ext_rows = get_pool_rows(cache, "external_control")
    external_control = _pool_data("external_control", ext_ids.tolist(), ext_rows)

    subsets = {
        "train_positive": train_positive,
        "validation_positive": validation_positive,
        "held_out_positive": held_out_positive,
        "c1": c1,
        "c2": c2,
        "c3_fold_challenges": c3_fold_challenges,
        "external_control": external_control,
    }
    leakage_report = _assert_no_cross_subset_overlap(subsets)

    return ExperimentData(
        fold_id=config.fold_id,
        feature_representation=config.feature_representation,
        feature_dim=config.feature_dim,
        train_positive=train_positive,
        validation_positive=validation_positive,
        held_out_positive=held_out_positive,
        c1=c1,
        c2=c2,
        c3_fold_challenges=c3_fold_challenges,
        external_control=external_control,
        leakage_report=leakage_report,
    )
