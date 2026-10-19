"""Configurable delta-sensitivity analysis for Task 3.31."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
import math
from numbers import Real
from pathlib import Path
from typing import Any, Mapping, Sequence

from .config import ResearchConfig, load_research_config
from .delta_score import DELTA_SCORE_DATASET_VERSION, DELTA_SCORE_FIELDS
from .false_sensitivity_rate import (
    false_sensitivity_rate,
    is_insufficient_response,
)
from .invariance_rate import invariance_rate, is_invariant
from .preliminary_bcs import calculate_bcs
from .standardization import REPOSITORY_ROOT


DELTA_SENSITIVITY_SCHEMA_VERSION = "1.0"
DELTA_SENSITIVITY_PIPELINE_VERSION = "c3_aop_bcs_delta_sensitivity_v1"
DELTA_SENSITIVITY_REPORT_VERSION = "c3_aop_bcs_pp1_pilot_dummy_delta_sensitivity_v1"

DEFAULT_INPUT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "pp1_pilot_dummy_delta_scores_v1.csv"
)
DEFAULT_REPORT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "pp1_pilot_dummy_delta_sensitivity_report_v1.json"
)


class DeltaSensitivityError(ValueError):
    """Raised when sensitivity inputs violate the configured metric contract."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display_path(path: Path) -> str:
    return (
        path.relative_to(REPOSITORY_ROOT).as_posix()
        if path.is_relative_to(REPOSITORY_ROOT)
        else str(path)
    )


