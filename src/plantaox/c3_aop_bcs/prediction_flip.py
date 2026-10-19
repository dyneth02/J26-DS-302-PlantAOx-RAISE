"""Prediction-flip detection and PFR calculation for Task 3.27."""

from __future__ import annotations

from collections import Counter
import csv
from dataclasses import dataclass
from datetime import date
import hashlib
import json
import math
from numbers import Real
from pathlib import Path
from typing import Any, Mapping, Sequence

from .delta_score import DELTA_SCORE_FIELDS, DELTA_SCORE_DATASET_VERSION
from .standardization import REPOSITORY_ROOT


PREDICTION_FLIP_SCHEMA_VERSION = "1.0"
PREDICTION_FLIP_PIPELINE_VERSION = "c3_aop_bcs_prediction_flip_pfr_v1"
PREDICTION_FLIP_DATASET_VERSION = "c3_aop_bcs_pp1_pilot_dummy_prediction_flips_v1"
DUMMY_DECISION_THRESHOLD = 0.5
DECISION_COMPARATOR = "greater_than_or_equal"

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
    / "pp1_pilot_dummy_prediction_flips_v1.csv"
)
DEFAULT_REPORT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "pp1_pilot_dummy_pfr_report_v1.json"
)

PREDICTION_FLIP_FIELDS = (
    *DELTA_SCORE_FIELDS,
    "decision_threshold",
    "decision_comparator",
    "original_class",
    "perturbed_class",
    "prediction_flip",
    "flip_direction",
)


class PredictionFlipError(ValueError):
    """Raised when a decision rule or flip dataset is invalid."""


@dataclass(frozen=True, slots=True)
class PredictionFlip:
    """Classification and flip result for one score pair."""

    original_class: int
    perturbed_class: int
    flipped: bool
    direction: str


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display_path(path: Path) -> str:
    return (
        path.relative_to(REPOSITORY_ROOT).as_posix()
        if path.is_relative_to(REPOSITORY_ROOT)
        else str(path)
    )


def _float_text(value: float) -> str:
    return format(value, ".17g")


