"""P1 insufficient-response False Sensitivity Rate for Task 3.29."""

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
from .standardization import REPOSITORY_ROOT


FSR_SCHEMA_VERSION = "1.0"
FSR_PIPELINE_VERSION = "c3_aop_bcs_false_sensitivity_rate_v1"
FSR_DATASET_VERSION = "c3_aop_bcs_pp1_pilot_dummy_p1_insufficient_response_v1"
INSUFFICIENT_RESPONSE_COMPARATOR = "absolute_delta_score_strictly_less_than_delta"

DEFAULT_INPUT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "pp1_pilot_dummy_delta_scores_v1.csv"
)
DEFAULT_OUTPUT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "pp1_pilot_dummy_p1_insufficient_response_v1.csv"
)
DEFAULT_REPORT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "pp1_pilot_dummy_fsr_report_v1.json"
)

FSR_FIELDS = (
    *DELTA_SCORE_FIELDS,
    "insufficient_response_delta",
    "insufficient_response_comparator",
    "insufficient_response",
)


class FalseSensitivityRateError(ValueError):
    """Raised when P1 inputs or FSR parameters violate the frozen contract."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display_path(path: Path) -> str:
    return (
        path.relative_to(REPOSITORY_ROOT).as_posix()
        if path.is_relative_to(REPOSITORY_ROOT)
        else str(path)
    )


def _validated_nonnegative(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise FalseSensitivityRateError(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0.0:
        raise FalseSensitivityRateError(f"{label} must be finite and non-negative")
    return number


def _validated_delta(value: object) -> float:
    delta = _validated_nonnegative(value, "delta")
    if not 0.0 < delta <= 1.0:
        raise FalseSensitivityRateError("delta must be in (0,1]")
    return delta


def is_insufficient_response(absolute_delta_score: object, delta: object) -> bool:
    """Apply the frozen P1 rule: insufficient when |DeltaScore| < delta."""

    magnitude = _validated_nonnegative(absolute_delta_score, "absolute_delta_score")
    threshold = _validated_delta(delta)
    return magnitude < threshold


def false_sensitivity_rate(flags: Sequence[bool]) -> float:
    """Return insufficient-response P1 edits divided by evaluated P1 edits."""

    if not flags:
        raise FalseSensitivityRateError("FSR requires at least one P1 perturbation")
    if any(not isinstance(value, bool) for value in flags):
        raise FalseSensitivityRateError("FSR inputs must be booleans")
    return sum(flags) / len(flags)


def _read_delta_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if tuple(reader.fieldnames or ()) != DELTA_SCORE_FIELDS:
            raise FalseSensitivityRateError("DeltaScore input schema is invalid")
        rows = [dict(row) for row in reader]
    if not rows:
        raise FalseSensitivityRateError("DeltaScore input is empty")
    identifiers = [row["variant_id"] for row in rows]
    if len(identifiers) != len(set(identifiers)):
        raise FalseSensitivityRateError("DeltaScore input has duplicate variant identifiers")
    return rows


def calculate_insufficient_response_rows(
    delta_rows: Sequence[Mapping[str, str]],
    delta: float,
) -> list[dict[str, str]]:
    """Restrict to P1 records and append insufficient-response indicators."""

    threshold = _validated_delta(delta)
    p1_rows = [row for row in delta_rows if row["perturbation_type"] == "P1"]
    if not p1_rows:
        raise FalseSensitivityRateError("DeltaScore input contains no P1 perturbations")
    output: list[dict[str, str]] = []
    predictor_metadata: tuple[str, ...] | None = None
    metadata_fields = (
        "predictor_id",
        "predictor_version",
        "scoring_method",
        "software_testing_only",
        "score_contract_id",
        "normalization_mapping",
    )
    for row in p1_rows:
        current_metadata = tuple(row[field] for field in metadata_fields)
        if predictor_metadata is None:
            predictor_metadata = current_metadata
        elif current_metadata != predictor_metadata:
            raise FalseSensitivityRateError("P1 input mixes predictor or score metadata")
        try:
            magnitude = float(row["absolute_delta_score"])
        except ValueError as exc:
            raise FalseSensitivityRateError(
                f"{row['variant_id']} contains a non-numeric absolute DeltaScore"
            ) from exc
        insufficient = is_insufficient_response(magnitude, threshold)
        output.append(
            {
                **row,
                "insufficient_response_delta": repr(threshold),
                "insufficient_response_comparator": INSUFFICIENT_RESPONSE_COMPARATOR,
                "insufficient_response": str(insufficient).lower(),
            }
        )
    return output


def _write_rows(path: Path, rows: Sequence[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FSR_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: row[field] for field in FSR_FIELDS} for row in rows)


def build_false_sensitivity_rate_dataset(
    input_path: str | Path = DEFAULT_INPUT_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    config: ResearchConfig | None = None,
    created_on: date | None = None,
) -> dict[str, Any]:
    """Create P1 insufficient-response indicators and preliminary pilot FSR."""

    active_config = config or load_research_config()
    source = Path(input_path)
    output = Path(output_path)
    report_output = Path(report_path)
    delta_rows = _read_delta_rows(source)
    response_rows = calculate_insufficient_response_rows(
        delta_rows,
        active_config.primary_delta,
    )
    _write_rows(output, response_rows)

    flags = [row["insufficient_response"] == "true" for row in response_rows]
    insufficient_count = sum(flags)
    sufficient_count = len(flags) - insufficient_count
    rate = false_sensitivity_rate(flags)
    boundary_checks = [
        {
            "absolute_delta_score": math.nextafter(active_config.primary_delta, 0.0),
            "expected_insufficient_response": True,
            "actual_insufficient_response": is_insufficient_response(
                math.nextafter(active_config.primary_delta, 0.0),
                active_config.primary_delta,
            ),
        },
        {
            "absolute_delta_score": active_config.primary_delta,
            "expected_insufficient_response": False,
            "actual_insufficient_response": is_insufficient_response(
                active_config.primary_delta,
                active_config.primary_delta,
            ),
        },
    ]
    report: dict[str, Any] = {
        "schema_version": FSR_SCHEMA_VERSION,
        "pipeline_version": FSR_PIPELINE_VERSION,
        "dataset_version": FSR_DATASET_VERSION,
        "created_on": (created_on or date.today()).isoformat(),
        "source_dataset_version": DELTA_SCORE_DATASET_VERSION,
        "definition": {
            "eligible_perturbation_type": "P1",
            "delta_source": "research_config.toml research.primary_delta",
            "delta": active_config.primary_delta,
            "insufficient_response_rule": "absolute_delta_score < delta",
            "boundary_rule": (
                "an edit with absolute_delta_score == delta is a sufficient response"
            ),
            "false_sensitivity_rate": (
                "insufficient_response_p1_count / evaluated_p1_count"
            ),
        },
        "predictor": {
            "predictor_id": response_rows[0]["predictor_id"],
            "display_name": response_rows[0]["predictor_display_name"],
            "version": response_rows[0]["predictor_version"],
            "scoring_method": response_rows[0]["scoring_method"],
            "software_testing_only": response_rows[0]["software_testing_only"] == "true",
            "scientific_result": False,
        },
        "source": {
            "path": _display_path(source),
            "record_count": len(delta_rows),
            "p1_record_count": len(response_rows),
            "sha256": _sha256(source),
        },
        "result": {
            "evaluated_p1_count": len(response_rows),
            "insufficient_response_p1_count": insufficient_count,
            "sufficient_response_p1_count": sufficient_count,
            "false_sensitivity_rate": rate,
        },
        "boundary_checks": boundary_checks,
        "validation": {
            "status": "PASS",
            "only_p1_records": all(
                row["perturbation_type"] == "P1" for row in response_rows
            ),
            "all_rows_classified": len(flags) == len(response_rows),
            "counts_reconcile": insufficient_count + sufficient_count
            == len(response_rows),
            "fsr_within_zero_to_one": 0.0 <= rate <= 1.0,
            "strict_boundary_verified": all(
                check["actual_insufficient_response"]
                == check["expected_insufficient_response"]
                for check in boundary_checks
            ),
            "software_testing_only_preserved": all(
                row["software_testing_only"] == "true" for row in response_rows
            ),
        },
        "output": {
            "path": _display_path(output),
            "record_count": len(response_rows),
            "fields": list(FSR_FIELDS),
            "sha256": _sha256(output),
        },
    }
    if not all(
        value for key, value in report["validation"].items() if key != "status"
    ):
        raise FalseSensitivityRateError("false-sensitivity-rate dataset failed validation")
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


if __name__ == "__main__":
    result = build_false_sensitivity_rate_dataset()
    values = result["result"]
    print(
        f"Marked {values['insufficient_response_p1_count']} of "
        f"{values['evaluated_p1_count']} software-only P1 edits insufficient "
        f"(FSR={values['false_sensitivity_rate']:.6f})."
    )
