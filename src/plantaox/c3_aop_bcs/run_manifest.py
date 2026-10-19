"""Create the versioned, checksum-backed PP1 pilot run manifest."""

from __future__ import annotations

import csv
from datetime import date
import hashlib
import json
from pathlib import Path
import re
import subprocess
from typing import Any, Mapping

from .blosum62 import DEFAULT_MANIFEST_PATH as DEFAULT_BLOSUM62_PATH
from .config import DEFAULT_CONFIG_PATH, load_research_config
from .dummy_predictor import DEFAULT_DUMMY_DEFINITION_PATH
from .standardization import REPOSITORY_ROOT


RUN_MANIFEST_SCHEMA_VERSION = "1.0"
RUN_ID = "c3_aop_bcs_pp1_dummy_pilot_run_v1"
WARNING = (
    "PP1 PILOT - DUMMY SOFTWARE TEST ONLY - NOT SCIENTIFIC RESULTS; "
    "real-predictor experimental scoring remains pending."
)
DEFAULT_OUTPUT_PATH = (
    REPOSITORY_ROOT
    / "data"
    / "processed"
    / "c3_aop_bcs"
    / "pp1_pilot_run_manifest_v1.json"
)

DATA_DIRECTORY = REPOSITORY_ROOT / "data" / "processed" / "c3_aop_bcs"
FIGURE_DIRECTORY = DATA_DIRECTORY / "figures"

DEFAULT_REPORT_PATHS = {
    "perturbation_pipeline": DATA_DIRECTORY / "combined_perturbation_pipeline_report_v1.json",
    "predictor_scoring": DATA_DIRECTORY / "dummy_predictor_scoring_report_v1.json",
    "pilot_selection": DATA_DIRECTORY / "pp1_pilot_report_v1.json",
    "delta_score": DATA_DIRECTORY / "pp1_pilot_dummy_delta_score_report_v1.json",
    "prediction_flip": DATA_DIRECTORY / "pp1_pilot_dummy_pfr_report_v1.json",
    "invariance_rate": DATA_DIRECTORY / "pp1_pilot_dummy_ir_report_v1.json",
    "false_sensitivity_rate": DATA_DIRECTORY / "pp1_pilot_dummy_fsr_report_v1.json",
    "preliminary_bcs": DATA_DIRECTORY / "pp1_pilot_dummy_bcs_report_v1.json",
    "delta_sensitivity": DATA_DIRECTORY / "pp1_pilot_dummy_delta_sensitivity_report_v1.json",
    "perturbation_count_review": DATA_DIRECTORY / "pp1_pilot_perturbation_count_report_v1.json",
    "manual_variant_inspection": DATA_DIRECTORY / "pp1_manual_variant_inspection_v1.json",
    "preliminary_visualizations": DATA_DIRECTORY / "pp1_pilot_visualization_report_v1.json",
}

DEFAULT_RESULT_PATHS = {
    "pilot_subjects": DATA_DIRECTORY / "pp1_pilot_subjects_v1.csv",
    "pilot_perturbations": DATA_DIRECTORY / "pp1_pilot_perturbations_v1.csv",
    "delta_scores": DATA_DIRECTORY / "pp1_pilot_dummy_delta_scores_v1.csv",
    "prediction_flips": DATA_DIRECTORY / "pp1_pilot_dummy_prediction_flips_v1.csv",
    "p2_invariance": DATA_DIRECTORY / "pp1_pilot_dummy_p2_invariance_v1.csv",
    "p1_insufficient_response": DATA_DIRECTORY / "pp1_pilot_dummy_p1_insufficient_response_v1.csv",
    "perturbation_counts": DATA_DIRECTORY / "pp1_pilot_perturbation_counts_v1.csv",
    "metric_summary_data": FIGURE_DIRECTORY / "pp1_pilot_metric_summary_v1.csv",
    "absolute_delta_distributions": FIGURE_DIRECTORY / "pp1_pilot_absolute_delta_distributions_v1.svg",
    "score_examples": FIGURE_DIRECTORY / "pp1_pilot_score_examples_v1.svg",
    "metric_summary_figure": FIGURE_DIRECTORY / "pp1_pilot_metric_summary_v1.svg",
    "prediction_flip_figure": FIGURE_DIRECTORY / "pp1_pilot_prediction_flip_comparison_v1.svg",
}

_COMMIT_PATTERN = re.compile(r"^[0-9a-f]{40}$")


