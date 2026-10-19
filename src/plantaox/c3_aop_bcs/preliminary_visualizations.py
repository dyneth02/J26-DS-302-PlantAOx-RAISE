"""Dependency-free PP1 pilot visualizations for Task 3.34."""

from __future__ import annotations

from collections import Counter
import csv
from datetime import date
from html import escape
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from .delta_score import DELTA_SCORE_FIELDS, DEFAULT_OUTPUT_PATH as DEFAULT_DELTA_PATH
from .manual_variant_inspection import DEFAULT_REPORT_PATH as DEFAULT_EXAMPLE_PATH
from .invariance_rate import DEFAULT_REPORT_PATH as DEFAULT_IR_PATH
from .false_sensitivity_rate import DEFAULT_REPORT_PATH as DEFAULT_FSR_PATH
from .preliminary_bcs import DEFAULT_REPORT_PATH as DEFAULT_BCS_PATH
from .prediction_flip import DEFAULT_REPORT_PATH as DEFAULT_PFR_PATH
from .standardization import REPOSITORY_ROOT


VISUALIZATION_SCHEMA_VERSION = "1.0"
VISUALIZATION_VERSION = "c3_aop_bcs_pp1_preliminary_visualizations_v1"
WARNING = "PP1 PILOT - DUMMY SOFTWARE TEST ONLY - NOT SCIENTIFIC RESULTS"
TYPE_COLORS = {"P1": "#D55E00", "P2": "#0072B2", "P3": "#009E73"}
TEXT_COLOR = "#172033"
MUTED_COLOR = "#5F6B7A"
GRID_COLOR = "#D8DEE8"
FRAME_COLOR = "#9AA6B5"
BACKGROUND_COLOR = "#FFFFFF"
WARNING_BACKGROUND = "#FFF4D6"
WARNING_COLOR = "#7A4D00"

DEFAULT_OUTPUT_DIRECTORY = (
    REPOSITORY_ROOT / "data" / "processed" / "c3_aop_bcs" / "figures"
)
DEFAULT_DISTRIBUTION_PATH = DEFAULT_OUTPUT_DIRECTORY / "pp1_pilot_absolute_delta_distributions_v1.svg"
DEFAULT_SCORE_EXAMPLES_PATH = DEFAULT_OUTPUT_DIRECTORY / "pp1_pilot_score_examples_v1.svg"
DEFAULT_METRIC_TABLE_PATH = DEFAULT_OUTPUT_DIRECTORY / "pp1_pilot_metric_summary_v1.svg"
DEFAULT_FLIP_COMPARISON_PATH = DEFAULT_OUTPUT_DIRECTORY / "pp1_pilot_prediction_flip_comparison_v1.svg"
DEFAULT_METRIC_DATA_PATH = DEFAULT_OUTPUT_DIRECTORY / "pp1_pilot_metric_summary_v1.csv"
DEFAULT_REPORT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "pp1_pilot_visualization_report_v1.json"
)

METRIC_DATA_FIELDS = ("metric", "value", "numerator", "denominator", "interpretation")


