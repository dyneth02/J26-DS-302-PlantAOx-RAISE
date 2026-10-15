"""Bucket 4, Task 4.4 -- PU-Bagging (Mordelet & Vert 2014-style) baseline.

Builds on ``pu_sklearn_common.build_sklearn_pu_dataset`` (Task 4.4's
shared dataset assembly -- the SAME one ``two_step_pu_baseline.py`` uses,
itself reusing Task 4.2/4.3's deterministic C1 partition and E1+E2
positive selection unchanged) rather than a second PU-dataset builder.
CLI stage: ``python -m plantaox.c2_pu.run fr4-pu-bagging-baseline``.

**What "PU-Bagging" means here, stated explicitly:** this implements the
bootstrap-aggregating PU classifier of Mordelet & Vert, "A bagging SVM to
learn from positive and unlabeled examples" (Pattern Recognition Letters,
2014), via ``pulearn.BaggingPuClassifier`` (itself adapted from
``sklearn.ensemble.BaggingClassifier``, citing the same paper directly in
its own docstring). The procedure:

1. Repeat ``n_estimators`` times: draw a bootstrap sample WITH
   REPLACEMENT **from the C1-unlabeled rows only**, of size
   ``max_samples`` (default ``1.0`` = the full unlabeled-row count, i.e.
   ``int(1.0 * n_c1_unlabeled)``), and combine it with ALL E1/E2 labeled
   positives (every positive row is included in EVERY bootstrap member,
   never resampled or left out) to fit one base classifier -- confirmed
   directly from ``pulearn``'s own source (``bagging.py``:
   ``unlabeled_count = count_nonzero(y == 0)``; ``max_samples`` is scaled
   against that count, not the combined row count), not assumed from its
   prose docstring alone. This is exactly Mordelet & Vert's prescribed
   procedure (bootstrap U, keep all of P fixed each iteration), treating
   the bootstrapped C1 rows AS IF negative for that bootstrap member's
   own training step -- the same standard PU-Bagging mechanism as
   Two-Step PU's first stage, not a reclassification of C1.
2. For each training row, average the predictions of only the ensemble
   members for which that row was OUT-OF-BAG (not drawn into that
   member's bootstrap sample) -- ``oob_decision_function_``. **A direct
   consequence of point 1, verified empirically on the real fold-0 run
   (see this module's acceptance test): every E1/E2 positive row has
   EXACTLY ZERO valid out-of-bag observations** (``oob_decision_function_``
   is NaN for all 604 training-positive rows, confirmed by
   ``n_rows_never_out_of_bag`` in this module's own diagnostics) --
   positives are never excluded from any bootstrap, so they can never be
   "out of bag." ``oob_score_``/``oob_decision_function_`` are therefore
   informative ONLY about the unlabeled (C1) training rows, which is
   exactly PU-Bagging's intended internal diagnostic (it estimates which
   unlabeled rows look most positive-like under repeated resampling, not
   a measure of positive-class recall). For out-of-sample (validation)
   rows, ``predict_proba`` averages ALL ensemble members' predictions (no
   OOB restriction applies, since those rows were never eligible to be
   in-bag in the first place).

**Why PU-Bagging's predicted probabilities stay bounded in ``[0, 1]``,
unlike Two-Step PU's corrected estimate:** PU-Bagging's final score is a
plain average of ordinary bounded classifier probabilities across
ensemble members -- there is no Elkan & Noto-style ``1/c`` correction
anywhere in this algorithm, so no out-of-range values are expected or
observed here (verified directly against the real fold-0 run, see the
module's own acceptance test).

**How this differs from PN (Task 4.2), nnPU (Task 4.3), and Two-Step PU
(this task), recorded explicitly:**

1. **Base estimator family and training cost.** Like Two-Step PU, this
   wraps ``sklearn.linear_model.LogisticRegression`` (see
   ``two_step_pu_baseline.BASE_ESTIMATOR_DECISION_NOTE`` -- the SAME
   decision applies here, kept in one place rather than duplicated) --
   NOT ``models.BinaryMlp``. Training cost is ``n_estimators`` independent
   ``LogisticRegression`` fits on bootstrap-resampled data (cheap per fit,
   embarrassingly parallel across ensemble members in principle, though
   this module runs single-threaded -- ``n_jobs=1`` -- for strict
   same-seed reproducibility) rather than one iterative gradient-descent
   trajectory.
2. **No epoch loop, no learning curve, no early stopping** -- same
   documented difference as Two-Step PU. ``.fit()`` with a fixed
   ``n_estimators`` is the whole training procedure; there is no
   per-epoch validation metric to monitor or stop early on. The
   ensemble's own internal validation signal is the out-of-bag score
   (``oob_score_``), reported here, not a held-out loss curve.
3. **No explicit prior or correction constant.** Unlike nnPU's ``pi`` or
   Two-Step PU's estimated ``c``, PU-Bagging has no analogous global
   scalar hyperparameter at all -- its only PU-specific "parameter" is
   the ensemble's bootstrap-and-average mechanism itself, controlled by
   ``n_estimators``/``max_samples``, both ordinary ensemble-size knobs
   rather than anything modeling a labeling or mixture prior.
4. **Risk/loss framework.** Same as Two-Step PU -- no BCE, no nnPU risk.
   Each bootstrap member is trained with its own base estimator's
   ordinary loss (logistic loss here); PU-Bagging's PU-specific
   contribution is purely the bootstrap/OOB-averaging SCHEME around that,
   not a custom risk estimator.

Deliberately NO torch import anywhere in this module -- PU-Bagging is
entirely scikit-learn/pulearn-based, exactly like Two-Step PU.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np

from plantaox.c2_pu.pu_sklearn_common import (
    PU_SKLEARN_LABEL_ENCODING_NOTE,
    SklearnPuDataset,
    combined_fit_arrays,
    save_sklearn_checkpoint,
    score_distribution_summary,
)
from plantaox.c2_pu.two_step_pu_baseline import BASE_ESTIMATOR_DECISION_NOTE

# Mordelet & Vert's own experiments and common PU-Bagging practice use
# ensembles on the order of a hundred bootstrap replicates (larger than
# scikit-learn's own conservative BaggingClassifier default of 10) to get
# a stable out-of-bag average -- this is a documented, reasonable default,
# not a tuned/selected value (no hyperparameter sweep was run; see
# docs/IMPLEMENTATION_STATUS.md's Task 4.4 decision log).
DEFAULT_N_ESTIMATORS = 100
DEFAULT_MAX_SAMPLES = 1.0  # pulearn's own default: bootstrap size = the full C1-unlabeled row count (all
# labeled positives are kept fixed in every bootstrap member -- see the module docstring, point 1).


def train_pu_bagging_baseline(
    config,
    dataset: SklearnPuDataset,
    run_dir: Path,
    n_estimators: int = DEFAULT_N_ESTIMATORS,
    max_samples: float = DEFAULT_MAX_SAMPLES,
) -> dict:
    """Fits ``pulearn.BaggingPuClassifier`` once (a single, non-iterative
    ``.fit()`` call that internally trains ``n_estimators`` bootstrap
    members -- see the module docstring) on the Task 4.4 shared PU
    dataset, computes OOB and validation-side diagnostics, and
    checkpoints the fitted ensemble via ``joblib``.
    """
    import sklearn
    from pulearn import BaggingPuClassifier
    from sklearn.linear_model import LogisticRegression

    from plantaox.c2_pu.run_recorder import append_epoch_metrics

    start_time = time.time()

    train_x, train_y, _train_ids = combined_fit_arrays(dataset, "train")
    if not np.isfinite(train_x).all():
        raise RuntimeError("Non-finite value(s) in PU-Bagging training features -- refusing to train.")

    base_estimator = LogisticRegression(max_iter=2000, random_state=config.train_seed)
    clf = BaggingPuClassifier(
        estimator=base_estimator,
        n_estimators=n_estimators,
        max_samples=max_samples,
        bootstrap=True,
        oob_score=True,
        random_state=config.train_seed,
        n_jobs=1,  # strict same-seed reproducibility over raw training speed
    )
    clf.fit(train_x, train_y)

    if not np.isfinite(clf.oob_score_):
        raise RuntimeError(f"PU-Bagging produced a non-finite OOB score: {clf.oob_score_!r}")

    oob_decision = clf.oob_decision_function_[:, 1]
    oob_finite_mask = np.isfinite(oob_decision)
    n_never_oob = int((~oob_finite_mask).sum())
    is_train_positive = train_y == 1
    oob_metrics = {
        "oob_score": float(clf.oob_score_),
        "n_rows_never_out_of_bag": n_never_oob,
        "n_rows_total": int(len(oob_decision)),
        "positive_rows": score_distribution_summary(oob_decision[is_train_positive & oob_finite_mask]),
        "unlabeled_rows": score_distribution_summary(oob_decision[~is_train_positive & oob_finite_mask]),
    }

    val_x, val_y, val_ids = combined_fit_arrays(dataset, "validation")
    if not np.isfinite(val_x).all():
        raise RuntimeError("Non-finite value(s) in PU-Bagging validation features -- refusing to evaluate.")

    val_proba = clf.predict_proba(val_x)[:, 1]
    if not np.isfinite(val_proba).all():
        raise RuntimeError("Non-finite value(s) in PU-Bagging validation predictions.")
    if not ((val_proba >= 0.0) & (val_proba <= 1.0)).all():
        raise RuntimeError("PU-Bagging validation predict_proba produced value(s) outside [0, 1].")

    is_val_positive = val_y == 1
    validation_metrics = {
        "positive_rows": score_distribution_summary(val_proba[is_val_positive]),
        "unlabeled_rows": score_distribution_summary(val_proba[~is_val_positive]),
    }

    train_metrics = {
        "n_estimators": n_estimators,
        "max_samples": max_samples,
        "n_train_positive": int((train_y == 1).sum()),
        "n_train_unlabeled": int((train_y == 0).sum()),
        "oob": oob_metrics,
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
            "note": "Determinism is controlled entirely via BaggingPuClassifier(random_state=..., n_jobs=1) "
            "and LogisticRegression(random_state=...); no separate global numpy/torch seed call is needed "
            "or made by this module.",
        },
        "base_estimator_decision": BASE_ESTIMATOR_DECISION_NOTE,
        "label_encoding_note": PU_SKLEARN_LABEL_ENCODING_NOTE,
        "n_estimators": n_estimators,
        "max_samples": max_samples,
        "oob_metrics": oob_metrics,
        "train_metrics": train_metrics,
        "validation_metrics": validation_metrics,
        "no_learning_curve_reason": "PU-Bagging's .fit() is a single, non-iterative procedure that internally "
        "trains n_estimators bootstrap members in one call -- there is no per-epoch optimization trajectory "
        "to plot, unlike PN/nnPU's mini-batch training loops. The ensemble's own internal validation signal "
        "(out-of-bag score) is reported in oob_metrics instead of a held-out loss curve.",
        "elapsed_seconds": elapsed_seconds,
    }


__all__ = ["DEFAULT_N_ESTIMATORS", "DEFAULT_MAX_SAMPLES", "train_pu_bagging_baseline"]
