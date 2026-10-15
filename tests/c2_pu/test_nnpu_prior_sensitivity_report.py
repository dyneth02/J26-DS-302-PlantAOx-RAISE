"""Bucket 4.3 POST-ACCEPTANCE DIAGNOSTIC -- unit tests for comparison-
table assembly, classification, and SVG rendering
(``nnpu_prior_sensitivity_report.py``). Torch-free, fast, no gating.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from plantaox.c2_pu.nnpu_prior_sensitivity_report import (
    build_comparison_table,
    classify_prior_sensitivity,
    render_dual_component_svg,
    render_multi_series_line_svg,
    render_score_distribution_svg,
)

# ---------------------------------------------------------------------------
# build_comparison_table
# ---------------------------------------------------------------------------


def test_build_comparison_table_fills_missing_fields_with_not_measured():
    rows = {"0.10": {"executed_epochs": 26, "best_epoch": 15}}
    table = build_comparison_table(rows)
    assert table["0.10"]["executed_epochs"] == 26
    assert table["0.10"]["best_epoch"] == 15
    assert table["0.10"]["best_val_nnpu_risk"] == "NOT MEASURED"
    assert table["0.10"]["e1_median_score"] == "NOT MEASURED"


def test_build_comparison_table_never_fabricates_a_numeric_value():
    rows = {"0.05": {}}
    table = build_comparison_table(rows)
    assert all(v == "NOT MEASURED" for v in table["0.05"].values())


def test_build_comparison_table_sorts_priors():
    rows = {"0.20": {}, "0.05": {}, "0.10": {}}
    table = build_comparison_table(rows)
    assert list(table.keys()) == ["0.05", "0.10", "0.20"]


# ---------------------------------------------------------------------------
# classify_prior_sensitivity
# ---------------------------------------------------------------------------


def test_classify_persistently_clamped_when_all_near_universal_and_tight():
    fractions = {"0.05": 0.982, "0.10": 0.986, "0.20": 0.992}
    assert classify_prior_sensitivity(fractions) == "Persistently clamped"


def test_classify_prior_sensitive_when_spread_is_large_and_not_all_near_universal():
    fractions = {"0.05": 0.10, "0.10": 0.50, "0.20": 0.95}
    assert classify_prior_sensitivity(fractions) == "Prior-sensitive"


def test_classify_inconclusive_with_fewer_than_two_measured_priors():
    assert classify_prior_sensitivity({"0.10": 0.98}) == "Inconclusive"
    assert classify_prior_sensitivity({}) == "Inconclusive"


def test_classify_ignores_non_numeric_not_measured_entries():
    fractions = {"0.05": 0.98, "0.10": "NOT MEASURED", "0.20": 0.99}
    # Only 2 real numeric values remain -- still classifiable, not crashing on the string.
    result = classify_prior_sensitivity(fractions)
    assert result in {"Persistently clamped", "Prior-sensitive", "Mixed behavior", "Inconclusive"}


# ---------------------------------------------------------------------------
# SVG rendering -- structural validity, not pixel-exact appearance
# ---------------------------------------------------------------------------


def test_render_multi_series_line_svg_produces_one_polyline_per_series(tmp_path):
    series = {
        "0.05": [(0, 0.1), (1, 0.2), (2, 0.15)],
        "0.10": [(0, 0.9), (1, 0.95), (2, 0.99)],
        "0.20": [(0, 0.5), (1, 0.6), (2, 0.7)],
    }
    out = render_multi_series_line_svg(series, tmp_path / "plot.svg", title="t", y_label="y")
    content = out.read_text(encoding="utf-8")
    assert content.startswith("<svg")
    assert content.count("<polyline") == 3


def test_render_multi_series_line_svg_zero_reference_line_present(tmp_path):
    series = {"0.10": [(0, -0.5), (1, 0.5)]}
    out = render_multi_series_line_svg(
        series, tmp_path / "plot.svg", title="t", y_label="y", zero_reference_line=True
    )
    content = out.read_text(encoding="utf-8")
    assert "R_n = 0" in content


def test_render_multi_series_line_svg_empty_raises(tmp_path):
    with pytest.raises(ValueError):
        render_multi_series_line_svg({}, tmp_path / "plot.svg", title="t", y_label="y")


def test_render_dual_component_svg_has_solid_and_dashed_lines(tmp_path):
    positive = {"0.10": [(0, 0.01), (1, 0.02)]}
    negative = {"0.10": [(0, -3.0), (1, -2.0)]}
    out = render_dual_component_svg(positive, negative, tmp_path / "plotc.svg", title="t")
    content = out.read_text(encoding="utf-8")
    assert content.startswith("<svg")
    assert "stroke-dasharray" in content  # the unclamped-R_n series is dashed


def test_render_score_distribution_svg_handles_not_measured_groups(tmp_path):
    distributions = {
        "0.05": {"train_e1": {"p5": 0.1, "p25": 0.3, "median": 0.5, "p75": 0.7, "p95": 0.9}},
        "0.10": {"train_e1": "NOT MEASURED"},
    }
    out = render_score_distribution_svg(distributions, tmp_path / "plotd.svg")
    content = out.read_text(encoding="utf-8")
    assert content.startswith("<svg")
    assert "NOT MEASURED" in content
