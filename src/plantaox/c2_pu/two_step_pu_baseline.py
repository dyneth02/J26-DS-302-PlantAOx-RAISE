"""Bucket 4, Task 4.4 -- Two-Step PU (Elkan & Noto 2008-style) baseline.

Builds on ``pu_sklearn_common.build_sklearn_pu_dataset`` (Task 4.4's
shared dataset assembly, itself reusing Task 4.2/4.3's deterministic C1
partition and E1+E2 positive selection unchanged) rather than a second
PU-dataset builder. CLI stage: ``python -m plantaox.c2_pu.run
fr4-two-step-pu-baseline``.

**What "Two-Step PU" means here, stated explicitly (per the task brief's
own instruction not to silently conflate PU-learning variants):** this
implements the single-classifier probability-correction method of Elkan
& Noto, "Learning classifiers from only positive and unlabeled data"
(KDD 2008), via ``pulearn.ElkanotoPuClassifier``. The "two steps" are:

1. Train an ordinary probabilistic classifier ``g(x)`` to distinguish
   labeled positives (``s=1``) from everything else (``s=0``) -- C1 rows
   are passed into this internal step AS IF they were negative. This is
   a standard, well-documented step of the Elkan & Noto algorithm itself
   (their own paper calls the labeled/unlabeled indicator ``s``, distinct
   from the true unobserved label ``y``) -- it is not this project
   reclassifying C1 as confirmed-negative; C1's true composition (some
   unknown mixture of true positives and true negatives) is exactly what
   the correction in step 2 exists to compensate for.
2. Estimate ``c = P(s=1 | y=1)`` (the probability a true positive ends up
   labeled) from a held-out slice of the labeled positives, then correct
   ``g(x)`` into an estimate of ``f(x) = P(y=1 | x) = g(x) / c``.

**A real, load-bearing numerical property, documented rather than hidden
or silently clipped away:** because ``c <= 1``, the corrected estimate
``g(x)/c`` CAN EXCEED 1 -- this is explicit in pulearn's own
``ElkanotoPuClassifier.predict_proba`` docstring and is a known property
of the Elkan & Noto estimator, not a bug in this implementation. Every
summary this module produces reports BOTH the raw corrected value
(unclipped, the quantity the algorithm actually defines) and a
clipped-to-``[0, 1]`` version (for any downstream code that structurally
requires a bounded probability), labeled as such.

**How this differs from PN (Task 4.2) and nnPU (Task 4.3), recorded
explicitly so later comparisons do not attribute every observed
difference to the wrong cause:**

1. **Base estimator family.** PN/nnPU share one PyTorch ``BinaryMlp``
   (495 -> 128 ReLU -> 64 ReLU -> 1 logit) trained by backprop. Two-Step
   PU wraps a plain ``sklearn.linear_model.LogisticRegression`` --a
   different model family entirely, chosen because the Two-Step PU
   literature and the ``pulearn`` library (the only practical
   implementation available, see the decision log) are both built around
   scikit-learn-compatible estimators, not because of an architectural
   preference. See the module-level ``BASE_ESTIMATOR_DECISION_NOTE``.
2. **Training procedure.** PN/nnPU are iterative mini-batch gradient
   descent over many epochs, with a per-epoch validation loss/risk curve
   and early stopping. Two-Step PU's ``.fit()`` is a SINGLE, non-iterative
   call: one hold-out split, one classifier fit, one scalar correction
   constant ``c``. There is no epoch-wise optimization trajectory, so no
   learning-curve SVG is produced here (documented, not a missing
   feature) and no early stopping applies.
3. **No explicit prior.** nnPU requires a positive-class prior ``pi``
   that must be chosen or estimated (Task 4.3's own documented
   provisional ``pi=0.10``). Two-Step PU has no such global prior
   hyperparameter -- its analogous quantity is ``c``, but ``c`` is
   ESTIMATED directly from a held-out slice of the labeled positives
   (not assumed/provided), and is a different quantity (a labeling-
   propensity correction, not a mixture-prevalence prior).
4. **Risk/loss framework.** PN uses BCE-with-logits; nnPU uses the
   non-negative PU risk estimator. Two-Step PU uses neither -- its first
   stage is an ordinary scikit-learn classifier's own loss (logistic
   loss for ``LogisticRegression``), and the PU-specific correction is a
   closed-form post-hoc scalar division, not a custom risk estimator
   ``compute_nnpu_risk`` style function at all.

Deliberately NO torch import anywhere in this module's dataset/training
code -- Two-Step PU is an entirely scikit-learn/pulearn-based baseline.
``joblib``-based checkpointing (``pu_sklearn_common``) is used instead of
``run_recorder.save_checkpoint``, since ``ElkanotoPuClassifier`` is not a
``torch.nn.Module``.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from plantaox.c2_pu.pu_sklearn_common import (
    PU_SKLEARN_LABEL_ENCODING_NOTE,
    SklearnPuDataset,
    combined_fit_arrays,
    load_sklearn_checkpoint,
    save_sklearn_checkpoint,
    score_distribution_summary,
)

DEFAULT_HOLD_OUT_RATIO = 0.1  # pulearn's own published default -- not retuned for this project.

BASE_ESTIMATOR_DECISION_NOTE = (
    "Base estimator: sklearn.linear_model.LogisticRegression(max_iter=2000, "
    "random_state=<config.train_seed>), default L2 penalty, C=1.0 (sklearn's own "
    "default). No pre-specified base-classifier/architecture for Two-Step PU or "
    "PU-Bagging was found in docs/PU_AOP_RESEARCH_CONTEXT.md, the Planner doc, or "
    "the proposal (inspected directly before writing this module, not assumed). "
    "Logistic regression was chosen over a tree ensemble (e.g. RandomForestClassifier) "
    "because it is the more common choice in the original Two-Step PU (Elkan & Noto "
    "2008) and PU-Bagging (Mordelet & Vert 2014) literature, is simpler to reason "
    "about and faster to fit/reproduce exactly, and keeps both new baselines on the "
    "SAME base-estimator family for a cleaner later comparison between them. Wrapping "
    "the existing torch BinaryMlp as a scikit-learn estimator merely to force "
    "architectural uniformity with PN/nnPU was explicitly considered and rejected as "
    "a disproportionate engineering detour for a baseline-implementation task -- see "
    "docs/IMPLEMENTATION_STATUS.md's Task 4.4 decision log entry."
)


@dataclass(frozen=True)
class TwoStepPuResult:
    estimator: object
    c: float
    hold_out_ratio: int | float
    train_metrics: dict
    validation_metrics: dict
    elapsed_seconds: float


def train_two_step_pu_baseline(
    config,
    dataset: SklearnPuDataset,
    run_dir: Path,
    hold_out_ratio: float = DEFAULT_HOLD_OUT_RATIO,
) -> dict:
    """Fits ``pulearn.ElkanotoPuClassifier`` once (a non-iterative
    procedure -- see the module docstring) on the Task 4.4 shared PU
    dataset, computes validation-side diagnostics, and checkpoints the
    fitted estimator via ``joblib``.
    """
    import sklearn
    from pulearn import ElkanotoPuClassifier
    from sklearn.linear_model import LogisticRegression

    from plantaox.c2_pu.run_recorder import append_epoch_metrics

    start_time = time.time()

    train_x, train_y, _train_ids = combined_fit_arrays(dataset, "train")
    if not np.isfinite(train_x).all():
        raise RuntimeError("Non-finite value(s) in Two-Step PU training features -- refusing to train.")

    base_estimator = LogisticRegression(max_iter=2000, random_state=config.train_seed)
    clf = ElkanotoPuClassifier(estimator=base_estimator, hold_out_ratio=hold_out_ratio, random_state=config.train_seed)
    clf.fit(train_x, train_y)

    if not np.isfinite(clf.c) or clf.c <= 0:
        raise RuntimeError(f"Two-Step PU produced a non-finite or non-positive c estimate: {clf.c!r}")

    val_x, val_y, val_ids = combined_fit_arrays(dataset, "validation")
    if not np.isfinite(val_x).all():
        raise RuntimeError("Non-finite value(s) in Two-Step PU validation features -- refusing to evaluate.")

    val_proba_base = clf.estimator.predict_proba(val_x)[:, 1]
    val_proba_corrected = clf.predict_proba(val_x)[:, 1]
    if not np.isfinite(val_proba_base).all() or not np.isfinite(val_proba_corrected).all():
        raise RuntimeError("Non-finite value(s) in Two-Step PU validation predictions.")
    val_proba_corrected_clipped = np.clip(val_proba_corrected, 0.0, 1.0)

    is_positive = val_y == 1
    validation_metrics = {
        "base_estimator_proba": {
            "positive_rows": score_distribution_summary(val_proba_base[is_positive]),
            "unlabeled_rows": score_distribution_summary(val_proba_base[~is_positive]),
        },
        "corrected_proba_unclipped": {
            "positive_rows": score_distribution_summary(val_proba_corrected[is_positive]),
            "unlabeled_rows": score_distribution_summary(val_proba_corrected[~is_positive]),
            "fraction_exceeding_one_overall": float(np.mean(val_proba_corrected > 1.0)),
        },
        "corrected_proba_clipped_0_1": {
            "positive_rows": score_distribution_summary(val_proba_corrected_clipped[is_positive]),
            "unlabeled_rows": score_distribution_summary(val_proba_corrected_clipped[~is_positive]),
        },
    }

    train_metrics = {
        "estimated_c": float(clf.c),
        "hold_out_ratio": hold_out_ratio,
        "n_train_positive": int((train_y == 1).sum()),
        "n_train_unlabeled": int((train_y == 0).sum()),
    }

    checkpoint_metrics = {**train_metrics, "validation": validation_metrics}
    save_sklearn_checkpoint(run_dir, clf, checkpoint_metrics, is_best=True)
    save_sklearn_checkpoint(run_dir, clf, checkpoint_metrics, is_best=False)
    append_epoch_metrics(run_dir, epoch=0, metrics=checkpoint_metrics)

    elapsed_seconds = time.time() - start_time

    return {
        "seed_context": {
            "effective_seed": config.train_seed,
            "library": f"scikit-learn {sklearn.__version__} / pulearn",
            "note": "Determinism is controlled entirely via ElkanotoPuClassifier(random_state=...) and "
            "LogisticRegression(random_state=...); lbfgs is itself a deterministic solver given fixed "
            "data, so no separate global numpy/torch seed call is needed or made by this module.",
        },
        "base_estimator_decision": BASE_ESTIMATOR_DECISION_NOTE,
        "label_encoding_note": PU_SKLEARN_LABEL_ENCODING_NOTE,
        "estimated_c": float(clf.c),
        "hold_out_ratio": hold_out_ratio,
        "train_metrics": train_metrics,
        "validation_metrics": validation_metrics,
        "no_learning_curve_reason": "Two-Step PU's .fit() is a single, non-iterative procedure (one hold-out "
        "split, one classifier fit, one scalar correction constant) -- there is no per-epoch optimization "
        "trajectory to plot, unlike PN/nnPU's mini-batch training loops.",
        "elapsed_seconds": elapsed_seconds,
    }


__all__ = ["DEFAULT_HOLD_OUT_RATIO", "BASE_ESTIMATOR_DECISION_NOTE", "train_two_step_pu_baseline", "TwoStepPuResult"]
