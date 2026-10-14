"""Bucket 4, Task 4.4 -- shared scikit-learn/pulearn PU-baseline plumbing.

Two-Step PU (``two_step_pu_baseline.py``) and PU-Bagging
(``pu_bagging_baseline.py``) both need the EXACT SAME fold-0 PU dataset
assembly nnPU (Task 4.3) uses -- E1+E2 labeled positives vs. C1 treated
as UNLABELED -- and both are trained with scikit-learn-compatible
estimators rather than ``models.BinaryMlp``. This module holds the one
shared dataset-assembly function and the one shared sklearn-model
checkpoint helper so neither new baseline module duplicates either, the
same "one implementation, not two" discipline Task 4.2/4.3 already
established for ``split_c1_train_validation``/``assert_no_cross_subset_overlap``.

**Scientific framing, never to be weakened (same invariant as PN/nnPU):**
C1 is this project's assumed-negative, PU-UNLABELED pool -- peptides with
no reported antioxidant activity, never experimentally confirmed
inactive. This module's own dataset dataclass (``SklearnPuDataset``) has
NO binary-label field for C1, exactly like ``NnPuDataset``. A combined
``(X, y)`` array with ``y`` in ``{1, 0}`` is unavoidable at the point
Two-Step PU/PU-Bagging actually call ``.fit()`` -- that is a scikit-
learn/pulearn API-level REQUIREMENT (their estimators have no notion of
a three-way positive/unlabeled/negative label), not a project-level claim
that C1 is confirmed negative. Both algorithms' own FIRST internal step
is to train a classifier that treats the unlabeled group AS IF it were
negative -- this is a standard, well-documented step of the Two-Step PU
and PU-Bagging algorithms themselves (Elkan & Noto 2008; Mordelet & Vert
2014), not a reinterpretation of C1's status by this project. See each
baseline module's own docstring for the algorithm-specific detail.

Why scikit-learn estimators here and not ``models.BinaryMlp``: see the
decision log entry in ``docs/IMPLEMENTATION_STATUS.md`` (Task 4.4). In
short, Two-Step PU and PU-Bagging are specific algorithms built around
scikit-learn-compatible base estimators in both the originating
literature and the only available PU-learning library wrapping them
(``pulearn``) -- wrapping ``BinaryMlp`` as a scikit-learn estimator
merely to force architectural uniformity with PN/nnPU would be a
disproportionate engineering detour for a baseline-implementation task,
and was explicitly rejected.

No torch import anywhere in this module -- dataset assembly needs only
numpy/pandas (identical discipline to ``pn_baseline.py``/
``nnpu_baseline.py``'s own torch-free dataset-construction halves).
``joblib`` (a transitive scikit-learn dependency, already present) is
used for sklearn-estimator checkpoint persistence -- NOT ``torch.save``,
since these estimators are not ``torch.nn.Module`` instances.
"""

from __future__ import annotations

import datetime as _dt
import os
import tempfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from plantaox.c2_pu.experiment_config import ExperimentConfig
from plantaox.c2_pu.experiment_data import ExperimentData, PoolData, assert_no_cross_subset_overlap
from plantaox.c2_pu.pn_baseline import InsufficientDataError, split_c1_train_validation

# Task 4.3's E1/E2 evidence-tier constant, duplicated here (NOT imported
# from nnpu_baseline.py) purely to avoid a transitive torch import: this
# module's top-level import graph is deliberately torch-free so
# Two-Step PU/PU-Bagging's own claim of being "entirely scikit-learn/
# pulearn-based, no torch anywhere" (see each baseline module's
# docstring) is actually true, not just asserted. ``nnpu_baseline.py``
# itself imports ``nnpu_risk.py`` at module level, which imports ``torch``
# (it needs torch tensors for the risk-estimator math) -- that import is
# unrelated to the tiny selection-masking logic below, but Python has no
# way to import just one name from a module without running that
# module's own top-level imports first. See the Task 4.4 decision log in
# docs/IMPLEMENTATION_STATUS.md for the full rationale, and
# ``test_pu_sklearn_common.py``'s equivalence test, which asserts this
# function and ``nnpu_baseline.select_e1_e2_positive_evidence`` produce
# IDENTICAL output on the same input, so the two can never silently
# diverge.
NNPU_POSITIVE_EVIDENCE_TIERS = ("E1", "E2")


