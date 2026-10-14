"""Bucket 4.3 -- non-negative PU (nnPU) risk estimator.

Implements the Kiryo et al. (2017) "Positive-Unlabeled Learning with
Non-Negative Risk Estimator" objective, as the explicitly-named **direct
clamped** variant.

Mathematical formulation (exactly as specified for Task 4.3)
--------------------------------------------------------------
Let:
    P  = labeled positive samples (fused-feature rows)
    U  = unlabeled samples (C1 -- never "negatives", see AGENTS.md rule 1)
    pi = assumed positive-class prior in U's generating distribution
    f_theta(x) = model's raw logit (never a sigmoid-ed probability)
    l(f, +1) = softplus(-f)   (stable binary logistic loss, positive class)
    l(f, -1) = softplus(f)    (stable binary logistic loss, negative class)

    R_p^+ = E_{x~P}[l(f(x), +1)]      (positive-risk component)
    R_p^- = E_{x~P}[l(f(x), -1)]      (positive-as-negative risk component)
    R_u^- = E_{x~U}[l(f(x), -1)]      (unlabeled-as-negative risk component)

    R_n     = R_u^- - pi * R_p^-                 (estimated negative risk)
    R_uPU   = pi * R_p^+ + R_n                   (ordinary/unbiased PU risk)
    R_nnPU  = pi * R_p^+ + max(0, R_n)           (non-negative PU risk)

Each of R_p^+, R_p^-, R_u^- is a SEPARATE per-group mean (never a single
mean over a combined positive+unlabeled batch) -- this is what makes the
pi/|P|/|U| weighting in the math hold regardless of whatever
positive/unlabeled mini-batch SIZE ratio a training loop happens to draw
(Task 4.3 Section 10.1's requirement; see ``nnpu_baseline.py``).

Which nnPU variant this module implements, and why
----------------------------------------------------
The original Kiryo et al. paper also describes a *training procedure*
(not just the displayed risk number) in which, once the estimated
negative risk R_n drops below a threshold ``-beta``, the optimizer takes
a **gradient-ASCENT** step on R_n (scaled by a hyperparameter ``gamma``)
instead of simply following the gradient of ``max(0, R_n)`` (whose
gradient is exactly zero whenever R_n < 0). These are related but **not
interchangeable** training algorithms, per the task's explicit
instruction not to silently conflate them.

Before writing this module, the following were inspected for a
pre-specified choice between the two: ``docs/PU_AOP_RESEARCH_CONTEXT.md``,
``docs/PU_AOP_PP1_Microsoft_Planner_Buckets_and_Tasks.md`` (Sections
"4.3 -- Plain nnPU Baseline Implementation" and "4.6 -- Optional FR4
Curriculum Prototype"), the proposal PDF's abridged FR3/FR4 requirement
table, and every existing decision-log entry in
``docs/IMPLEMENTATION_STATUS.md``. **None specifies the beta/gamma
corrective procedure, a beta or gamma value, or even that a corrective
step is required.** Per the task's own fallback instruction ("if neither
is specified, use the direct clamped objective as the explicitly named
initial baseline, and document that it is not automatically equivalent
to the original beta/gamma corrective training algorithm"), this module
implements and only implements the **direct clamped objective**:
backpropagating through ``max(0, R_n)`` itself.

``nnpu_variant = "direct_clamped"`` is recorded in every run's resolved
config/manifest/summary so this choice is never ambiguous later. The
beta/gamma corrective variant is NOT implemented anywhere in this
component as of Task 4.3 -- this is a scope decision, logged in
``docs/IMPLEMENTATION_STATUS.md``'s decision log, not an oversight.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import torch
import torch.nn.functional as F

MIN_PRIOR = 0.0
MAX_PRIOR = 1.0

NNPU_VARIANT_DIRECT_CLAMPED = "direct_clamped"


class InvalidPriorError(ValueError):
    """Raised when a configured/assumed positive-class prior ``pi`` is
    not a finite, non-boolean numeric value strictly between 0 and 1."""


class EmptyBatchError(ValueError):
    """Raised when the nnPU risk estimator is asked to compute a risk
    over a positive or unlabeled group with zero rows. The estimator is
    mathematically undefined for an empty group (its mean has no
    denominator), so this fails loudly rather than silently returning
    ``nan`` or treating the missing group as contributing zero risk."""


def validate_prior(prior: float) -> float:
    """Requires ``0 < prior < 1`` (Section 8/Test F). Rejects ``bool``
    (a `bool` is technically an `int` in Python and would otherwise
    silently pass an ``isinstance(..., (int, float))`` check), ``NaN``,
    and infinite values with a clear, specific exception rather than
    letting a bad prior silently propagate into ``softplus``/the risk
    sum and surface as a confusing downstream NaN.
    """
    if isinstance(prior, bool):
        raise InvalidPriorError(f"prior must be a float/int, got bool {prior!r}")
    try:
        value = float(prior)
    except (TypeError, ValueError) as exc:
        raise InvalidPriorError(f"prior must be convertible to float, got {prior!r}") from exc
    if math.isnan(value) or math.isinf(value):
        raise InvalidPriorError(f"prior must be finite, got {prior!r}")
    if not (MIN_PRIOR < value < MAX_PRIOR):
        raise InvalidPriorError(f"prior must be strictly between 0 and 1, got {value!r}")
    return value


def logistic_loss_positive(logits: torch.Tensor) -> torch.Tensor:
    """l(f, +1) = softplus(-f) -- elementwise, numerically stable
    (``torch.nn.functional.softplus`` switches to a linear
    approximation past its ``threshold`` to avoid overflow for large
    inputs; sigmoid is never applied before this loss, per Section 4.1).
    """
    return F.softplus(-logits)


def logistic_loss_negative(logits: torch.Tensor) -> torch.Tensor:
    """l(f, -1) = softplus(f) -- elementwise, numerically stable."""
    return F.softplus(logits)


@dataclass
class NnPuRiskResult:
    """Every risk component Task 4.3 Section 10.3 requires to be logged.

    ``loss`` is the differentiable scalar tensor to call ``.backward()``
    on (the direct-clamped nnPU objective); every other field is a plain
    Python ``float``/``bool`` detached from the graph, safe to log or
    JSON-serialize directly.
    """

    loss: torch.Tensor
    positive_risk_contribution: float  # pi * R_p^+          (objective term 1)
    positive_as_negative_risk: float  # R_p^- (raw, unweighted)
    unlabeled_as_negative_risk: float  # R_u^- (raw, unweighted)
    negative_risk_unclamped: float  # R_n = R_u^- - pi * R_p^-
    negative_risk_contribution: float  # max(0, R_n)          (objective term 2)
    is_clamped: bool  # True iff R_n < 0 this step (term 2's gradient is zero)
    unbiased_pu_risk: float  # pi*R_p^+ + R_n  (R_uPU, for comparison/Test B)
    prior: float
    n_positive: int
    n_unlabeled: int


def compute_nnpu_risk(
    positive_logits: torch.Tensor,
    unlabeled_logits: torch.Tensor,
    prior: float,
) -> NnPuRiskResult:
    """The non-negative PU risk estimator (direct-clamped variant -- see
    module docstring).

    Averages ``l(f,+1)``/``l(f,-1)`` SEPARATELY within each group
    (positive, unlabeled) before combining with ``pi`` -- never pools
    positive+unlabeled rows into one combined mean, so the estimator's
    pi/|P|/|U| weighting is respected regardless of the positive/
    unlabeled mini-batch SIZE RATIO a caller happens to pass in (Test H;
    Section 10.1).

    Raises ``InvalidPriorError`` for an out-of-range/non-finite prior,
    ``EmptyBatchError`` for an empty positive or unlabeled group, and a
    plain ``ValueError`` for non-finite input logits or a non-finite
    resulting risk -- mirroring ``pn_baseline.py``'s own
    fail-loudly-on-non-finite-value discipline rather than silently
    continuing past a NaN/Inf.
    """
    prior = validate_prior(prior)

    if positive_logits.numel() == 0:
        raise EmptyBatchError("compute_nnpu_risk: positive batch/group is empty.")
    if unlabeled_logits.numel() == 0:
        raise EmptyBatchError("compute_nnpu_risk: unlabeled batch/group is empty.")

    positive_logits = positive_logits.reshape(-1)
    unlabeled_logits = unlabeled_logits.reshape(-1)

    if not torch.isfinite(positive_logits).all():
        raise ValueError("compute_nnpu_risk: non-finite positive-group logit(s) passed in.")
    if not torch.isfinite(unlabeled_logits).all():
        raise ValueError("compute_nnpu_risk: non-finite unlabeled-group logit(s) passed in.")

    r_p_plus = logistic_loss_positive(positive_logits).mean()
    r_p_minus = logistic_loss_negative(positive_logits).mean()
    r_u_minus = logistic_loss_negative(unlabeled_logits).mean()

    positive_term = prior * r_p_plus
    negative_risk = r_u_minus - prior * r_p_minus
    clamped_negative_term = torch.clamp(negative_risk, min=0.0)

    loss = positive_term + clamped_negative_term
    unbiased_pu_risk = positive_term + negative_risk

    if not torch.isfinite(loss):
        raise ValueError("compute_nnpu_risk: resulting nnPU risk is non-finite.")

    return NnPuRiskResult(
        loss=loss,
        positive_risk_contribution=float(positive_term.detach().item()),
        positive_as_negative_risk=float(r_p_minus.detach().item()),
        unlabeled_as_negative_risk=float(r_u_minus.detach().item()),
        negative_risk_unclamped=float(negative_risk.detach().item()),
        negative_risk_contribution=float(clamped_negative_term.detach().item()),
        is_clamped=bool(negative_risk.detach().item() < 0.0),
        unbiased_pu_risk=float(unbiased_pu_risk.detach().item()),
        prior=prior,
        n_positive=int(positive_logits.numel()),
        n_unlabeled=int(unlabeled_logits.numel()),
    )
