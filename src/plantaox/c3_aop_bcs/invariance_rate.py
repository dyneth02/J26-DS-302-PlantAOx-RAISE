"""P2 conservative-edit Invariance Rate calculation for Task 3.28."""

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


INVARIANCE_SCHEMA_VERSION = "1.0"
INVARIANCE_PIPELINE_VERSION = "c3_aop_bcs_invariance_rate_v1"
INVARIANCE_DATASET_VERSION = "c3_aop_bcs_pp1_pilot_dummy_p2_invariance_v1"
INVARIANCE_COMPARATOR = "absolute_delta_score_strictly_less_than_delta"

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
    / "pp1_pilot_dummy_p2_invariance_v1.csv"
)
DEFAULT_REPORT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "pp1_pilot_dummy_ir_report_v1.json"
)

INVARIANCE_FIELDS = (
    *DELTA_SCORE_FIELDS,
    "invariance_delta",
    "invariance_comparator",
    "is_invariant",
)


class InvarianceRateError(ValueError):
    """Raised when P2 inputs or IR parameters violate the frozen contract."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display_path(path: Path) -> str:
    return (
        path.relative_to(REPOSITORY_ROOT).as_posix()
        if path.is_relative_to(REPOSITORY_ROOT)
        else str(path)
    )


def _float_text(value: float) -> str:
    return repr(value)


def _validated_nonnegative(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise InvarianceRateError(f"{label} must be numeric")
    number = float(value)
    if not math.isfinite(number) or number < 0.0:
        raise InvarianceRateError(f"{label} must be finite and non-negative")
    return number


def _validated_delta(value: object) -> float:
    delta = _validated_nonnegative(value, "delta")
    if not 0.0 < delta <= 1.0:
        raise InvarianceRateError("delta must be in (0,1]")
    return delta


def is_invariant(absolute_delta_score: object, delta: object) -> bool:
    """Apply the frozen strict P2 invariance rule: |DeltaScore| < delta."""

    magnitude = _validated_nonnegative(absolute_delta_score, "absolute_delta_score")
    threshold = _validated_delta(delta)
    return magnitude < threshold


def invariance_rate(flags: Sequence[bool]) -> float:
    """Return invariant P2 edits divided by all evaluated P2 edits."""

    if not flags:
        raise InvarianceRateError("IR requires at least one P2 perturbation")
    if any(not isinstance(value, bool) for value in flags):
        raise InvarianceRateError("IR inputs must be booleans")
    return sum(flags) / len(flags)


def _read_delta_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if tuple(reader.fieldnames or ()) != DELTA_SCORE_FIELDS:
            raise InvarianceRateError("DeltaScore input schema is invalid")
        rows = [dict(row) for row in reader]
    if not rows:
        raise InvarianceRateError("DeltaScore input is empty")
    identifiers = [row["variant_id"] for row in rows]
    if len(identifiers) != len(set(identifiers)):
        raise InvarianceRateError("DeltaScore input has duplicate variant identifiers")
    return rows


def calculate_invariance_rows(
    delta_rows: Sequence[Mapping[str, str]],
    delta: float,
) -> list[dict[str, str]]:
    """Restrict to P2 records and append strict invariance indicators."""

    threshold = _validated_delta(delta)
    p2_rows = [row for row in delta_rows if row["perturbation_type"] == "P2"]
    if not p2_rows:
        raise InvarianceRateError("DeltaScore input contains no P2 perturbations")
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
    for row in p2_rows:
        current_metadata = tuple(row[field] for field in metadata_fields)
        if predictor_metadata is None:
            predictor_metadata = current_metadata
        elif current_metadata != predictor_metadata:
            raise InvarianceRateError("P2 input mixes predictor or score metadata")
        try:
            magnitude = float(row["absolute_delta_score"])
        except ValueError as exc:
            raise InvarianceRateError(
                f"{row['variant_id']} contains a non-numeric absolute DeltaScore"
            ) from exc
        invariant = is_invariant(magnitude, threshold)
        output.append(
            {
                **row,
                "invariance_delta": _float_text(threshold),
                "invariance_comparator": INVARIANCE_COMPARATOR,
                "is_invariant": str(invariant).lower(),
            }
        )
    return output


def _write_rows(path: Path, rows: Sequence[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=INVARIANCE_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: row[field] for field in INVARIANCE_FIELDS} for row in rows)


def build_invariance_rate_dataset(
    input_path: str | Path = DEFAULT_INPUT_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    config: ResearchConfig | None = None,
    created_on: date | None = None,
) -> dict[str, Any]:
    """Create P2 invariance indicators and the preliminary pilot IR."""

    active_config = config or load_research_config()
    source = Path(input_path)
    output = Path(output_path)
    report_output = Path(report_path)
    delta_rows = _read_delta_rows(source)
    invariant_rows = calculate_invariance_rows(delta_rows, active_config.primary_delta)
    _write_rows(output, invariant_rows)

    flags = [row["is_invariant"] == "true" for row in invariant_rows]
    invariant_count = sum(flags)
    non_invariant_count = len(flags) - invariant_count
    rate = invariance_rate(flags)
    boundary_checks = [
        {
            "absolute_delta_score": math.nextafter(active_config.primary_delta, 0.0),
            "expected_invariant": True,
            "actual_invariant": is_invariant(
                math.nextafter(active_config.primary_delta, 0.0),
                active_config.primary_delta,
            ),
        },
        {
            "absolute_delta_score": active_config.primary_delta,
            "expected_invariant": False,
            "actual_invariant": is_invariant(
                active_config.primary_delta,
                active_config.primary_delta,
            ),
        },
    ]
    report: dict[str, Any] = {
        "schema_version": INVARIANCE_SCHEMA_VERSION,
        "pipeline_version": INVARIANCE_PIPELINE_VERSION,
        "dataset_version": INVARIANCE_DATASET_VERSION,
        "created_on": (created_on or date.today()).isoformat(),
        "source_dataset_version": DELTA_SCORE_DATASET_VERSION,
        "definition": {
            "eligible_perturbation_type": "P2",
            "delta_source": "research_config.toml research.primary_delta",
            "delta": active_config.primary_delta,
            "invariant_rule": "absolute_delta_score < delta",
            "boundary_rule": "an edit with absolute_delta_score == delta is non-invariant",
            "invariance_rate": "invariant_p2_count / evaluated_p2_count",
        },
        "predictor": {
            "predictor_id": invariant_rows[0]["predictor_id"],
            "display_name": invariant_rows[0]["predictor_display_name"],
            "version": invariant_rows[0]["predictor_version"],
            "scoring_method": invariant_rows[0]["scoring_method"],
            "software_testing_only": invariant_rows[0]["software_testing_only"] == "true",
            "scientific_result": False,
        },
        "source": {
            "path": _display_path(source),
            "record_count": len(delta_rows),
            "p2_record_count": len(invariant_rows),
            "sha256": _sha256(source),
        },
        "result": {
            "evaluated_p2_count": len(invariant_rows),
            "invariant_p2_count": invariant_count,
            "non_invariant_p2_count": non_invariant_count,
            "invariance_rate": rate,
        },
        "boundary_checks": boundary_checks,
        "validation": {
            "status": "PASS",
            "only_p2_records": all(
                row["perturbation_type"] == "P2" for row in invariant_rows
            ),
            "all_rows_classified": len(flags) == len(invariant_rows),
            "counts_reconcile": invariant_count + non_invariant_count
            == len(invariant_rows),
            "ir_within_zero_to_one": 0.0 <= rate <= 1.0,
            "strict_boundary_verified": all(
                check["actual_invariant"] == check["expected_invariant"]
                for check in boundary_checks
            ),
            "software_testing_only_preserved": all(
                row["software_testing_only"] == "true" for row in invariant_rows
            ),
        },
        "output": {
            "path": _display_path(output),
            "record_count": len(invariant_rows),
            "fields": list(INVARIANCE_FIELDS),
            "sha256": _sha256(output),
        },
    }
    if not all(
        value for key, value in report["validation"].items() if key != "status"
    ):
        raise InvarianceRateError("invariance-rate dataset failed validation")
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


if __name__ == "__main__":
    result = build_invariance_rate_dataset()
    values = result["result"]
    print(
        f"Marked {values['invariant_p2_count']} of {values['evaluated_p2_count']} "
        f"software-only P2 edits invariant (IR={values['invariance_rate']:.6f})."
    )