class RunManifestError(ValueError):
    """Raised when PP1 run provenance is incomplete or inconsistent."""


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _display_path(path: Path) -> str:
    try:
        return path.resolve().relative_to(REPOSITORY_ROOT.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RunManifestError(f"could not read {label}: {path}") from exc
    if not isinstance(value, dict):
        raise RunManifestError(f"{label} must contain a JSON object")
    return value


def _csv_record_count(path: Path) -> int:
    try:
        with path.open("r", encoding="utf-8", newline="") as csv_file:
            reader = csv.reader(csv_file)
            if next(reader, None) is None:
                raise RunManifestError(f"CSV has no header: {path}")
            return sum(1 for _ in reader)
    except OSError as exc:
        raise RunManifestError(f"could not read result CSV: {path}") from exc


def _artifact(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RunManifestError(f"required artifact is missing: {path}")
    value: dict[str, Any] = {
        "path": _display_path(path),
        "format": path.suffix.lstrip("."),
        "sha256": _sha256(path),
        "size_bytes": path.stat().st_size,
    }
    if path.suffix.lower() == ".csv":
        value["record_count"] = _csv_record_count(path)
    return value


def resolve_git_commit(repository_root: str | Path = REPOSITORY_ROOT) -> str:
    """Return the full commit that contains the code used for manifest generation."""

    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=Path(repository_root),
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise RunManifestError("could not resolve the current Git commit") from exc
    commit = completed.stdout.strip().lower()
    if not _COMMIT_PATTERN.fullmatch(commit):
        raise RunManifestError("Git returned an invalid full commit hash")
    return commit


def _require_equal(label: str, *values: object) -> None:
    if not values or any(value != values[0] for value in values[1:]):
        raise RunManifestError(f"inconsistent {label}: {values!r}")


def build_run_manifest(
    *,
    code_commit: str,
    output_path: str | Path = DEFAULT_OUTPUT_PATH,
    created_on: date | None = None,
    report_paths: Mapping[str, Path] = DEFAULT_REPORT_PATHS,
    result_paths: Mapping[str, Path] = DEFAULT_RESULT_PATHS,
) -> dict[str, Any]:
    """Build and write the traceable PP1 pilot run manifest."""

    normalized_commit = code_commit.strip().lower()
    if not _COMMIT_PATTERN.fullmatch(normalized_commit):
        raise RunManifestError("code_commit must be a full 40-character lowercase Git hash")
    if set(report_paths) != set(DEFAULT_REPORT_PATHS):
        raise RunManifestError("report path registry is incomplete or contains unknown entries")
    if set(result_paths) != set(DEFAULT_RESULT_PATHS):
        raise RunManifestError("result path registry is incomplete or contains unknown entries")

    reports = {
        label: _read_json(Path(path), f"{label} report")
        for label, path in report_paths.items()
    }
    validation_reports = tuple(
        report
        for report in reports.values()
        if isinstance(report.get("validation"), dict)
        and "status" in report["validation"]
    )
    if any(report["validation"].get("status") != "PASS" for report in validation_reports):
        raise RunManifestError("one or more source reports did not pass validation")

    config = load_research_config()
    blosum = _read_json(DEFAULT_BLOSUM62_PATH, "BLOSUM62 support manifest")
    predictor_definition = _read_json(
        DEFAULT_DUMMY_DEFINITION_PATH, "dummy predictor definition"
    )
    pilot = reports["pilot_selection"]
    scoring = reports["predictor_scoring"]
    delta = reports["delta_score"]
    count_review = reports["perturbation_count_review"]
    perturbation_pipeline = reports["perturbation_pipeline"]

    pilot_counts = pilot["coverage"]
    delta_counts = delta["counts"]
    review_counts = count_review["counts"]
    _require_equal(
        "pilot peptide count",
        config.pilot_dataset_size,
        pilot_counts["selected_subject_count"],
        delta_counts["unique_subject_count"],
        review_counts["subject_count"],
        _csv_record_count(Path(result_paths["pilot_subjects"])),
    )
    _require_equal(
        "pilot perturbation count",
        pilot_counts["perturbation_count"],
        delta_counts["delta_score_count"],
        review_counts["total_variant_count"],
        _csv_record_count(Path(result_paths["pilot_perturbations"])),
        _csv_record_count(Path(result_paths["delta_scores"])),
    )
    for kind in ("P1", "P2", "P3"):
        _require_equal(
            f"{kind} perturbation count",
            pilot_counts["perturbations_by_type"][kind],
            delta_counts["by_perturbation_type"][kind],
            review_counts["by_perturbation_type"][kind],
        )
    _require_equal(
        "predictor ID",
        predictor_definition["predictor_id"],
        scoring["predictor"]["predictor_id"],
        delta["predictor"]["predictor_id"],
    )
    _require_equal(
        "predictor version",
        predictor_definition["version"],
        scoring["predictor"]["version"],
        delta["predictor"]["version"],
    )
    if not predictor_definition["classification"]["software_testing_only"]:
        raise RunManifestError("the PP1 smoke run must retain its testing-only classification")

    pilot_perturbation_count = int(pilot_counts["perturbation_count"])
    finite_scored_pilot_count = int(delta_counts["delta_score_count"])
    missing_score_count = pilot_perturbation_count - finite_scored_pilot_count
    if missing_score_count < 0:
        raise RunManifestError("scored pilot count exceeds selected perturbation count")

    manifest: dict[str, Any] = {
        "schema_version": RUN_MANIFEST_SCHEMA_VERSION,
        "run_id": RUN_ID,
        "run_date": (created_on or date.today()).isoformat(),
        "classification": {
            "pilot_preliminary": True,
            "software_testing_only": True,
            "scientific_result": False,
            "real_predictor_scoring_completed": False,
            "warning": WARNING,
        },
        "code": {
            "git_commit": normalized_commit,
            "commit_resolution": "git rev-parse HEAD before canonical manifest generation",
        },
        "dataset": {
            "version": pilot["dataset_version"],
            "subject_count": pilot_counts["selected_subject_count"],
            "source_dataset_version": pilot["sources"]["subjects"]["dataset_version"],
        },
        "predictor": {
            "predictor_id": predictor_definition["predictor_id"],
            "display_name": predictor_definition["display_name"],
            "version": predictor_definition["version"],
            "scoring_method": scoring["predictor"]["scoring_method"],
            "software_testing_only": True,
            "scientific_aop_predictor": False,
        },
        "configuration": {
            "source": _artifact(DEFAULT_CONFIG_PATH),
            "random_seed": config.random_seed,
            "redox_residues": list(config.redox_residues),
            "primary_delta": config.primary_delta,
            "sensitivity_deltas": list(config.sensitivity_deltas),
            "blosum62": {
                "support_manifest": _artifact(DEFAULT_BLOSUM62_PATH),
                "matrix": blosum["matrix_name"],
                "minimum_score": blosum["selection_rule"]["minimum_score"],
                "eligible_positions": "non-redox positions only",
                "excluded_candidates": blosum["selection_rule"]["excluded_candidates"],
                "selection": "highest-scoring eligible replacement",
                "tie_break": blosum["selection_rule"]["tie_break"],
            },
        },
        "counts": {
            "peptides": pilot_counts["selected_subject_count"],
            "perturbations_total": pilot_perturbation_count,
            "perturbations_by_type": {
                kind: pilot_counts["perturbations_by_type"][kind]
                for kind in ("P1", "P2", "P3")
            },
        },
        "failures_and_missing_scores": {
            "rejected_full_pipeline_perturbations": perturbation_pipeline["counts"]["rejected_variant_count"],
            "pilot_perturbations_without_finite_scores": missing_score_count,
            "failed_pilot_scores": missing_score_count,
            "derivation": (
                "selected pilot perturbation count minus validated finite DeltaScore count; "
                "the scoring and DeltaScore reports both passed validation"
            ),
        },
        "provenance": {
            "predictor_definition": _artifact(DEFAULT_DUMMY_DEFINITION_PATH),
            "source_reports": {
                label: _artifact(Path(path)) for label, path in report_paths.items()
            },
            "versioned_results": {
                label: _artifact(Path(path)) for label, path in result_paths.items()
            },
        },
        "validation": {
            "status": "PASS",
            "all_available_source_validations_passed": True,
            "dataset_counts_reconciled": True,
            "perturbation_type_counts_reconciled": True,
            "predictor_identity_reconciled": True,
            "all_required_artifacts_exist": True,
            "all_artifacts_have_sha256": True,
            "no_missing_pilot_scores": missing_score_count == 0,
            "software_testing_only_preserved": True,
            "not_a_scientific_result": True,
        },
    }
    if not all(
        value for key, value in manifest["validation"].items() if key != "status"
    ):
        raise RunManifestError("PP1 run manifest validation failed")

    destination = Path(output_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n"
    )
    return manifest


def main() -> None:
    manifest = build_run_manifest(code_commit=resolve_git_commit())
    print(
        f"Wrote {manifest['run_id']} for {manifest['counts']['peptides']} peptides "
        f"and {manifest['counts']['perturbations_total']} perturbations."
    )


if __name__ == "__main__":
    main()
