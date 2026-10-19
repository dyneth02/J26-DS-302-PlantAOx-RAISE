"""Per-perturbation DeltaScore calculation for Task 3.26."""

from __future__ import annotations

from collections import Counter
import csv
from datetime import date
import hashlib
import json
import math
from numbers import Real
from pathlib import Path
from typing import Any, Mapping, Sequence

from .perturbation_schema import PERTURBATION_FIELDS
from .predictor_scoring import SCORED_PERTURBATION_FIELDS
from .score_normalization import (
    NORMALIZATION_SCHEMA_VERSION,
    load_normalization_registry,
    normalize_score,
)
from .standardization import REPOSITORY_ROOT


DELTA_SCORE_SCHEMA_VERSION = "1.0"
DELTA_SCORE_PIPELINE_VERSION = "c3_aop_bcs_delta_score_v1"
DELTA_SCORE_DATASET_VERSION = "c3_aop_bcs_pp1_pilot_dummy_delta_scores_v1"
DUMMY_SCORE_CONTRACT_ID = "c3_dummy_smoke_score"

DEFAULT_SCORED_INPUT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "dummy_scored_perturbations_v1.csv"
)
DEFAULT_PILOT_INPUT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "pp1_pilot_perturbations_v1.csv"
)
DEFAULT_OUTPUT_PATH = (
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
    / "pp1_pilot_dummy_delta_score_report_v1.json"
)

DELTA_SCORE_FIELDS = (
    *SCORED_PERTURBATION_FIELDS,
    "normalization_schema_version",
    "score_contract_id",
    "normalization_mapping",
    "original_usable_score",
    "perturbed_usable_score",
    "delta_score",
    "absolute_delta_score",
)


class DeltaScoreError(ValueError):
    """Raised when scored inputs cannot produce a valid DeltaScore dataset."""


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


def calculate_delta_score(
    original_score: object,
    perturbed_score: object,
) -> tuple[float, float]:
    """Return signed original-minus-perturbed score and its magnitude."""

    for label, value in (
        ("original_score", original_score),
        ("perturbed_score", perturbed_score),
    ):
        if isinstance(value, bool) or not isinstance(value, Real):
            raise DeltaScoreError(f"{label} must be numeric")
        if not math.isfinite(float(value)):
            raise DeltaScoreError(f"{label} must be finite")
    delta = float(original_score) - float(perturbed_score)
    return delta, abs(delta)


def _read_pilot_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if tuple(reader.fieldnames or ()) != PERTURBATION_FIELDS:
            raise DeltaScoreError("pilot perturbation schema is invalid")
        rows = [dict(row) for row in reader]
    if not rows:
        raise DeltaScoreError("pilot perturbation dataset is empty")
    identifiers = [row["variant_id"] for row in rows]
    if len(identifiers) != len(set(identifiers)):
        raise DeltaScoreError("pilot perturbation dataset has duplicate variant identifiers")
    return rows