def _validated_delta(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise DeltaSensitivityError(f"{label} must be numeric")
    delta = float(value)
    if not math.isfinite(delta) or not 0.0 < delta < 1.0:
        raise DeltaSensitivityError(f"{label} must be finite and within (0,1)")
    return delta


def _validated_thresholds(
    deltas: Sequence[object],
    primary_delta: object,
) -> tuple[tuple[float, ...], float]:
    if not deltas:
        raise DeltaSensitivityError("at least one sensitivity delta is required")
    thresholds = tuple(
        _validated_delta(value, f"sensitivity_deltas[{index}]")
        for index, value in enumerate(deltas)
    )
    if len(set(thresholds)) != len(thresholds):
        raise DeltaSensitivityError("sensitivity deltas must not contain duplicates")
    if thresholds != tuple(sorted(thresholds)):
        raise DeltaSensitivityError("sensitivity deltas must be in ascending order")
    primary = _validated_delta(primary_delta, "primary_delta")
    if primary not in thresholds:
        raise DeltaSensitivityError("primary delta must be included in sensitivity deltas")
    return thresholds, primary


def _read_delta_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if tuple(reader.fieldnames or ()) != DELTA_SCORE_FIELDS:
            raise DeltaSensitivityError("DeltaScore input schema is invalid")
        rows = [dict(row) for row in reader]
    if not rows:
        raise DeltaSensitivityError("DeltaScore input is empty")
    identifiers = [row["variant_id"] for row in rows]
    if len(identifiers) != len(set(identifiers)):
        raise DeltaSensitivityError("DeltaScore input has duplicate variant identifiers")
    return rows


def _extract_magnitudes(
    rows: Sequence[Mapping[str, str]],
) -> tuple[list[float], list[float]]:
    p1_magnitudes: list[float] = []
    p2_magnitudes: list[float] = []
    predictor_metadata: tuple[str, ...] | None = None
    metadata_fields = (
        "predictor_id",
        "predictor_version",
        "scoring_method",
        "software_testing_only",
        "score_contract_id",
        "normalization_mapping",
    )
    for row in rows:
        current_metadata = tuple(row[field] for field in metadata_fields)
        if predictor_metadata is None:
            predictor_metadata = current_metadata
        elif current_metadata != predictor_metadata:
            raise DeltaSensitivityError("input mixes predictor or score metadata")
        if row["perturbation_type"] not in {"P1", "P2"}:
            continue
        try:
            magnitude = float(row["absolute_delta_score"])
        except ValueError as exc:
            raise DeltaSensitivityError(
                f"{row['variant_id']} contains a non-numeric absolute DeltaScore"
            ) from exc
        if not math.isfinite(magnitude) or magnitude < 0.0:
            raise DeltaSensitivityError(
                f"{row['variant_id']} contains an invalid absolute DeltaScore"
            )
        if row["perturbation_type"] == "P1":
            p1_magnitudes.append(magnitude)
        else:
            p2_magnitudes.append(magnitude)
    if not p1_magnitudes:
        raise DeltaSensitivityError("DeltaScore input contains no P1 perturbations")
    if not p2_magnitudes:
        raise DeltaSensitivityError("DeltaScore input contains no P2 perturbations")
    return p1_magnitudes, p2_magnitudes


def calculate_delta_sensitivity(
    delta_rows: Sequence[Mapping[str, str]],
    deltas: Sequence[object],
    primary_delta: object,
) -> list[dict[str, Any]]:
    """Calculate IR, FSR, and BCS for every configured delta threshold."""

    thresholds, primary = _validated_thresholds(deltas, primary_delta)
    p1_magnitudes, p2_magnitudes = _extract_magnitudes(delta_rows)
    results: list[dict[str, Any]] = []
    for delta in thresholds:
        invariant_flags = [is_invariant(value, delta) for value in p2_magnitudes]
        insufficient_flags = [
            is_insufficient_response(value, delta) for value in p1_magnitudes
        ]
        ir = invariance_rate(invariant_flags)
        fsr = false_sensitivity_rate(insufficient_flags)
        bcs = calculate_bcs(ir, fsr)
        results.append(
            {
                "delta": delta,
                "is_primary": delta == primary,
                "p2_evaluated_count": len(p2_magnitudes),
                "p2_invariant_count": sum(invariant_flags),
                "invariance_rate": ir,
                "p1_evaluated_count": len(p1_magnitudes),
                "p1_insufficient_response_count": sum(insufficient_flags),
                "false_sensitivity_rate": fsr,
                "preliminary_bcs": bcs,
            }
        )
    return results


def build_delta_sensitivity_report(
    input_path: str | Path = DEFAULT_INPUT_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    config: ResearchConfig | None = None,
    created_on: date | None = None,
) -> dict[str, Any]:
    """Rerun pilot behavioural metrics over all configured sensitivity deltas."""

    active_config = config or load_research_config()
    source = Path(input_path)
    output = Path(report_path)
    rows = _read_delta_rows(source)
    results = calculate_delta_sensitivity(
        rows,
        active_config.sensitivity_deltas,
        active_config.primary_delta,
    )
    primary_results = [result for result in results if result["is_primary"]]
    predictor = rows[0]
    report: dict[str, Any] = {
        "schema_version": DELTA_SENSITIVITY_SCHEMA_VERSION,
        "pipeline_version": DELTA_SENSITIVITY_PIPELINE_VERSION,
        "report_version": DELTA_SENSITIVITY_REPORT_VERSION,
        "created_on": (created_on or date.today()).isoformat(),
        "source_dataset_version": DELTA_SCORE_DATASET_VERSION,
        "definition": {
            "configured_deltas": list(active_config.sensitivity_deltas),
            "primary_delta": active_config.primary_delta,
            "invariance_rule": "P2 absolute_delta_score < delta",
            "false_sensitivity_rule": "P1 absolute_delta_score < delta",
            "bcs_formula": "BCS = IR * (1 - FSR)",
            "boundary_rule": "absolute_delta_score == delta does not satisfy < delta",
            "interpretation_scope": (
                "PP1 demonstrates configurable reproducible reruns only; full "
                "robustness interpretation is reserved for the later study."
            ),
        },
        "predictor": {
            "predictor_id": predictor["predictor_id"],
            "display_name": predictor["predictor_display_name"],
            "version": predictor["predictor_version"],
            "scoring_method": predictor["scoring_method"],
            "software_testing_only": predictor["software_testing_only"] == "true",
            "scientific_result": False,
        },
        "source": {
            "path": _display_path(source),
            "record_count": len(rows),
            "p1_record_count": sum(row["perturbation_type"] == "P1" for row in rows),
            "p2_record_count": sum(row["perturbation_type"] == "P2" for row in rows),
            "sha256": _sha256(source),
        },
        "threshold_results": results,
        "validation": {
            "status": "PASS",
            "all_configured_thresholds_evaluated": (
                [result["delta"] for result in results]
                == list(active_config.sensitivity_deltas)
            ),
            "exactly_one_primary_result": len(primary_results) == 1,
            "primary_delta_is_0_05": active_config.primary_delta == 0.05,
            "all_rates_within_zero_to_one": all(
                0.0 <= result[metric] <= 1.0
                for result in results
                for metric in (
                    "invariance_rate",
                    "false_sensitivity_rate",
                    "preliminary_bcs",
                )
            ),
            "counts_reconcile": all(
                result["p2_invariant_count"] <= result["p2_evaluated_count"]
                and result["p1_insufficient_response_count"]
                <= result["p1_evaluated_count"]
                for result in results
            ),
            "software_testing_only_preserved": (
                predictor["software_testing_only"] == "true"
            ),
            "not_a_scientific_result": True,
        },
    }
    if not all(value for key, value in report["validation"].items() if key != "status"):
        raise DeltaSensitivityError("delta-sensitivity report failed validation")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


if __name__ == "__main__":
    generated = build_delta_sensitivity_report()
    print("Calculated software-only sensitivity metrics:")
    for values in generated["threshold_results"]:
        primary_label = " (primary)" if values["is_primary"] else ""
        print(
            f"delta={values['delta']:.2f}{primary_label}: "
            f"IR={values['invariance_rate']:.6f}, "
            f"FSR={values['false_sensitivity_rate']:.6f}, "
            f"BCS={values['preliminary_bcs']:.6f}"
        )