class PreliminaryVisualizationError(ValueError):
    """Raised when source data or generated visualizations fail validation."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display_path(path: Path) -> str:
    return (
        path.relative_to(REPOSITORY_ROOT).as_posix()
        if path.is_relative_to(REPOSITORY_ROOT)
        else str(path)
    )


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PreliminaryVisualizationError(f"could not read {label}: {path}") from exc
    if not isinstance(value, dict):
        raise PreliminaryVisualizationError(f"{label} must contain a JSON object")
    return value


def _read_delta_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if tuple(reader.fieldnames or ()) != DELTA_SCORE_FIELDS:
            raise PreliminaryVisualizationError("DeltaScore schema is invalid")
        rows = [dict(row) for row in reader]
    if not rows:
        raise PreliminaryVisualizationError("DeltaScore input is empty")
    return rows


def _svg_start(title: str, description: str, width: int = 1200, height: int = 720) -> list[str]:
    return [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}" role="img" '
            f'aria-labelledby="title desc">'
        ),
        f"<title id=\"title\">{escape(title)}</title>",
        f"<desc id=\"desc\">{escape(description)}</desc>",
        f'<rect width="{width}" height="{height}" fill="{BACKGROUND_COLOR}"/>',
        f'<text x="60" y="54" font-family="Arial, sans-serif" font-size="26" font-weight="700" fill="{TEXT_COLOR}">{escape(title)}</text>',
        f'<rect x="60" y="72" width="1080" height="34" rx="4" fill="{WARNING_BACKGROUND}"/>',
        f'<text x="600" y="95" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" font-weight="700" fill="{WARNING_COLOR}">{escape(WARNING)}</text>',
    ]


def _text(x: float, y: float, value: object, size: int = 13, anchor: str = "start", weight: int = 400, color: str = TEXT_COLOR) -> str:
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" text-anchor="{anchor}" '
        f'font-family="Arial, sans-serif" font-size="{size}" font-weight="{weight}" '
        f'fill="{color}">{escape(str(value))}</text>'
    )


def _finish_svg(lines: list[str], caption: str) -> str:
    lines.append(_text(60, 694, caption, 12, color=MUTED_COLOR))
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def _histogram(values: Sequence[float], edges: Sequence[float]) -> list[int]:
    counts = [0] * (len(edges) - 1)
    for value in values:
        index = min(int((value - edges[0]) / (edges[1] - edges[0])), len(counts) - 1)
        if index < 0:
            raise PreliminaryVisualizationError("absolute DeltaScore cannot be negative")
        counts[index] += 1
    return counts


def render_delta_distributions(rows: Sequence[Mapping[str, str]]) -> str:
    """Render shared-scale P1/P2/P3 absolute DeltaScore histograms."""

    values = {
        kind: [
            float(row["absolute_delta_score"])
            for row in rows
            if row["perturbation_type"] == kind
        ]
        for kind in ("P1", "P2", "P3")
    }
    if any(not group for group in values.values()):
        raise PreliminaryVisualizationError("all three perturbation types require values")
    edges = [index * 0.05 for index in range(11)]
    histograms = {kind: _histogram(group, edges) for kind, group in values.items()}
    percentages = {
        kind: [count / len(values[kind]) * 100.0 for count in counts]
        for kind, counts in histograms.items()
    }
    y_max = max(max(group) for group in percentages.values())
    y_ceiling = max(10.0, math.ceil(y_max / 10.0) * 10.0)
    lines = _svg_start(
        "Absolute DeltaScore distributions by perturbation type",
        "Three shared-scale histograms show pilot absolute score changes for P1, P2, and P3.",
    )
    plot_top, plot_bottom = 150.0, 590.0
    panel_width, panel_gap = 330.0, 35.0
    left_start = 75.0
    for panel_index, kind in enumerate(("P1", "P2", "P3")):
        left = left_start + panel_index * (panel_width + panel_gap)
        right = left + panel_width
        lines.append(_text((left + right) / 2, 136, f"{kind} (n={len(values[kind])})", 16, "middle", 700, TYPE_COLORS[kind]))
        lines.append(f'<rect x="{left}" y="{plot_top}" width="{panel_width}" height="{plot_bottom - plot_top}" fill="none" stroke="{FRAME_COLOR}"/>')
        for tick in range(0, int(y_ceiling) + 1, 10):
            y = plot_bottom - (tick / y_ceiling) * (plot_bottom - plot_top)
            lines.append(f'<line x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}" stroke="{GRID_COLOR}" stroke-width="1"/>')
            if panel_index == 0:
                lines.append(_text(left - 9, y + 4, tick, 11, "end", color=MUTED_COLOR))
        bin_width = panel_width / 10
        for index, percentage in enumerate(percentages[kind]):
            bar_height = (percentage / y_ceiling) * (plot_bottom - plot_top)
            x = left + index * bin_width + 2
            y = plot_bottom - bar_height
            lines.append(f'<rect x="{x:.2f}" y="{y:.2f}" width="{bin_width - 4:.2f}" height="{bar_height:.2f}" fill="{TYPE_COLORS[kind]}" opacity="0.86"/>')
        for tick_index in (0, 2, 4, 6, 8, 10):
            x = left + tick_index / 10 * panel_width
            lines.append(_text(x, plot_bottom + 22, f"{edges[tick_index]:.1f}", 11, "middle", color=MUTED_COLOR))
        threshold_x = left + 0.05 / 0.5 * panel_width
        lines.append(f'<line x1="{threshold_x:.2f}" y1="{plot_top}" x2="{threshold_x:.2f}" y2="{plot_bottom}" stroke="#8B5CF6" stroke-width="2" stroke-dasharray="6 5"/>')
    lines.append(_text(600, 645, "Absolute DeltaScore |original - perturbed|", 14, "middle", 600))
    lines.append(f'<text x="22" y="370" transform="rotate(-90 22 370)" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" font-weight="600" fill="{TEXT_COLOR}">Percentage of edits (%)</text>')
    lines.append(_text(600, 670, "Dashed line: primary delta = 0.05", 12, "middle", color="#6D28D9"))
    return _finish_svg(lines, "Source: 449 generated PP1 pilot perturbations (P1=54, P2=150, P3=245).")


def render_score_examples(examples: Sequence[Mapping[str, Any]]) -> str:
    """Render original-versus-perturbed scores for inspected examples."""

    lines = _svg_start(
        "Original vs perturbed scores - inspected examples",
        "Scatter plot of six manually inspected dummy-score examples with a no-change diagonal.",
    )
    left, right, top, bottom = 150.0, 1040.0, 145.0, 600.0
    lines.append(f'<rect x="{left}" y="{top}" width="{right-left}" height="{bottom-top}" fill="none" stroke="{FRAME_COLOR}"/>')
    for tick_index in range(6):
        value = tick_index / 5
        x = left + value * (right - left)
        y = bottom - value * (bottom - top)
        lines.append(f'<line x1="{x:.2f}" y1="{top}" x2="{x:.2f}" y2="{bottom}" stroke="{GRID_COLOR}"/>')
        lines.append(f'<line x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}" stroke="{GRID_COLOR}"/>')
        lines.append(_text(x, bottom + 22, f"{value:.1f}", 11, "middle", color=MUTED_COLOR))
        lines.append(_text(left - 12, y + 4, f"{value:.1f}", 11, "end", color=MUTED_COLOR))
    lines.append(f'<line x1="{left}" y1="{bottom}" x2="{right}" y2="{top}" stroke="{MUTED_COLOR}" stroke-width="2" stroke-dasharray="8 6"/>')
    lines.append(_text(right - 8, top + 20, "no change", 12, "end", color=MUTED_COLOR))
    type_number = Counter()
    for example in examples:
        kind = str(example["perturbation_type"])
        type_number[kind] += 1
        label = f"{kind}-{type_number[kind]}"
        x = left + float(example["original_score"]) * (right - left)
        y = bottom - float(example["perturbed_score"]) * (bottom - top)
        lines.append(f'<circle cx="{x:.2f}" cy="{y:.2f}" r="9" fill="{TYPE_COLORS[kind]}" stroke="#FFFFFF" stroke-width="2"/>')
        label_y = y - 13 if type_number[kind] == 1 else y + 24
        lines.append(_text(x, label_y, f"{label}: {example['mutation']}", 12, "middle", 700, TYPE_COLORS[kind]))
    lines.append(_text(595, 645, "Original usable score", 14, "middle", 600))
    lines.append(f'<text x="48" y="372" transform="rotate(-90 48 372)" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" font-weight="600" fill="{TEXT_COLOR}">Perturbed usable score</text>')
    legend_x = 770
    for index, kind in enumerate(("P1", "P2", "P3")):
        x = legend_x + index * 105
        lines.append(f'<circle cx="{x}" cy="127" r="6" fill="{TYPE_COLORS[kind]}"/>')
        lines.append(_text(x + 12, 132, kind, 12, weight=700))
    return _finish_svg(lines, "Six examples from the Task 3.33 inspection evidence; diagonal indicates unchanged score.")


def _metric_rows(ir_report: Mapping[str, Any], fsr_report: Mapping[str, Any], bcs_report: Mapping[str, Any]) -> list[dict[str, str]]:
    return [
        {
            "metric": "IR",
            "value": repr(ir_report["result"]["invariance_rate"]),
            "numerator": str(ir_report["result"]["invariant_p2_count"]),
            "denominator": str(ir_report["result"]["evaluated_p2_count"]),
            "interpretation": "P2 edits with |DeltaScore| < 0.05",
        },
        {
            "metric": "FSR",
            "value": repr(fsr_report["result"]["false_sensitivity_rate"]),
            "numerator": str(fsr_report["result"]["insufficient_response_p1_count"]),
            "denominator": str(fsr_report["result"]["evaluated_p1_count"]),
            "interpretation": "P1 edits with |DeltaScore| < 0.05",
        },
        {
            "metric": "BCS",
            "value": repr(bcs_report["result"]["preliminary_bcs"]),
            "numerator": "",
            "denominator": "",
            "interpretation": "IR x (1 - FSR)",
        },
    ]


def render_metric_summary(metric_rows: Sequence[Mapping[str, str]]) -> str:
    """Render the requested IR/FSR/BCS pilot summary table."""

    lines = _svg_start(
        "Preliminary IR, FSR and BCS summary",
        "Table and aligned bars summarize the primary delta 0.05 dummy-pipeline metrics.",
    )
    columns = (80, 250, 470, 690, 850, 1120)
    headers = ("Metric", "Value", "Count", "Meaning")
    lines.append(f'<rect x="80" y="150" width="1040" height="54" fill="#EEF2F7"/>')
    lines.append(_text(105, 184, headers[0], 14, weight=700))
    lines.append(_text(290, 184, headers[1], 14, weight=700))
    lines.append(_text(510, 184, headers[2], 14, weight=700))
    lines.append(_text(720, 184, headers[3], 14, weight=700))
    for index, row in enumerate(metric_rows):
        y_top = 204 + index * 112
        y_mid = y_top + 43
        value = float(row["value"])
        lines.append(f'<rect x="80" y="{y_top}" width="1040" height="112" fill="{BACKGROUND_COLOR}" stroke="{GRID_COLOR}"/>')
        lines.append(_text(105, y_mid, row["metric"], 20, weight=700, color="#5B3FD6"))
        lines.append(_text(290, y_mid, f"{value:.4f}", 18, weight=700))
        count = f"{row['numerator']}/{row['denominator']}" if row["numerator"] else "composite"
        lines.append(_text(510, y_mid, count, 15, weight=600))
        lines.append(_text(720, y_mid, row["interpretation"], 13, color=MUTED_COLOR))
        bar_x, bar_y, bar_width = 290, y_mid + 18, 300
        lines.append(f'<rect x="{bar_x}" y="{bar_y}" width="{bar_width}" height="14" rx="3" fill="#E5EAF1"/>')
        lines.append(f'<rect x="{bar_x}" y="{bar_y}" width="{bar_width * value:.2f}" height="14" rx="3" fill="#5B3FD6"/>')
    lines.append(_text(80, 585, "Primary threshold: delta = 0.05", 14, weight=700))
    lines.append(_text(80, 615, "BCS formula: IR x (1 - FSR) = 0.4494", 14, weight=700))
    return _finish_svg(lines, "Higher IR and BCS are preferable; lower FSR is preferable. Do not interpret dummy values scientifically.")


def render_flip_comparison(pfr_report: Mapping[str, Any]) -> str:
    """Render P1/P2/P3 prediction-flip rate comparison bars."""

    groups = pfr_report["pfr"]["by_perturbation_type"]
    lines = _svg_start(
        "Prediction-flip comparison by perturbation type",
        "Bar chart compares pilot prediction flip rates for P1, P2, and P3.",
    )
    left, right, top, bottom = 170.0, 1080.0, 155.0, 590.0
    y_ceiling = 0.25
    lines.append(f'<rect x="{left}" y="{top}" width="{right-left}" height="{bottom-top}" fill="none" stroke="{FRAME_COLOR}"/>')
    for tick_index in range(6):
        value = tick_index * 0.05
        y = bottom - value / y_ceiling * (bottom - top)
        lines.append(f'<line x1="{left}" y1="{y:.2f}" x2="{right}" y2="{y:.2f}" stroke="{GRID_COLOR}"/>')
        lines.append(_text(left - 12, y + 4, f"{value:.2f}", 11, "end", color=MUTED_COLOR))
    centers = (340.0, 625.0, 910.0)
    for center, kind in zip(centers, ("P1", "P2", "P3")):
        group = groups[kind]
        rate = float(group["prediction_flip_rate"])
        height = rate / y_ceiling * (bottom - top)
        y = bottom - height
        lines.append(f'<rect x="{center-70:.2f}" y="{y:.2f}" width="140" height="{height:.2f}" rx="4" fill="{TYPE_COLORS[kind]}"/>')
        lines.append(_text(center, y - 16, f"{rate:.3f}", 17, "middle", 700, TYPE_COLORS[kind]))
        lines.append(_text(center, y + 25, f"{group['flip_count']} flips", 13, "middle", 700, "#FFFFFF"))
        lines.append(_text(center, bottom + 31, kind, 16, "middle", 700))
        lines.append(_text(center, bottom + 52, f"{group['flip_count']}/{group['perturbation_count']} edits", 12, "middle", color=MUTED_COLOR))
    lines.append(f'<text x="50" y="370" transform="rotate(-90 50 370)" text-anchor="middle" font-family="Arial, sans-serif" font-size="14" font-weight="600" fill="{TEXT_COLOR}">Prediction Flip Rate</text>')
    return _finish_svg(lines, "Decision threshold = 0.5 for the dummy predictor only; real predictors require their own verified rule.")


def _write_text(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8", newline="\n")


def _write_metric_data(path: Path, rows: Sequence[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=METRIC_DATA_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: row[field] for field in METRIC_DATA_FIELDS} for row in rows)


def build_preliminary_visualizations(
    delta_path: str | Path = DEFAULT_DELTA_PATH,
    example_path: str | Path = DEFAULT_EXAMPLE_PATH,
    ir_path: str | Path = DEFAULT_IR_PATH,
    fsr_path: str | Path = DEFAULT_FSR_PATH,
    bcs_path: str | Path = DEFAULT_BCS_PATH,
    pfr_path: str | Path = DEFAULT_PFR_PATH,
    output_directory: str | Path = DEFAULT_OUTPUT_DIRECTORY,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    created_on: date | None = None,
) -> dict[str, Any]:
    """Generate four PP1-ready figures and their traceability manifest."""

    delta_source, example_source = Path(delta_path), Path(example_path)
    ir_source, fsr_source, bcs_source, pfr_source = map(
        Path, (ir_path, fsr_path, bcs_path, pfr_path)
    )
    output_dir = Path(output_directory)
    report_output = Path(report_path)
    delta_rows = _read_delta_rows(delta_source)
    example_report = _read_json(example_source, "manual example report")
    ir_report = _read_json(ir_source, "IR report")
    fsr_report = _read_json(fsr_source, "FSR report")
    bcs_report = _read_json(bcs_source, "BCS report")
    pfr_report = _read_json(pfr_source, "PFR report")
    source_reports = (example_report, ir_report, fsr_report, bcs_report, pfr_report)
    if any(report["validation"]["status"] != "PASS" for report in source_reports):
        raise PreliminaryVisualizationError("a source report did not pass validation")
    if any(row["software_testing_only"] != "true" for row in delta_rows):
        raise PreliminaryVisualizationError("DeltaScore rows lost testing-only status")

    paths = {
        "absolute_delta_distributions": output_dir / DEFAULT_DISTRIBUTION_PATH.name,
        "original_vs_perturbed_examples": output_dir / DEFAULT_SCORE_EXAMPLES_PATH.name,
        "metric_summary_table": output_dir / DEFAULT_METRIC_TABLE_PATH.name,
        "prediction_flip_comparison": output_dir / DEFAULT_FLIP_COMPARISON_PATH.name,
        "metric_summary_data": output_dir / DEFAULT_METRIC_DATA_PATH.name,
    }
    metric_rows = _metric_rows(ir_report, fsr_report, bcs_report)
    _write_text(paths["absolute_delta_distributions"], render_delta_distributions(delta_rows))
    _write_text(paths["original_vs_perturbed_examples"], render_score_examples(example_report["examples"]))
    _write_text(paths["metric_summary_table"], render_metric_summary(metric_rows))
    _write_text(paths["prediction_flip_comparison"], render_flip_comparison(pfr_report))
    _write_metric_data(paths["metric_summary_data"], metric_rows)

    sources = {
        "delta_scores": delta_source,
        "manual_examples": example_source,
        "invariance_rate": ir_source,
        "false_sensitivity_rate": fsr_source,
        "preliminary_bcs": bcs_source,
        "prediction_flips": pfr_source,
    }
    type_counts = Counter(row["perturbation_type"] for row in delta_rows)
    report: dict[str, Any] = {
        "schema_version": VISUALIZATION_SCHEMA_VERSION,
        "visualization_version": VISUALIZATION_VERSION,
        "created_on": (created_on or date.today()).isoformat(),
        "classification": {
            "pilot_preliminary": True,
            "software_testing_only": True,
            "scientific_result": False,
            "visible_warning": WARNING,
        },
        "sources": {
            label: {"path": _display_path(path), "sha256": _sha256(path)}
            for label, path in sources.items()
        },
        "data_summary": {
            "delta_score_record_count": len(delta_rows),
            "perturbation_counts": {
                kind: type_counts[kind] for kind in ("P1", "P2", "P3")
            },
            "inspected_example_count": len(example_report["examples"]),
            "primary_delta": ir_report["definition"]["delta"],
            "invariance_rate": ir_report["result"]["invariance_rate"],
            "false_sensitivity_rate": fsr_report["result"]["false_sensitivity_rate"],
            "preliminary_bcs": bcs_report["result"]["preliminary_bcs"],
            "prediction_flip_rates": {
                kind: pfr_report["pfr"]["by_perturbation_type"][kind]["prediction_flip_rate"]
                for kind in ("P1", "P2", "P3")
            },
        },
        "outputs": {
            label: {
                "path": _display_path(path),
                "format": path.suffix.lstrip("."),
                "sha256": _sha256(path),
            }
            for label, path in paths.items()
        },
        "validation": {
            "status": "PASS",
            "all_requested_visualizations_created": all(path.exists() for path in paths.values()),
            "only_generated_results_used": True,
            "all_figures_visibly_labelled_preliminary": all(
                WARNING in path.read_text(encoding="utf-8")
                for label, path in paths.items()
                if label != "metric_summary_data"
            ),
            "all_sources_passed_validation": True,
            "software_testing_only_preserved": True,
            "not_a_scientific_result": True,
        },
    }
    if not all(value for key, value in report["validation"].items() if key != "status"):
        raise PreliminaryVisualizationError("preliminary visualizations failed validation")
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


if __name__ == "__main__":
    generated = build_preliminary_visualizations()
    print(
        f"Generated {len(generated['outputs']) - 1} preliminary PP1 figures "
        "plus one metric data table."
    )