def _read_scored_rows(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        if tuple(reader.fieldnames or ()) != SCORED_PERTURBATION_FIELDS:
            raise DeltaScoreError("scored perturbation schema is invalid")
        rows: dict[str, dict[str, str]] = {}
        for row_number, row in enumerate(reader, start=2):
            variant_id = row["variant_id"]
            if variant_id in rows:
                raise DeltaScoreError(
                    f"scored perturbations contain duplicate variant {variant_id!r}"
                )
            rows[variant_id] = dict(row)
            if not variant_id:
                raise DeltaScoreError(
                    f"scored perturbations have an empty variant ID at row {row_number}"
                )
    if not rows:
        raise DeltaScoreError("scored perturbation dataset is empty")
    return rows


def _validate_join(
    pilot_row: Mapping[str, str],
    scored_row: Mapping[str, str],
) -> None:
    for field in PERTURBATION_FIELDS:
        if pilot_row[field] != scored_row[field]:
            raise DeltaScoreError(
                f"{pilot_row['variant_id']} has conflicting {field!r} values"
            )


def calculate_delta_rows(
    pilot_rows: Sequence[Mapping[str, str]],
    scored_by_id: Mapping[str, Mapping[str, str]],
    score_contract_id: str = DUMMY_SCORE_CONTRACT_ID,
) -> list[dict[str, str]]:
    """Join pilot variants to scores and calculate normalized DeltaScores."""

    registry = load_normalization_registry()
    output: list[dict[str, str]] = []
    predictor_metadata: tuple[str, ...] | None = None
    metadata_fields = (
        "score_schema_version",
        "predictor_id",
        "predictor_display_name",
        "predictor_version",
        "scoring_method",
        "software_testing_only",
    )

    for pilot_row in pilot_rows:
        variant_id = pilot_row["variant_id"]
        scored_row = scored_by_id.get(variant_id)
        if scored_row is None:
            raise DeltaScoreError(f"pilot variant {variant_id!r} has no scored record")
        _validate_join(pilot_row, scored_row)

        current_metadata = tuple(scored_row[field] for field in metadata_fields)
        if predictor_metadata is None:
            predictor_metadata = current_metadata
        elif current_metadata != predictor_metadata:
            raise DeltaScoreError("scored input mixes predictor or scoring metadata")

        try:
            original_native = float(scored_row["original_score"])
            perturbed_native = float(scored_row["perturbed_score"])
        except ValueError as exc:
            raise DeltaScoreError(f"{variant_id} contains a non-numeric score") from exc
        original = normalize_score(original_native, score_contract_id, registry)
        perturbed = normalize_score(perturbed_native, score_contract_id, registry)
        if original.mapping != perturbed.mapping:
            raise DeltaScoreError(f"{variant_id} uses inconsistent normalization mappings")
        delta, absolute_delta = calculate_delta_score(
            original.usable_score,
            perturbed.usable_score,
        )
        output.append(
            {
                **scored_row,
                "normalization_schema_version": NORMALIZATION_SCHEMA_VERSION,
                "score_contract_id": score_contract_id,
                "normalization_mapping": original.mapping,
                "original_usable_score": _float_text(original.usable_score),
                "perturbed_usable_score": _float_text(perturbed.usable_score),
                "delta_score": _float_text(delta),
                "absolute_delta_score": _float_text(absolute_delta),
            }
        )
    return output


def _write_rows(path: Path, rows: Sequence[Mapping[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=DELTA_SCORE_FIELDS, lineterminator="\n")
        writer.writeheader()
        writer.writerows({field: row[field] for field in DELTA_SCORE_FIELDS} for row in rows)


def _hand_checks() -> list[dict[str, Any]]:
    examples = (
        (0.8, 0.3, 0.5, 0.5),
        (0.25, 0.4, -0.15, 0.15),
        (0.6, 0.6, 0.0, 0.0),
    )
    checks: list[dict[str, Any]] = []
    for original, perturbed, expected_delta, expected_absolute in examples:
        actual_delta, actual_absolute = calculate_delta_score(original, perturbed)
        passed = math.isclose(actual_delta, expected_delta, abs_tol=1e-12) and math.isclose(
            actual_absolute, expected_absolute, abs_tol=1e-12
        )
        checks.append(
            {
                "original_score": original,
                "perturbed_score": perturbed,
                "expected_delta_score": expected_delta,
                "expected_absolute_delta_score": expected_absolute,
                "actual_delta_score": actual_delta,
                "actual_absolute_delta_score": actual_absolute,
                "passed": passed,
            }
        )
    return checks


def build_delta_score_dataset(
    scored_input_path: str | Path = DEFAULT_SCORED_INPUT_PATH,
    pilot_input_path: str | Path = DEFAULT_PILOT_INPUT_PATH,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    score_contract_id: str = DUMMY_SCORE_CONTRACT_ID,
    created_on: date | None = None,
) -> dict[str, Any]:
    """Build the versioned PP1 per-position DeltaScore dataset and report."""

    scored_input = Path(scored_input_path)
    pilot_input = Path(pilot_input_path)
    output = Path(output_path)
    report_output = Path(report_path)
    pilot_rows = _read_pilot_rows(pilot_input)
    scored_rows = _read_scored_rows(scored_input)
    delta_rows = calculate_delta_rows(pilot_rows, scored_rows, score_contract_id)
    _write_rows(output, delta_rows)

    delta_values = [float(row["delta_score"]) for row in delta_rows]
    absolute_values = [float(row["absolute_delta_score"]) for row in delta_rows]
    type_counts = Counter(row["perturbation_type"] for row in delta_rows)
    hand_checks = _hand_checks()
    report: dict[str, Any] = {
        "schema_version": DELTA_SCORE_SCHEMA_VERSION,
        "pipeline_version": DELTA_SCORE_PIPELINE_VERSION,
        "dataset_version": DELTA_SCORE_DATASET_VERSION,
        "created_on": (created_on or date.today()).isoformat(),
        "definition": {
            "delta_score": "original_usable_score - perturbed_usable_score",
            "absolute_delta_score": "abs(delta_score)",
            "interpretation": {
                "positive": "perturbation decreased the usable predictor score",
                "negative": "perturbation increased the usable predictor score",
                "zero": "no usable score change",
            },
        },
        "predictor": {
            "predictor_id": delta_rows[0]["predictor_id"],
            "display_name": delta_rows[0]["predictor_display_name"],
            "version": delta_rows[0]["predictor_version"],
            "scoring_method": delta_rows[0]["scoring_method"],
            "software_testing_only": delta_rows[0]["software_testing_only"] == "true",
            "score_contract_id": score_contract_id,
            "normalization_mapping": delta_rows[0]["normalization_mapping"],
            "scientific_result": False,
        },
        "sources": {
            "scored_perturbations": {
                "path": _display_path(scored_input),
                "record_count": len(scored_rows),
                "sha256": _sha256(scored_input),
            },
            "pilot_perturbations": {
                "path": _display_path(pilot_input),
                "record_count": len(pilot_rows),
                "sha256": _sha256(pilot_input),
            },
        },
        "counts": {
            "delta_score_count": len(delta_rows),
            "unique_subject_count": len({row["sequence_id"] for row in delta_rows}),
            "by_perturbation_type": {
                kind: type_counts[kind] for kind in ("P1", "P2", "P3")
            },
            "positive_delta_count": sum(value > 0 for value in delta_values),
            "negative_delta_count": sum(value < 0 for value in delta_values),
            "zero_delta_count": sum(value == 0 for value in delta_values),
        },
        "range": {
            "delta_score_min": min(delta_values),
            "delta_score_max": max(delta_values),
            "absolute_delta_score_min": min(absolute_values),
            "absolute_delta_score_max": max(absolute_values),
        },
        "hand_checked_examples": hand_checks,
        "validation": {
            "status": "PASS",
            "all_pilot_variants_joined_once": len(delta_rows) == len(pilot_rows),
            "all_values_finite": all(
                math.isfinite(value) for value in (*delta_values, *absolute_values)
            ),
            "all_absolute_values_non_negative": all(value >= 0 for value in absolute_values),
            "all_absolute_values_match_signed_magnitude": all(
                math.isclose(abs(delta), absolute, abs_tol=1e-15)
                for delta, absolute in zip(delta_values, absolute_values, strict=True)
            ),
            "hand_checks_passed": all(check["passed"] for check in hand_checks),
            "software_testing_only_preserved": all(
                row["software_testing_only"] == "true" for row in delta_rows
            ),
        },
        "output": {
            "path": _display_path(output),
            "record_count": len(delta_rows),
            "fields": list(DELTA_SCORE_FIELDS),
            "sha256": _sha256(output),
        },
    }
    if not all(
        value for key, value in report["validation"].items() if key != "status"
    ):
        raise DeltaScoreError("DeltaScore dataset failed validation")
    report_output.parent.mkdir(parents=True, exist_ok=True)
    report_output.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


if __name__ == "__main__":
    result = build_delta_score_dataset()
    print(
        f"Calculated {result['counts']['delta_score_count']} software-only PP1 "
        "DeltaScore records."
    )