def _validated_score(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise PredictionFlipError(f"{label} must be numeric")
    score = float(value)
    if not math.isfinite(score) or not 0.0 <= score <= 1.0:
        raise PredictionFlipError(f"{label} must be finite and within [0,1]")
    return score


def _validated_threshold(value: object) -> float:
    return _validated_score(value, "decision_threshold")


def classify_score(score: object, threshold: object) -> int:
    """Classify a usable score using the frozen inclusive threshold rule."""

    usable = _validated_score(score, "usable_score")
    boundary = _validated_threshold(threshold)
    return int(usable >= boundary)


def detect_prediction_flip(
    original_score: object,
    perturbed_score: object,
    threshold: object,
) -> PredictionFlip:
    """Classify a score pair and detect whether its predicted class changed."""

    original_class = classify_score(original_score, threshold)
    perturbed_class = classify_score(perturbed_score, threshold)
    flipped = original_class != perturbed_class
    if original_class == 1 and perturbed_class == 0:
        direction = "positive_to_negative"
    elif original_class == 0 and perturbed_class == 1:
        direction = "negative_to_positive"
    else:
        direction = "none"
    return PredictionFlip(original_class, perturbed_class, flipped, direction)


def prediction_flip_rate(flips: Sequence[bool]) -> float:
    """Return flip count divided by the number of evaluated perturbations."""

    if not flips:
        raise PredictionFlipError("PFR requires at least one perturbation")
    if any(not isinstance(value, bool) for value in flips):
        raise PredictionFlipError("PFR inputs must be booleans")
    return sum(flips) / len(flips)


def _read_delta_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if tuple(reader.fieldnames or ()) != DELTA_SCORE_FIELDS:
            raise PredictionFlipError("DeltaScore input schema is invalid")
        rows = [dict(row) for row in reader]
    if not rows:
        raise PredictionFlipError("DeltaScore input is empty")
    identifiers = [row["variant_id"] for row in rows]
    if len(identifiers) != len(set(identifiers)):
        raise PredictionFlipError("DeltaScore input has duplicate variant identifiers")
    return rows


def calculate_prediction_flip_rows(
    delta_rows: Sequence[Mapping[str, str]],
    decision_threshold: float,
) -> list[dict[str, str]]:
    """Append classes and flip metadata to each DeltaScore record."""

    threshold = _validated_threshold(decision_threshold)
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
    for row in delta_rows:
        current_metadata = tuple(row[field] for field in metadata_fields)
        if predictor_metadata is None:
            predictor_metadata = current_metadata
        elif current_metadata != predictor_metadata:
            raise PredictionFlipError("DeltaScore input mixes predictor or score metadata")
        try:
            original_score = float(row["original_usable_score"])
            perturbed_score = float(row["perturbed_usable_score"])
        except ValueError as exc:
            raise PredictionFlipError(
                f"{row['variant_id']} contains a non-numeric usable score"
            ) from exc
        result = detect_prediction_flip(original_score, perturbed_score, threshold)
        output.append(
            {
                **row,
                "decision_threshold": _float_text(threshold),
                "decision_comparator": DECISION_COMPARATOR,
                "original_class": str(result.original_class),
                "perturbed_class": str(result.perturbed_class),
                "prediction_flip": str(result.flipped).lower(),
                "flip_direction": result.direction,
            }
        )
    return output


def _write_rows(path: Path, rows: Sequence[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=PREDICTION_FLIP_FIELDS,
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(
            {field: row[field] for field in PREDICTION_FLIP_FIELDS} for row in rows
        )


def _pfr_summary(rows: Sequence[Mapping[str, str]]) -> dict[str, Any]:
    flips = [row["prediction_flip"] == "true" for row in rows]
    directions = Counter(row["flip_direction"] for row in rows)
    return {
        "perturbation_count": len(rows),
        "flip_count": sum(flips),
        "prediction_flip_rate": prediction_flip_rate(flips),
        "positive_to_negative_count": directions["positive_to_negative"],
        "negative_to_positive_count": directions["negative_to_positive"],
        "no_flip_count": directions["none"],
    }


def build_prediction_flip_dataset(
    input_path: str | Path = DEFAULT_INPUT_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    decision_threshold: float = DUMMY_DECISION_THRESHOLD,
    created_on: date | None = None,
) -> dict[str, Any]:
    """Create per-perturbation flip results and overall/type-specific PFR."""

    source = Path(input_path)
    output = Path(output_path)
    report_output = Path(report_path)
    delta_rows = _read_delta_rows(source)
    flip_rows = calculate_prediction_flip_rows(delta_rows, decision_threshold)
    _write_rows(output, flip_rows)

    grouped = {
        kind: [row for row in flip_rows if row["perturbation_type"] == kind]
        for kind in ("P1", "P2", "P3")
    }
    overall = _pfr_summary(flip_rows)
    by_type = {kind: _pfr_summary(rows) for kind, rows in grouped.items()}
    original_class_counts = Counter(row["original_class"] for row in flip_rows)
    perturbed_class_counts = Counter(row["perturbed_class"] for row in flip_rows)
    boundary_checks = [
        {
            "score": 0.5,
            "threshold": decision_threshold,
            "expected_class": 1,
            "actual_class": classify_score(0.5, decision_threshold),
        },
        {
            "score": math.nextafter(0.5, 0.0),
            "threshold": decision_threshold,
            "expected_class": 0,
            "actual_class": classify_score(math.nextafter(0.5, 0.0), decision_threshold),
        },
    ]

    report: dict[str, Any] = {
        "schema_version": PREDICTION_FLIP_SCHEMA_VERSION,
        "pipeline_version": PREDICTION_FLIP_PIPELINE_VERSION,
        "dataset_version": PREDICTION_FLIP_DATASET_VERSION,
        "created_on": (created_on or date.today()).isoformat(),
        "source_dataset_version": DELTA_SCORE_DATASET_VERSION,
        "decision_rule": {
            "predictor_id": flip_rows[0]["predictor_id"],
            "score_field": "usable score from the recorded normalization contract",
            "threshold": decision_threshold,
            "comparator": DECISION_COMPARATOR,
            "positive_class_rule": "usable_score >= threshold",
            "negative_class_rule": "usable_score < threshold",
            "source": "C3 software-smoke-test convention",
            "real_predictor_policy": (
                "Every real predictor must provide and record its own verified decision rule; "
                "the dummy threshold must not be reused implicitly."
            ),
        },
        "predictor": {
            "predictor_id": flip_rows[0]["predictor_id"],
            "display_name": flip_rows[0]["predictor_display_name"],
            "version": flip_rows[0]["predictor_version"],
            "scoring_method": flip_rows[0]["scoring_method"],
            "software_testing_only": flip_rows[0]["software_testing_only"] == "true",
            "scientific_result": False,
        },
        "source": {
            "path": _display_path(source),
            "record_count": len(delta_rows),
            "sha256": _sha256(source),
        },
        "class_counts": {
            "original": {
                "negative": original_class_counts["0"],
                "positive": original_class_counts["1"],
            },
            "perturbed": {
                "negative": perturbed_class_counts["0"],
                "positive": perturbed_class_counts["1"],
            },
        },
        "pfr": {
            "definition": "flip_count / perturbation_count",
            "overall": overall,
            "by_perturbation_type": by_type,
        },
        "boundary_checks": boundary_checks,
        "validation": {
            "status": "PASS",
            "all_rows_classified": all(
                row["original_class"] in {"0", "1"}
                and row["perturbed_class"] in {"0", "1"}
                for row in flip_rows
            ),
            "all_flip_indicators_consistent": all(
                (row["prediction_flip"] == "true")
                == (row["original_class"] != row["perturbed_class"])
                for row in flip_rows
            ),
            "counts_reconcile": overall["flip_count"] + overall["no_flip_count"]
            == overall["perturbation_count"],
            "group_counts_reconcile": sum(
                summary["perturbation_count"] for summary in by_type.values()
            )
            == overall["perturbation_count"],
            "pfr_within_zero_to_one": all(
                0.0 <= summary["prediction_flip_rate"] <= 1.0
                for summary in (overall, *by_type.values())
            ),
            "boundary_rule_verified": all(
                check["actual_class"] == check["expected_class"]
                for check in boundary_checks
            ),
            "software_testing_only_preserved": all(
                row["software_testing_only"] == "true" for row in flip_rows
            ),
        },
        "output": {
            "path": _display_path(output),
            "record_count": len(flip_rows),
            "fields": list(PREDICTION_FLIP_FIELDS),
            "sha256": _sha256(output),
        },
    }
    if not all(
        value for key, value in report["validation"].items() if key != "status"
    ):
        raise PredictionFlipError("prediction-flip dataset failed validation")
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


if __name__ == "__main__":
    result = build_prediction_flip_dataset()
    overall = result["pfr"]["overall"]
    print(
        f"Detected {overall['flip_count']} flips across "
        f"{overall['perturbation_count']} software-only pilot perturbations "
        f"(PFR={overall['prediction_flip_rate']:.6f})."
    )
