"""Preliminary Behavioural Consistency Score calculation for Task 3.30."""

from __future__ import annotations

from datetime import date
import hashlib
import json
import math
from numbers import Real
from pathlib import Path
from typing import Any, Mapping

from .false_sensitivity_rate import FSR_DATASET_VERSION
from .invariance_rate import INVARIANCE_DATASET_VERSION
from .standardization import REPOSITORY_ROOT


BCS_SCHEMA_VERSION = "1.0"
BCS_PIPELINE_VERSION = "c3_aop_bcs_preliminary_bcs_v1"
BCS_REPORT_VERSION = "c3_aop_bcs_pp1_pilot_dummy_bcs_v1"

DEFAULT_IR_REPORT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "pp1_pilot_dummy_ir_report_v1.json"
)
DEFAULT_FSR_REPORT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "pp1_pilot_dummy_fsr_report_v1.json"
)
DEFAULT_REPORT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "pp1_pilot_dummy_bcs_report_v1.json"
)


class PreliminaryBCSError(ValueError):
    """Raised when component metrics violate the preliminary BCS contract."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display_path(path: Path) -> str:
    return (
        path.relative_to(REPOSITORY_ROOT).as_posix()
        if path.is_relative_to(REPOSITORY_ROOT)
        else str(path)
    )


def _validated_rate(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise PreliminaryBCSError(f"{label} must be numeric")
    rate = float(value)
    if not math.isfinite(rate) or not 0.0 <= rate <= 1.0:
        raise PreliminaryBCSError(f"{label} must be finite and within [0,1]")
    return rate


def calculate_bcs(invariance_rate: object, false_sensitivity_rate: object) -> float:
    """Calculate BCS = IR * (1 - FSR) from validated component rates."""

    ir = _validated_rate(invariance_rate, "invariance_rate")
    fsr = _validated_rate(false_sensitivity_rate, "false_sensitivity_rate")
    score = ir * (1.0 - fsr)
    if not 0.0 <= score <= 1.0:
        raise PreliminaryBCSError("calculated BCS is outside [0,1]")
    return score


def _read_report(path: Path, label: str) -> dict[str, Any]:
    try:
        report = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PreliminaryBCSError(f"could not read {label} report: {path}") from exc
    if not isinstance(report, dict):
        raise PreliminaryBCSError(f"{label} report must contain a JSON object")
    return report


def _require_mapping(
    value: object,
    label: str,
) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise PreliminaryBCSError(f"{label} must be an object")
    return value


def _validate_component_reports(
    ir_report: Mapping[str, Any],
    fsr_report: Mapping[str, Any],
) -> tuple[float, float]:
    if ir_report.get("dataset_version") != INVARIANCE_DATASET_VERSION:
        raise PreliminaryBCSError("IR report dataset version is not supported")
    if fsr_report.get("dataset_version") != FSR_DATASET_VERSION:
        raise PreliminaryBCSError("FSR report dataset version is not supported")

    ir_validation = _require_mapping(ir_report.get("validation"), "IR validation")
    fsr_validation = _require_mapping(fsr_report.get("validation"), "FSR validation")
    if ir_validation.get("status") != "PASS":
        raise PreliminaryBCSError("IR report validation status is not PASS")
    if fsr_validation.get("status") != "PASS":
        raise PreliminaryBCSError("FSR report validation status is not PASS")

    ir_predictor = _require_mapping(ir_report.get("predictor"), "IR predictor")
    fsr_predictor = _require_mapping(fsr_report.get("predictor"), "FSR predictor")
    metadata_fields = (
        "predictor_id",
        "display_name",
        "version",
        "scoring_method",
        "software_testing_only",
        "scientific_result",
    )
    if any(ir_predictor.get(field) != fsr_predictor.get(field) for field in metadata_fields):
        raise PreliminaryBCSError("IR and FSR reports use different predictor metadata")
    if ir_predictor.get("software_testing_only") is not True:
        raise PreliminaryBCSError("preliminary BCS input must preserve testing-only status")
    if ir_predictor.get("scientific_result") is not False:
        raise PreliminaryBCSError("preliminary BCS input must not claim a scientific result")

    ir_definition = _require_mapping(ir_report.get("definition"), "IR definition")
    fsr_definition = _require_mapping(fsr_report.get("definition"), "FSR definition")
    if ir_definition.get("delta") != fsr_definition.get("delta"):
        raise PreliminaryBCSError("IR and FSR reports use different delta thresholds")

    ir_source = _require_mapping(ir_report.get("source"), "IR source")
    fsr_source = _require_mapping(fsr_report.get("source"), "FSR source")
    if ir_report.get("source_dataset_version") != fsr_report.get("source_dataset_version"):
        raise PreliminaryBCSError("IR and FSR reports use different source datasets")
    if ir_source.get("sha256") != fsr_source.get("sha256"):
        raise PreliminaryBCSError("IR and FSR reports use different source content")

    ir_result = _require_mapping(ir_report.get("result"), "IR result")
    fsr_result = _require_mapping(fsr_report.get("result"), "FSR result")
    ir = _validated_rate(ir_result.get("invariance_rate"), "invariance_rate")
    fsr = _validated_rate(
        fsr_result.get("false_sensitivity_rate"),
        "false_sensitivity_rate",
    )
    return ir, fsr


def build_preliminary_bcs_report(
    ir_report_path: str | Path = DEFAULT_IR_REPORT_PATH,
    fsr_report_path: str | Path = DEFAULT_FSR_REPORT_PATH,
    report_path: str | Path = DEFAULT_REPORT_PATH,
    created_on: date | None = None,
) -> dict[str, Any]:
    """Combine validated IR and FSR reports into a preliminary pilot BCS report."""

    ir_source = Path(ir_report_path)
    fsr_source = Path(fsr_report_path)
    output = Path(report_path)
    ir_report = _read_report(ir_source, "IR")
    fsr_report = _read_report(fsr_source, "FSR")
    ir, fsr = _validate_component_reports(ir_report, fsr_report)
    bcs = calculate_bcs(ir, fsr)

    manual_checks = [
        {
            "invariance_rate": 1.0,
            "false_sensitivity_rate": 0.0,
            "expected_bcs": 1.0,
            "actual_bcs": calculate_bcs(1.0, 0.0),
        },
        {
            "invariance_rate": 0.8,
            "false_sensitivity_rate": 0.25,
            "expected_bcs": 0.6,
            "actual_bcs": calculate_bcs(0.8, 0.25),
        },
        {
            "invariance_rate": 0.0,
            "false_sensitivity_rate": 0.5,
            "expected_bcs": 0.0,
            "actual_bcs": calculate_bcs(0.0, 0.5),
        },
    ]
    ir_predictor = _require_mapping(ir_report["predictor"], "IR predictor")
    ir_result = _require_mapping(ir_report["result"], "IR result")
    fsr_result = _require_mapping(fsr_report["result"], "FSR result")
    report: dict[str, Any] = {
        "schema_version": BCS_SCHEMA_VERSION,
        "pipeline_version": BCS_PIPELINE_VERSION,
        "report_version": BCS_REPORT_VERSION,
        "created_on": (created_on or date.today()).isoformat(),
        "definition": {
            "formula": "BCS = IR * (1 - FSR)",
            "expected_range": "[0,1]",
            "interpretation": "higher BCS indicates better behavioural consistency",
            "scope": "preliminary PP1 software-pipeline pilot only",
        },
        "predictor": dict(ir_predictor),
        "sources": {
            "invariance_rate_report": {
                "path": _display_path(ir_source),
                "dataset_version": ir_report["dataset_version"],
                "sha256": _sha256(ir_source),
            },
            "false_sensitivity_rate_report": {
                "path": _display_path(fsr_source),
                "dataset_version": fsr_report["dataset_version"],
                "sha256": _sha256(fsr_source),
            },
            "shared_delta": ir_report["definition"]["delta"],
            "shared_delta_source": ir_report["definition"]["delta_source"],
        },
        "components": {
            "invariance_rate": {
                "evaluated_p2_count": ir_result["evaluated_p2_count"],
                "invariant_p2_count": ir_result["invariant_p2_count"],
                "value": ir,
            },
            "false_sensitivity_rate": {
                "evaluated_p1_count": fsr_result["evaluated_p1_count"],
                "insufficient_response_p1_count": fsr_result[
                    "insufficient_response_p1_count"
                ],
                "value": fsr,
            },
        },
        "result": {
            "preliminary_bcs": bcs,
            "preliminary_pilot_value": True,
            "software_testing_only": True,
            "scientific_result": False,
            "warning": (
                "This value was produced with the non-experimental dummy predictor "
                "to validate the metric pipeline; it is not a final scientific conclusion."
            ),
        },
        "manual_formula_checks": manual_checks,
        "validation": {
            "status": "PASS",
            "component_reports_passed": (
                ir_report["validation"]["status"] == "PASS"
                and fsr_report["validation"]["status"] == "PASS"
            ),
            "predictor_metadata_matches": True,
            "source_dataset_matches": True,
            "delta_matches": True,
            "formula_recomputed": bcs == ir * (1.0 - fsr),
            "bcs_within_zero_to_one": 0.0 <= bcs <= 1.0,
            "manual_examples_passed": all(
                math.isclose(
                    check["actual_bcs"],
                    check["expected_bcs"],
                    rel_tol=0.0,
                    abs_tol=1e-15,
                )
                for check in manual_checks
            ),
            "software_testing_only_preserved": (
                ir_predictor["software_testing_only"] is True
            ),
            "not_a_scientific_result": ir_predictor["scientific_result"] is False,
        },
    }
    if not all(value for key, value in report["validation"].items() if key != "status"):
        raise PreliminaryBCSError("preliminary BCS report failed validation")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return report


if __name__ == "__main__":
    generated = build_preliminary_bcs_report()
    result = generated["result"]
    print(
        "Calculated software-only preliminary pilot BCS="
        f"{result['preliminary_bcs']:.6f}; this is not a scientific result."
    )
