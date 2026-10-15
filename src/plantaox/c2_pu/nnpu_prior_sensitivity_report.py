"""Bucket 4, Task 4.3 POST-ACCEPTANCE DIAGNOSTIC -- comparison-table and
lightweight-SVG assembly for the pi in {0.05, 0.10, 0.20} sensitivity
investigation.

Pure data-shaping + hand-rolled SVG rendering (no new dependency, same
"no matplotlib" precedent already established project-wide -- see
``pn_baseline.render_loss_curve_svg``'s own docstring/decision-log entry).
Every function here operates on REAL numbers already computed by
``nnpu_prior_diagnostics.py`` or read from the accepted Task 4.3 summary
-- nothing in this module invents, estimates, or interpolates a result
that was not actually measured. Where a value genuinely is not available
(e.g. the accepted pi=0.10 run's best checkpoint is missing), the
caller must pass the literal string ``"NOT MEASURED"`` rather than this
module silently defaulting to 0/None in a way that could be misread as
a real measurement.
"""

from __future__ import annotations

from pathlib import Path

_COLORS = {"0.05": "#2ca02c", "0.10": "#1f77b4", "0.20": "#d62728"}
_GROUP_ORDER = ("train_e1", "train_e2", "train_c1", "val_e1", "val_e2", "val_c1")


def _prior_key(prior: float) -> str:
    return f"{prior:.2f}"


