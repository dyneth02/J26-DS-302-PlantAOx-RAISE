"""Bucket 4.3 POST-ACCEPTANCE DIAGNOSTIC -- unit tests for the pure-math
diagnostic helpers in ``nnpu_prior_diagnostics.py`` (clamped-fraction,
percentile/min/max aggregation, epoch-level risk re-aggregation,
prediction-saturation summary). These are torch-free, fast, and require
no real trained model or fold-0 cache -- run unconditionally, unlike the
acceptance suite below which is gated on real local artifacts.

Every test checks actual numeric correctness against an independently
computed reference value, not merely that the function returns without
raising -- matching this project's own ``test_nnpu_risk.py`` discipline.
"""

from __future__ import annotations

import numpy as np
import pytest

from plantaox.c2_pu.nnpu_prior_diagnostics import (
    clamped_fraction,
    epoch_level_risk_aggregation,
    percentile_summary,
    prediction_saturation_summary,
)

# ---------------------------------------------------------------------------
# clamped_fraction
# ---------------------------------------------------------------------------


def test_clamped_fraction_empty_list_is_zero_not_nan():
    assert clamped_fraction([]) == 0.0


def test_clamped_fraction_all_clamped_is_one():
    assert clamped_fraction([True, True, True]) == pytest.approx(1.0)


def test_clamped_fraction_none_clamped_is_zero():
    assert clamped_fraction([False, False, False, False]) == pytest.approx(0.0)


def test_clamped_fraction_mixed_matches_manual_count():
    flags = [True, False, True, True, False]  # 3 of 5
    assert clamped_fraction(flags) == pytest.approx(3 / 5)


# ---------------------------------------------------------------------------
# percentile_summary
# ---------------------------------------------------------------------------


def test_percentile_summary_known_values():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = percentile_summary(values, percentiles=(50.0,))
    assert result["n"] == 5
    assert result["min"] == pytest.approx(1.0)
    assert result["max"] == pytest.approx(5.0)
    assert result["mean"] == pytest.approx(3.0)
    assert result["p50"] == pytest.approx(3.0)


def test_percentile_summary_matches_numpy_reference_for_default_percentiles():
    rng = np.random.default_rng(0)
    values = rng.normal(size=200).tolist()
    result = percentile_summary(values)
    ref = np.asarray(values)
    assert result["min"] == pytest.approx(float(ref.min()))
    assert result["max"] == pytest.approx(float(ref.max()))
    assert result["mean"] == pytest.approx(float(ref.mean()))
    assert result["p5"] == pytest.approx(float(np.percentile(ref, 5)))
    assert result["p50"] == pytest.approx(float(np.percentile(ref, 50)))
    assert result["p95"] == pytest.approx(float(np.percentile(ref, 95)))


def test_percentile_summary_empty_raises():
    with pytest.raises(ValueError):
        percentile_summary([])


def test_percentile_summary_single_value_all_stats_equal_that_value():
    result = percentile_summary([7.0])
    assert result["min"] == result["max"] == result["mean"] == pytest.approx(7.0)
    assert result["p50"] == pytest.approx(7.0)


# ---------------------------------------------------------------------------
# epoch_level_risk_aggregation
# ---------------------------------------------------------------------------


def test_epoch_level_risk_aggregation_matches_manual_weighted_mean():
    values = [1.0, 2.0, 3.0]
    batch_sizes = [10, 20, 5]
    expected = (1.0 * 10 + 2.0 * 20 + 3.0 * 5) / (10 + 20 + 5)
    assert epoch_level_risk_aggregation(values, batch_sizes) == pytest.approx(expected)


def test_epoch_level_risk_aggregation_equal_batch_sizes_is_plain_mean():
    values = [2.0, 4.0, 6.0]
    batch_sizes = [1, 1, 1]
    assert epoch_level_risk_aggregation(values, batch_sizes) == pytest.approx(4.0)


def test_epoch_level_risk_aggregation_empty_raises():
    with pytest.raises(ValueError):
        epoch_level_risk_aggregation([], [])


def test_epoch_level_risk_aggregation_mismatched_lengths_raise():
    with pytest.raises(ValueError):
        epoch_level_risk_aggregation([1.0, 2.0], [1])


def test_epoch_level_risk_aggregation_zero_total_batch_size_raises():
    with pytest.raises(ValueError):
        epoch_level_risk_aggregation([1.0], [0])


# ---------------------------------------------------------------------------
# prediction_saturation_summary
# ---------------------------------------------------------------------------


def test_prediction_saturation_summary_known_fractions():
    # 2 of 10 values < 0.01, 3 of 10 values > 0.99, rest in between.
    proba = np.array([0.001, 0.009, 0.3, 0.4, 0.5, 0.6, 0.7, 0.992, 0.995, 0.999])
    result = prediction_saturation_summary(proba)
    assert result["n"] == 10
    assert result["fraction_lt_0_01"] == pytest.approx(2 / 10)
    assert result["fraction_gt_0_99"] == pytest.approx(3 / 10)
    assert result["fraction_gt_0_5"] == pytest.approx(5 / 10)  # 0.6,0.7,0.992,0.995,0.999
    assert result["min"] == pytest.approx(0.001)
    assert result["max"] == pytest.approx(0.999)


def test_prediction_saturation_summary_matches_numpy_percentiles():
    rng = np.random.default_rng(1)
    proba = rng.uniform(size=500)
    result = prediction_saturation_summary(proba)
    assert result["p25"] == pytest.approx(float(np.percentile(proba, 25)))
    assert result["p75"] == pytest.approx(float(np.percentile(proba, 75)))
    assert result["median"] == pytest.approx(float(np.median(proba)))
    assert result["std"] == pytest.approx(float(proba.std()))


def test_prediction_saturation_summary_empty_raises():
    with pytest.raises(ValueError):
        prediction_saturation_summary(np.array([]))


def test_prediction_saturation_summary_non_finite_raises():
    with pytest.raises(ValueError):
        prediction_saturation_summary(np.array([0.1, float("nan"), 0.5]))


def test_prediction_saturation_summary_out_of_bounds_raises():
    with pytest.raises(ValueError):
        prediction_saturation_summary(np.array([0.1, 1.5, 0.3]))
    with pytest.raises(ValueError):
        prediction_saturation_summary(np.array([-0.1, 0.5]))


def test_prediction_saturation_summary_accepts_2d_input_shape():
    # predict_proba's own output shape is (batch, 1) -- must reshape, not reject.
    proba = np.array([[0.1], [0.9], [0.5]])
    result = prediction_saturation_summary(proba)
    assert result["n"] == 3
