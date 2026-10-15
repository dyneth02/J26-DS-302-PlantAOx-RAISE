"""Bucket 4, Task 4.3 -- mathematical unit tests for the nnPU risk
estimator (``nnpu_risk.py``), run BEFORE any real training per Task
4.3's Stage A ("do not proceed to real training if these tests fail").

Every test verifies the actual mathematics (manually-computed reference
values / algebraic constructions), not merely that the output is
finite -- matching the task's explicit instruction not to settle for
"it ran without crashing."
"""

from __future__ import annotations

import math

import pytest
import torch

from plantaox.c2_pu.nnpu_risk import (
    EmptyBatchError,
    InvalidPriorError,
    NnPuRiskResult,
    compute_nnpu_risk,
    logistic_loss_negative,
    logistic_loss_positive,
    validate_prior,
)


def _softplus_ref(x: float) -> float:
    """High-precision reference softplus via Python's own ``math`` module
    (not the implementation under test) -- used to hand-derive every
    "known manual risk value" in Test A independently of
    ``torch.nn.functional.softplus``."""
    if x > 30:
        return x
    return math.log1p(math.exp(x))


# ---------------------------------------------------------------------------
# Test A -- known manual risk values
# ---------------------------------------------------------------------------


def test_known_manual_risk_values_match_hand_computed_reference():
    positive_logits = torch.tensor([1.0, -0.5, 2.0])
    unlabeled_logits = torch.tensor([0.5, -1.0, 0.0, 1.5])
    prior = 0.3

    # Hand-computed reference, entirely independent of the module under test.
    ref_r_p_plus = sum(_softplus_ref(-x) for x in (1.0, -0.5, 2.0)) / 3
    ref_r_p_minus = sum(_softplus_ref(x) for x in (1.0, -0.5, 2.0)) / 3
    ref_r_u_minus = sum(_softplus_ref(x) for x in (0.5, -1.0, 0.0, 1.5)) / 4
    ref_positive_term = prior * ref_r_p_plus
    ref_negative_risk = ref_r_u_minus - prior * ref_r_p_minus
    ref_clamped = max(0.0, ref_negative_risk)
    ref_nnpu = ref_positive_term + ref_clamped

    result = compute_nnpu_risk(positive_logits, unlabeled_logits, prior)

    assert result.positive_risk_contribution == pytest.approx(ref_positive_term, abs=1e-6)
    assert result.positive_as_negative_risk == pytest.approx(ref_r_p_minus, abs=1e-6)
    assert result.unlabeled_as_negative_risk == pytest.approx(ref_r_u_minus, abs=1e-6)
    assert result.negative_risk_unclamped == pytest.approx(ref_negative_risk, abs=1e-6)
    assert result.negative_risk_contribution == pytest.approx(ref_clamped, abs=1e-6)
    assert float(result.loss.item()) == pytest.approx(ref_nnpu, abs=1e-6)


# ---------------------------------------------------------------------------
# Test B -- positive negative-risk component: nnPU == unbiased PU risk
# ---------------------------------------------------------------------------


def test_nnpu_equals_unbiased_pu_risk_when_negative_risk_is_positive():
    # Unlabeled logits strongly positive (high softplus(f)) vs. positive
    # logits strongly negative (low softplus(f)) -- guarantees
    # R_u^- - pi*R_p^- > 0 for any reasonable pi.
    positive_logits = torch.tensor([-5.0, -4.0, -6.0])
    unlabeled_logits = torch.tensor([5.0, 4.0, 6.0])
    prior = 0.1

    result = compute_nnpu_risk(positive_logits, unlabeled_logits, prior)
    assert result.negative_risk_unclamped > 0
    assert not result.is_clamped
    assert float(result.loss.item()) == pytest.approx(result.unbiased_pu_risk, abs=1e-9)


# ---------------------------------------------------------------------------
# Test C -- negative estimated negative risk: nnPU clamps to zero
# ---------------------------------------------------------------------------


def test_nnpu_clamps_negative_risk_to_zero_when_estimate_is_negative():
    # Unlabeled logits strongly negative (low softplus(f)) vs. positive
    # logits near zero -- guarantees R_u^- - pi*R_p^- < 0.
    positive_logits = torch.tensor([0.0, 0.1, -0.1])
    unlabeled_logits = torch.tensor([-8.0, -9.0, -7.0])
    prior = 0.5

    result = compute_nnpu_risk(positive_logits, unlabeled_logits, prior)
    assert result.negative_risk_unclamped < 0
    assert result.is_clamped
    assert result.negative_risk_contribution == 0.0
    assert float(result.loss.item()) == pytest.approx(result.positive_risk_contribution, abs=1e-9)
    # The clamped nnPU risk must be strictly less than the (negative)
    # unbiased PU risk it was clamped away from.
    assert float(result.loss.item()) > result.unbiased_pu_risk


# ---------------------------------------------------------------------------
# Test D -- zero-boundary behavior (deliberately constructed, not accidental)
# ---------------------------------------------------------------------------