def render_multi_series_line_svg(
    series_by_prior: dict[str, list[tuple[int, float]]],
    path: Path,
    title: str,
    y_label: str,
    zero_reference_line: bool = False,
) -> Path:
    """A minimal multi-series SVG line chart (one polyline per prior),
    generalizing ``pn_baseline.render_loss_curve_svg``'s single-pair
    (train/validation) convention to an arbitrary number of named series
    -- used for Plots A/B/C (Section 8), each of which needs one series
    per prior rather than a fixed train-vs-validation pair.
    """
    width, height, pad = 720, 420, 56
    all_points = [pt for pts in series_by_prior.values() for pt in pts]
    if not all_points:
        raise ValueError("render_multi_series_line_svg: no data points given.")
    epochs = [p[0] for p in all_points]
    values = [p[1] for p in all_points]
    if zero_reference_line:
        values = values + [0.0]
    min_v, max_v = min(values), max(values)
    v_range = max(max_v - min_v, 1e-9)
    min_e, max_e = min(epochs), max(epochs)
    e_range = max(max_e - min_e, 1)

    def _x(epoch: int) -> float:
        return pad + (epoch - min_e) / e_range * (width - 2 * pad)

    def _y(value: float) -> float:
        return height - pad - (value - min_v) / v_range * (height - 2 * pad)

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="white"/>',
        f'<line x1="{pad}" y1="{height - pad}" x2="{width - pad}" y2="{height - pad}" stroke="black"/>',
        f'<line x1="{pad}" y1="{pad}" x2="{pad}" y2="{height - pad}" stroke="black"/>',
        f'<text x="{pad}" y="20" font-size="14">{title}</text>',
        f'<text x="{pad}" y="{height - 10}" font-size="11">epoch</text>',
        f'<text x="4" y="{pad}" font-size="11">{y_label}</text>',
    ]
    if zero_reference_line:
        svg.append(
            f'<line x1="{pad}" y1="{_y(0.0):.2f}" x2="{width - pad}" y2="{_y(0.0):.2f}" '
            f'stroke="#888" stroke-width="1" stroke-dasharray="4,3"/>'
        )
        svg.append(f'<text x="{width - pad - 70}" y="{_y(0.0) - 4:.2f}" font-size="10" fill="#888">R_n = 0</text>')

    legend_y = pad
    for prior_label, points in sorted(series_by_prior.items()):
        color = _COLORS.get(prior_label, "#333333")
        points_sorted = sorted(points, key=lambda p: p[0])
        poly = " ".join(f"{_x(e):.2f},{_y(v):.2f}" for e, v in points_sorted)
        svg.append(f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2"/>')
        svg.append(f'<rect x="{width - pad - 16}" y="{legend_y}" width="10" height="10" fill="{color}"/>')
        svg.append(f'<text x="{width - pad + 0}" y="{legend_y + 9}" font-size="10">pi={prior_label}</text>')
        legend_y += 14
    svg.append("</svg>")

    path = Path(path)
    path.write_text("\n".join(svg), encoding="utf-8", newline="\n")
    return path


def render_dual_component_svg(
    positive_series_by_prior: dict[str, list[tuple[int, float]]],
    negative_series_by_prior: dict[str, list[tuple[int, float]]],
    path: Path,
    title: str,
) -> Path:
    """Plot C: positive-risk contribution (solid) vs. unclamped
    negative-risk (dashed) per epoch, one color per prior -- explicitly
    two distinct line styles so the raw risk COMPONENTS are visually
    distinguishable from each other (Section 8's own requirement), not
    just distinguishable by color/prior.
    """
    width, height, pad = 720, 420, 56
    all_points = [pt for pts in list(positive_series_by_prior.values()) + list(negative_series_by_prior.values()) for pt in pts]
    if not all_points:
        raise ValueError("render_dual_component_svg: no data points given.")
    epochs = [p[0] for p in all_points]
    values = [p[1] for p in all_points]
    min_v, max_v = min(values), max(values)
    v_range = max(max_v - min_v, 1e-9)
    min_e, max_e = min(epochs), max(epochs)
    e_range = max(max_e - min_e, 1)

    def _x(epoch: int) -> float:
        return pad + (epoch - min_e) / e_range * (width - 2 * pad)

    def _y(value: float) -> float:
        return height - pad - (value - min_v) / v_range * (height - 2 * pad)

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="white"/>',
        f'<line x1="{pad}" y1="{height - pad}" x2="{width - pad}" y2="{height - pad}" stroke="black"/>',
        f'<line x1="{pad}" y1="{pad}" x2="{pad}" y2="{height - pad}" stroke="black"/>',
        f'<text x="{pad}" y="20" font-size="14">{title}</text>',
        f'<text x="{pad}" y="{height - 10}" font-size="11">epoch</text>',
        f'<text x="4" y="{pad}" font-size="11">risk</text>',
        f'<text x="{pad}" y="36" font-size="10">solid = pi*R_p^+ (positive-risk contribution); dashed = unclamped R_n</text>',
    ]
    legend_y = pad
    for prior_label in sorted(set(positive_series_by_prior) | set(negative_series_by_prior)):
        color = _COLORS.get(prior_label, "#333333")
        if prior_label in positive_series_by_prior:
            pts = sorted(positive_series_by_prior[prior_label], key=lambda p: p[0])
            poly = " ".join(f"{_x(e):.2f},{_y(v):.2f}" for e, v in pts)
            svg.append(f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2"/>')
        if prior_label in negative_series_by_prior:
            pts = sorted(negative_series_by_prior[prior_label], key=lambda p: p[0])
            poly = " ".join(f"{_x(e):.2f},{_y(v):.2f}" for e, v in pts)
            svg.append(f'<polyline points="{poly}" fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="6,4"/>')
        svg.append(f'<rect x="{width - pad - 16}" y="{legend_y}" width="10" height="10" fill="{color}"/>')
        svg.append(f'<text x="{width - pad + 0}" y="{legend_y + 9}" font-size="10">pi={prior_label}</text>')
        legend_y += 14
    svg.append("</svg>")

    path = Path(path)
    path.write_text("\n".join(svg), encoding="utf-8", newline="\n")
    return path


def render_score_distribution_svg(
    distributions_by_prior: dict[str, dict], path: Path, title: str = "Best-checkpoint score distributions (E1/E2/C1)"
) -> Path:
    """Plot D: one box (p25-p75, median tick, p5-p95 whiskers) per
    (group, prior) -- ``distributions_by_prior`` is
    ``{prior_label: {group_name: stats_dict_or_'NOT MEASURED'}}``, where
    ``stats_dict`` is ``prediction_saturation_summary``'s own output.
    Groups missing/`"NOT MEASURED"` are skipped with a labeled gap, never
    silently rendered as zero.
    """
    width = 900
    height = 420
    pad_left, pad_bottom, pad_top = 60, 70, 40
    plot_w = width - pad_left - 40
    plot_h = height - pad_top - pad_bottom

    priors = sorted(distributions_by_prior.keys())
    n_groups = len(_GROUP_ORDER)
    n_priors = len(priors)
    slot_w = plot_w / max(n_groups, 1)
    box_w = slot_w / max(n_priors + 1, 2)

    def _y(value: float) -> float:
        return pad_top + plot_h - value * plot_h  # value in [0, 1]

    svg = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<rect width="{width}" height="{height}" fill="white"/>',
        f'<line x1="{pad_left}" y1="{pad_top + plot_h:.2f}" x2="{pad_left + plot_w:.2f}" y2="{pad_top + plot_h:.2f}" stroke="black"/>',
        f'<line x1="{pad_left}" y1="{pad_top}" x2="{pad_left}" y2="{pad_top + plot_h:.2f}" stroke="black"/>',
        f'<text x="{pad_left}" y="20" font-size="14">{title}</text>',
        f'<text x="4" y="{pad_top}" font-size="10">score=1.0</text>',
        f'<text x="4" y="{pad_top + plot_h:.0f}" font-size="10">score=0.0</text>',
    ]

    for gi, group in enumerate(_GROUP_ORDER):
        group_x0 = pad_left + gi * slot_w
        svg.append(
            f'<text x="{group_x0 + slot_w / 2:.2f}" y="{pad_top + plot_h + 16:.0f}" '
            f'font-size="10" text-anchor="middle">{group}</text>'
        )
        for pi_idx, prior_label in enumerate(priors):
            stats = distributions_by_prior[prior_label].get(group)
            cx = group_x0 + (pi_idx + 0.75) * box_w
            color = _COLORS.get(prior_label, "#333333")
            if not isinstance(stats, dict) or "p25" not in stats:
                svg.append(
                    f'<text x="{cx:.2f}" y="{pad_top + plot_h / 2:.0f}" font-size="8" '
                    f'text-anchor="middle" fill="#999" transform="rotate(90 {cx:.2f},{pad_top + plot_h / 2:.0f})">'
                    f"NOT MEASURED</text>"
                )
                continue
            y_p5, y_p25, y_p75, y_p95, y_med = (
                _y(stats["p5"]), _y(stats["p25"]), _y(stats["p75"]), _y(stats["p95"]), _y(stats["median"]),
            )
            half = box_w * 0.3
            svg.append(f'<line x1="{cx:.2f}" y1="{y_p5:.2f}" x2="{cx:.2f}" y2="{y_p25:.2f}" stroke="{color}"/>')
            svg.append(f'<line x1="{cx:.2f}" y1="{y_p75:.2f}" x2="{cx:.2f}" y2="{y_p95:.2f}" stroke="{color}"/>')
            svg.append(
                f'<rect x="{cx - half:.2f}" y="{min(y_p25, y_p75):.2f}" width="{2 * half:.2f}" '
                f'height="{abs(y_p75 - y_p25):.2f}" fill="none" stroke="{color}" stroke-width="1.5"/>'
            )
            svg.append(f'<line x1="{cx - half:.2f}" y1="{y_med:.2f}" x2="{cx + half:.2f}" y2="{y_med:.2f}" stroke="{color}" stroke-width="2"/>')

    legend_y = pad_top
    for prior_label in priors:
        color = _COLORS.get(prior_label, "#333333")
        svg.append(f'<rect x="{width - 90}" y="{legend_y}" width="10" height="10" fill="none" stroke="{color}" stroke-width="2"/>')
        svg.append(f'<text x="{width - 75}" y="{legend_y + 9}" font-size="10">pi={prior_label}</text>')
        legend_y += 14
    svg.append("</svg>")

    path = Path(path)
    path.write_text("\n".join(svg), encoding="utf-8", newline="\n")
    return path