def select_e1_e2_positive_evidence(pool: PoolData) -> PoolData:
    """Logically identical to ``nnpu_baseline.select_e1_e2_positive_evidence``
    (filters an already fold-partitioned positive pool down to E1+E2 only,
    never relabeling/reweighting, excluding any other tier such as a
    future E3 row) -- deliberately duplicated rather than imported; see
    the module-level comment above for why.
    """
    if pool.evidence_tier is None:
        raise ValueError(f"{pool.pool}: no evidence_tier info available to filter by {NNPU_POSITIVE_EVIDENCE_TIERS}")
    mask = np.isin(pool.evidence_tier, NNPU_POSITIVE_EVIDENCE_TIERS)
    return PoolData(
        pool=f"{pool.pool}_E1E2",
        peptide_ids=pool.peptide_ids[mask],
        sequences=pool.sequences[mask],
        features=pool.features[mask],
        evidence_tier=pool.evidence_tier[mask],
    )


CHECKPOINT_BEST_FILENAME = "checkpoint_best.joblib"
CHECKPOINT_LAST_FILENAME = "checkpoint_last.joblib"

PU_SKLEARN_LABEL_ENCODING_NOTE = (
    "y=1 encodes an E1/E2 labeled positive; y=0 encodes a C1 row passed to the "
    "scikit-learn/pulearn estimator's unlabeled-surrogate slot. This 0 is a "
    "library-API numeric requirement (pulearn's PU estimators accept exactly "
    "one 'unlabeled' numeric code and have no three-way positive/unlabeled/"
    "negative label type), not a project-level claim that C1 is a confirmed "
    "negative -- see AGENTS.md rule #1 and this module's own docstring."
)


@dataclass(frozen=True)
class SklearnPuDataset:
    """Exactly what Two-Step PU / PU-Bagging training needs -- C2, C3, and
    the external control are structurally absent (same discipline as
    ``PnDataset``/``NnPuDataset``), so they cannot leak into either new
    baseline even by accident. No binary label field for C1 anywhere in
    this dataclass; combining into a ``(X, y)`` array happens only inside
    each baseline's own ``train_*`` function, immediately before the
    ``.fit()`` call that structurally requires it.
    """

    train_positive_features: np.ndarray  # (n_p_train, feature_dim) float32, E1+E2
    train_positive_ids: np.ndarray
    train_positive_tiers: np.ndarray  # "E1"/"E2" per row
    validation_positive_features: np.ndarray
    validation_positive_ids: np.ndarray
    validation_positive_tiers: np.ndarray
    train_unlabeled_features: np.ndarray  # (n_u_train, feature_dim) float32, C1 train
    train_unlabeled_ids: np.ndarray
    validation_unlabeled_features: np.ndarray
    validation_unlabeled_ids: np.ndarray
    e1_train_count: int
    e2_train_count: int
    e1_validation_count: int
    e2_validation_count: int
    c1_validation_fraction: float
    c1_partition_seed: int