def test_zero_boundary_negative_risk_deliberately_constructed():
    # Solve analytically for b such that softplus(b) == pi * softplus(a)
    # with a=0, pi=0.5: softplus(0) = ln(2); need softplus(b) = 0.5*ln(2)
    # => b = ln(exp(0.5*ln(2)) - 1).
    prior = 0.5
    a = 0.0
    target = prior * _softplus_ref(a)
    b = math.log(math.exp(target) - 1.0)

    positive_logits = torch.tensor([a, a, a])
    unlabeled_logits = torch.tensor([b, b, b])

    result = compute_nnpu_risk(positive_logits, unlabeled_logits, prior)
    # Deliberately constructed to be (near) exactly zero -- not relying
    # on an accidental float equality, hence the generous-but-tight
    # tolerance rather than `== 0.0`.
    assert result.negative_risk_unclamped == pytest.approx(0.0, abs=1e-6)
    # At the boundary, clamped and unclamped forms must agree.
    assert float(result.loss.item()) == pytest.approx(result.unbiased_pu_risk, abs=1e-6)
    assert float(result.loss.item()) == pytest.approx(result.positive_risk_contribution, abs=1e-6)


# ---------------------------------------------------------------------------
# Test E -- gradient behavior
# ---------------------------------------------------------------------------


def test_gradients_flow_through_unclamped_branch_with_expected_sign():
    positive_logits = torch.tensor([-5.0, -4.0], requires_grad=True)
    unlabeled_logits = torch.tensor([5.0, 4.0], requires_grad=True)
    prior = 0.2

    result = compute_nnpu_risk(positive_logits, unlabeled_logits, prior)
    assert not result.is_clamped
    result.loss.backward()

    assert positive_logits.grad is not None
    assert unlabeled_logits.grad is not None
    assert torch.isfinite(positive_logits.grad).all()
    assert torch.isfinite(unlabeled_logits.grad).all()
    # d/df softplus(f) = sigmoid(f) > 0, so increasing an unlabeled
    # logit increases R_u^- -> increases the (unclamped) loss: positive
    # gradient. d/df softplus(-f) = -sigmoid(-f) < 0, so increasing a
    # positive logit DECREASES R_p^+ -> gradient is negative.
    assert (unlabeled_logits.grad > 0).all()
    assert (positive_logits.grad < 0).all()


def test_gradient_is_zero_for_unlabeled_group_when_clamped():
    positive_logits = torch.tensor([0.0, 0.1], requires_grad=True)
    unlabeled_logits = torch.tensor([-8.0, -9.0], requires_grad=True)
    prior = 0.5

    result = compute_nnpu_risk(positive_logits, unlabeled_logits, prior)
    assert result.is_clamped
    result.loss.backward()

    # max(0, R_n) has zero gradient w.r.t. anything R_n depends on when
    # R_n < 0 -- so the unlabeled-group gradient must be exactly zero
    # under the direct-clamped objective (this IS the defining property
    # distinguishing it from the unbiased/uncl amped PU risk).
    assert torch.allclose(unlabeled_logits.grad, torch.zeros_like(unlabeled_logits.grad))
    # The positive-risk term (pi * R_p^+) is unaffected by clamping and
    # must still have a non-zero gradient.
    assert not torch.allclose(positive_logits.grad, torch.zeros_like(positive_logits.grad))


# ---------------------------------------------------------------------------
# Test F -- positive-prior validation
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("bad_prior", [0.0, 1.0, -0.1, 1.1, float("nan"), float("inf"), float("-inf")])
def test_validate_prior_rejects_out_of_range_or_non_finite(bad_prior):
    with pytest.raises(InvalidPriorError):
        validate_prior(bad_prior)


def test_validate_prior_rejects_bool():
    with pytest.raises(InvalidPriorError):
        validate_prior(True)


@pytest.mark.parametrize("good_prior", [0.01, 0.05, 0.1, 0.2, 0.5, 0.99])
def test_validate_prior_accepts_open_interval(good_prior):
    assert validate_prior(good_prior) == pytest.approx(good_prior)


def test_compute_nnpu_risk_rejects_invalid_prior_before_touching_logits():
    with pytest.raises(InvalidPriorError):
        compute_nnpu_risk(torch.tensor([1.0]), torch.tensor([1.0]), prior=1.5)


# ---------------------------------------------------------------------------
# Test G -- numerical stability
# ---------------------------------------------------------------------------


def test_numerical_stability_with_large_logits():
    positive_logits = torch.tensor([1e4, -1e4, 1e4])
    unlabeled_logits = torch.tensor([-1e4, 1e4, -1e4])
    result = compute_nnpu_risk(positive_logits, unlabeled_logits, prior=0.1)
    assert math.isfinite(result.positive_risk_contribution)
    assert math.isfinite(result.negative_risk_contribution)
    assert math.isfinite(float(result.loss.item()))


def test_numerical_stability_with_gradient_at_large_logits():
    positive_logits = torch.tensor([1e5, -1e5], requires_grad=True)
    unlabeled_logits = torch.tensor([-1e5, 1e5], requires_grad=True)
    result = compute_nnpu_risk(positive_logits, unlabeled_logits, prior=0.1)
    result.loss.backward()
    assert torch.isfinite(positive_logits.grad).all()
    assert torch.isfinite(unlabeled_logits.grad).all()