def build_comparison_table(prior_rows: dict[str, dict]) -> dict:
    """Assembles Section 9's comparison table. ``prior_rows`` maps a
    prior label ("0.05"/"0.10"/"0.20") to a dict with whatever of the
    following keys are actually available:
    ``executed_epochs``, ``best_epoch``, ``best_val_nnpu_risk``,
    ``mean_clamped_update_fraction``, ``final_five_epoch_clamped_fraction``,
    ``mean_train_negative_risk``, ``mean_val_negative_risk``,
    ``e1_median_score``, ``e2_median_score``, ``c1_median_score``,
    ``score_saturation_note``. Missing keys are rendered as the literal
    string "NOT MEASURED" -- never a fabricated number.
    """
    fields = [
        "executed_epochs", "best_epoch", "best_val_nnpu_risk", "mean_clamped_update_fraction",
        "final_five_epoch_clamped_fraction", "mean_train_negative_risk", "mean_val_negative_risk",
        "e1_median_score", "e2_median_score", "c1_median_score", "score_saturation_note",
    ]
    table = {}
    for prior_label in sorted(prior_rows.keys()):
        row = prior_rows[prior_label]
        table[prior_label] = {field: row.get(field, "NOT MEASURED") for field in fields}
    return table


def classify_prior_sensitivity(mean_clamped_fraction_by_prior: dict[str, float], threshold: float = 0.05) -> str:
    """Section 7/11's required classification:
    'Prior-sensitive' / 'Persistently clamped' / 'Mixed behavior' /
    'Inconclusive'. A purely descriptive, threshold-based rule over the
    REAL measured mean clamped-update fractions -- not a judgment this
    function is meant to overrule; the accompanying report must still
    state the numbers and let a human confirm the label is defensible.

    Rule: if every available prior's mean clamped fraction is >= (1 -
    threshold), clamping is 'Persistently clamped' (near-universal
    regardless of pi). If the SPREAD across priors exceeds `threshold`
    (i.e. at least one prior differs non-trivially from the others),
    it is 'Prior-sensitive'. If results are mixed/inconsistent (e.g. a
    non-monotonic pattern with a large spread but no prior reaching a
    low clamped fraction), 'Mixed behavior'. If fewer than 2 priors have
    real measurements, 'Inconclusive'.
    """
    values = {k: v for k, v in mean_clamped_fraction_by_prior.items() if isinstance(v, (int, float))}
    if len(values) < 2:
        return "Inconclusive"
    lo, hi = min(values.values()), max(values.values())
    spread = hi - lo
    all_near_universal = all(v >= (1.0 - threshold) for v in values.values())
    if all_near_universal and spread < threshold:
        return "Persistently clamped"
    if spread >= threshold and not all_near_universal:
        return "Prior-sensitive"
    if spread >= threshold and all_near_universal:
        return "Mixed behavior"
    return "Mixed behavior"