def build_sklearn_pu_dataset(data: ExperimentData, config: ExperimentConfig) -> SklearnPuDataset:
    """Assembles the Two-Step PU / PU-Bagging train/validation arrays from
    an already-built ``ExperimentData`` (Task 4.1), for ``config.fold_id``.

    Identical partition policy to nnPU (Task 4.3): positive group is E1+E2
    (this module's own ``select_e1_e2_positive_evidence`` -- behaviorally
    identical to, but not imported from, ``nnpu_baseline.py``'s function of
    the same name; see that function's own docstring for why), drawn from
    ``data.train_positive``/``data.validation_positive`` (GraphPart's own
    fold-aware partition, untouched); unlabeled group is C1, partitioned
    via ``pn_baseline.split_c1_train_validation`` -- the SAME deterministic
    C1 split PN and nnPU both use (same ``config.validation_fraction``/
    ``config.eval_seed``, genuinely imported and reused, not duplicated).
    This is the one and only PU-dataset-assembly implementation shared by
    Two-Step PU and PU-Bagging; neither baseline
    module reimplements this.

    Independently re-verifies (does not just trust Task 4.1's own
    ``data.leakage_report``) that none of the four subsets overlap with
    each other, with GraphPart's held-out fold, or with C2/C3/the external
    control -- by peptide_id AND by sequence, exactly as PN/nnPU do.
    """
    positive_train = select_e1_e2_positive_evidence(data.train_positive)
    positive_validation = select_e1_e2_positive_evidence(data.validation_positive)

    if len(positive_train.peptide_ids) == 0:
        raise InsufficientDataError(f"Fold {config.fold_id}: zero E1/E2 training positives.")
    if len(positive_validation.peptide_ids) == 0:
        raise InsufficientDataError(f"Fold {config.fold_id}: zero E1/E2 validation positives.")
    if len(data.c1.peptide_ids) == 0:
        raise InsufficientDataError(f"Fold {config.fold_id}: zero C1 rows -- nothing to partition as unlabeled data.")

    c1_train, c1_validation = split_c1_train_validation(data.c1, config.validation_fraction, config.eval_seed)

    if len(c1_train.peptide_ids) == 0 or len(c1_validation.peptide_ids) == 0:
        raise InsufficientDataError(f"Fold {config.fold_id}: zero C1 train or validation rows.")

    assert_no_cross_subset_overlap(
        {
            "e1e2_positive_train": positive_train,
            "e1e2_positive_validation": positive_validation,
            "c1_unlabeled_train": c1_train,
            "c1_unlabeled_validation": c1_validation,
            "held_out_positive": data.held_out_positive,
            "c2": data.c2,
            "c3_fold_challenges": data.c3_fold_challenges,
            "external_control": data.external_control,
        }
    )

    for name, pool in (
        ("train_positive", positive_train),
        ("validation_positive", positive_validation),
        ("c1_train", c1_train),
        ("c1_validation", c1_validation),
    ):
        if not np.isfinite(pool.features).all():
            raise ValueError(f"Non-finite value(s) in {name} features -- refusing to build a dataset.")

    train_tier_counts = Counter(positive_train.evidence_tier.tolist())
    validation_tier_counts = Counter(positive_validation.evidence_tier.tolist())

    return SklearnPuDataset(
        train_positive_features=positive_train.features,
        train_positive_ids=positive_train.peptide_ids,
        train_positive_tiers=positive_train.evidence_tier,
        validation_positive_features=positive_validation.features,
        validation_positive_ids=positive_validation.peptide_ids,
        validation_positive_tiers=positive_validation.evidence_tier,
        train_unlabeled_features=c1_train.features,
        train_unlabeled_ids=c1_train.peptide_ids,
        validation_unlabeled_features=c1_validation.features,
        validation_unlabeled_ids=c1_validation.peptide_ids,
        e1_train_count=int(train_tier_counts.get("E1", 0)),
        e2_train_count=int(train_tier_counts.get("E2", 0)),
        e1_validation_count=int(validation_tier_counts.get("E1", 0)),
        e2_validation_count=int(validation_tier_counts.get("E2", 0)),
        c1_validation_fraction=config.validation_fraction,
        c1_partition_seed=config.eval_seed,
    )


def score_distribution_summary(scores: np.ndarray) -> dict:
    """Descriptive (NOT MCC/AUPRC -- those are Task 4.5's scope)
    score-distribution summary shared by both Two-Step PU and
    PU-Bagging's validation/OOB diagnostics, mirroring nnPU's own
    prediction-saturation diagnostic style (fraction near 0 / near 1)."""
    return {
        "n": int(len(scores)),
        "mean": float(np.mean(scores)) if len(scores) else None,
        "median": float(np.median(scores)) if len(scores) else None,
        "min": float(np.min(scores)) if len(scores) else None,
        "max": float(np.max(scores)) if len(scores) else None,
        "fraction_near_zero_lt_0p01": float(np.mean(scores < 0.01)) if len(scores) else None,
        "fraction_near_one_gt_0p99": float(np.mean(scores > 0.99)) if len(scores) else None,
    }