def test_logistic_loss_helpers_never_produce_nan_or_inf_at_extremes():
    extreme = torch.tensor([1e8, -1e8, 0.0])
    assert torch.isfinite(logistic_loss_positive(extreme)).all()
    assert torch.isfinite(logistic_loss_negative(extreme)).all()


# ---------------------------------------------------------------------------
# Test H -- batch-size / reduction semantics (no raw-count weighting)
# ---------------------------------------------------------------------------


def test_risk_is_a_per_group_mean_not_weighted_by_raw_group_size():
    # 2 positives vs 200 unlabeled, all unlabeled logits identical to the
    # 2 positive logits' negative-loss value -- if the estimator pooled
    # everything into one combined mean instead of two independent
    # per-group means, the result would differ sharply from this
    # reference (which assumes exactly two independent group means).
    positive_logits = torch.tensor([0.3, -0.7])
    unlabeled_logits = torch.full((200,), 0.3)
    prior = 0.25

    result = compute_nnpu_risk(positive_logits, unlabeled_logits, prior)

    ref_r_p_plus = (_softplus_ref(-0.3) + _softplus_ref(0.7)) / 2
    ref_r_p_minus = (_softplus_ref(0.3) + _softplus_ref(-0.7)) / 2
    ref_r_u_minus = _softplus_ref(0.3)  # all 200 unlabeled rows identical
    ref_positive_term = prior * ref_r_p_plus
    ref_negative_risk = ref_r_u_minus - prior * ref_r_p_minus

    assert result.positive_risk_contribution == pytest.approx(ref_positive_term, abs=1e-6)
    assert result.unlabeled_as_negative_risk == pytest.approx(ref_r_u_minus, abs=1e-6)
    assert result.negative_risk_unclamped == pytest.approx(ref_negative_risk, abs=1e-6)


def test_risk_is_invariant_to_unlabeled_group_size_when_homogeneous():
    # Doubling an UNLABELED group of identical-valued logits must not
    # change the per-group mean (and hence not the risk) -- this would
    # fail under naive raw-count/combined-batch weighting.
    positive_logits = torch.tensor([1.0, -1.0, 0.5])
    small_unlabeled = torch.full((5,), 0.4)
    large_unlabeled = torch.full((500,), 0.4)
    prior = 0.15

    result_small = compute_nnpu_risk(positive_logits, small_unlabeled, prior)
    result_large = compute_nnpu_risk(positive_logits, large_unlabeled, prior)

    assert result_small.unlabeled_as_negative_risk == pytest.approx(result_large.unlabeled_as_negative_risk, abs=1e-6)
    assert float(result_small.loss.item()) == pytest.approx(float(result_large.loss.item()), abs=1e-6)


# ---------------------------------------------------------------------------
# Test I -- empty-class handling
# ---------------------------------------------------------------------------


def test_empty_positive_batch_is_rejected():
    with pytest.raises(EmptyBatchError):
        compute_nnpu_risk(torch.empty(0), torch.tensor([0.1, 0.2]), prior=0.1)


def test_empty_unlabeled_batch_is_rejected():
    with pytest.raises(EmptyBatchError):
        compute_nnpu_risk(torch.tensor([0.1, 0.2]), torch.empty(0), prior=0.1)


def test_both_empty_batches_are_rejected():
    with pytest.raises(EmptyBatchError):
        compute_nnpu_risk(torch.empty(0), torch.empty(0), prior=0.1)


# ---------------------------------------------------------------------------
# Additional robustness: non-finite logit inputs, 2D-shaped logits
# ---------------------------------------------------------------------------


def test_non_finite_positive_logits_are_rejected():
    with pytest.raises(ValueError, match="non-finite"):
        compute_nnpu_risk(torch.tensor([float("nan"), 0.1]), torch.tensor([0.1, 0.2]), prior=0.1)


def test_non_finite_unlabeled_logits_are_rejected():
    with pytest.raises(ValueError, match="non-finite"):
        compute_nnpu_risk(torch.tensor([0.1, 0.2]), torch.tensor([float("inf"), 0.1]), prior=0.1)


def test_accepts_column_shaped_batch_x_1_logits():
    # Models return (batch, 1) logits -- the estimator must accept and
    # correctly flatten this shape, matching BinaryMlp.forward's output.
    positive_logits = torch.tensor([[1.0], [-0.5]])
    unlabeled_logits = torch.tensor([[0.5], [-1.0], [0.2]])
    result = compute_nnpu_risk(positive_logits, unlabeled_logits, prior=0.1)
    assert isinstance(result, NnPuRiskResult)
    assert result.n_positive == 2
    assert result.n_unlabeled == 3


# Note on Test J (corrective beta/gamma optimization): NOT applicable --
# this module implements only the direct-clamped nnPU variant (see
# module docstring for why), so there is no beta/gamma branch to test.