def combined_fit_arrays(dataset: SklearnPuDataset, split: str = "train") -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Builds the ``(X, y, peptide_ids)`` arrays scikit-learn/pulearn's
    ``.fit(X, y)`` structurally requires -- ``y=1`` for E1/E2 positives,
    ``y=0`` for C1 (the library's required unlabeled-surrogate numeric
    code; see ``PU_SKLEARN_LABEL_ENCODING_NOTE``). ``split`` selects
    train or validation; positives are always listed before unlabeled
    rows so index-based bookkeeping (e.g. hold-out diagnostics) stays
    simple and consistent across both new baseline modules.
    """
    if split == "train":
        pos_x, pos_ids = dataset.train_positive_features, dataset.train_positive_ids
        unl_x, unl_ids = dataset.train_unlabeled_features, dataset.train_unlabeled_ids
    elif split == "validation":
        pos_x, pos_ids = dataset.validation_positive_features, dataset.validation_positive_ids
        unl_x, unl_ids = dataset.validation_unlabeled_features, dataset.validation_unlabeled_ids
    else:
        raise ValueError(f"split must be 'train' or 'validation', got {split!r}")

    x = np.concatenate([pos_x, unl_x], axis=0)
    y = np.concatenate([np.ones(len(pos_ids), dtype=np.int64), np.zeros(len(unl_ids), dtype=np.int64)])
    ids = np.concatenate([pos_ids, unl_ids])
    return x, y, ids


def save_sklearn_checkpoint(run_dir: Path, estimator, metrics: dict, is_best: bool, extra: dict | None = None) -> Path:
    """Atomic ``joblib``-based checkpoint save for a fitted scikit-learn /
    pulearn estimator -- mirrors ``run_recorder.save_checkpoint``'s
    atomicity (temp file + ``os.replace()``, cleaned up on any exception)
    and best/last filename convention (``checkpoint_best.joblib``/
    ``checkpoint_last.joblib``), but uses ``joblib.dump`` rather than
    ``torch.save`` since these estimators are not ``torch.nn.Module``
    instances.

    **A genuine, documented difference from PN/nnPU's checkpointing**:
    Two-Step PU's ``.fit()`` and PU-Bagging's ``.fit()`` are each a single,
    non-iterative training call (see each baseline module's own docstring)
    -- there is no per-epoch "best so far" to track. Both baselines
    therefore call this function with ``is_best=True`` exactly once (the
    one and only fit), and separately write an identical copy as
    ``checkpoint_last.joblib`` so any future script that looks for either
    filename (matching PN/nnPU's convention) finds a valid, identical
    checkpoint either way -- not two different models.
    """
    import joblib

    run_dir = Path(run_dir)
    payload = {
        "estimator": estimator,
        "metrics": metrics,
        "sklearn_version": __import__("sklearn").__version__,
        "pulearn_version": __import__("pulearn").__version__,
        "saved_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
        "extra": extra or {},
    }
    filename = CHECKPOINT_BEST_FILENAME if is_best else CHECKPOINT_LAST_FILENAME
    final_path = run_dir / filename
    fd, tmp_path = tempfile.mkstemp(dir=run_dir, suffix=".tmp")
    os.close(fd)
    try:
        joblib.dump(payload, tmp_path)
        os.replace(tmp_path, final_path)
    except BaseException:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
        raise
    return final_path


def load_sklearn_checkpoint(path: Path):
    """Loads a ``save_sklearn_checkpoint`` payload back -- raises
    ``FileNotFoundError`` if the path doesn't exist (matching
    ``run_recorder.load_checkpoint``'s behavior). Returns the full payload
    dict (``estimator`` is ready to call ``.predict_proba()`` on directly).
    """
    import joblib

    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Checkpoint not found: {path}")
    return joblib.load(path)
