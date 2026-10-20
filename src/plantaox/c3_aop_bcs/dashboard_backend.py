"""Standalone artifact-backed API and web server for the C3 AOP-BCS dashboard.

The module deliberately lives inside Component 3.  ``router`` can be mounted by
the shared API later, while ``app`` is immediately runnable without changing
the repository-wide backend or another component's files.
"""

from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Final, Literal

from fastapi import APIRouter, FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles


COMPONENT_DIRECTORY: Final = Path(__file__).resolve().parent
REPOSITORY_ROOT: Final = COMPONENT_DIRECTORY.parents[2]
FRONTEND_DIRECTORY: Final = COMPONENT_DIRECTORY / "frontend"

SOURCE_PATHS: Final[dict[str, str]] = {
    "cleaning": "data/processed/c3_aop_bcs/sequence_cleaning_report_v1.json",
    "deduplication": "data/processed/c3_aop_bcs/cd_hit_deduplication_report_v1.json",
    "eligibility": "data/processed/c3_aop_bcs/redox_eligibility_report_v1.json",
    "perturbations": "data/processed/c3_aop_bcs/combined_perturbation_pipeline_report_v1.json",
    "pilot": "data/processed/c3_aop_bcs/pp1_pilot_report_v1.json",
    "pfr": "data/processed/c3_aop_bcs/pp1_pilot_dummy_pfr_report_v1.json",
    "bcs": "data/processed/c3_aop_bcs/pp1_pilot_dummy_bcs_report_v1.json",
    "sensitivity": "data/processed/c3_aop_bcs/pp1_pilot_dummy_delta_sensitivity_report_v1.json",
    "countReview": "data/processed/c3_aop_bcs/pp1_pilot_perturbation_count_report_v1.json",
    "inspection": "data/processed/c3_aop_bcs/pp1_manual_variant_inspection_v1.json",
    "manifest": "data/processed/c3_aop_bcs/pp1_pilot_run_manifest_v1.json",
    "predictorPriority": "src/plantaox/c3_aop_bcs/predictor_priority_v1.json",
}

FIGURE_PATHS: Final[tuple[str, ...]] = (
    "data/processed/c3_aop_bcs/figures/pp1_pilot_absolute_delta_distributions_v1.svg",
    "data/processed/c3_aop_bcs/figures/pp1_pilot_score_examples_v1.svg",
    "data/processed/c3_aop_bcs/figures/pp1_pilot_metric_summary_v1.svg",
    "data/processed/c3_aop_bcs/figures/pp1_pilot_prediction_flip_comparison_v1.svg",
)
FIGURE_LOOKUP: Final = {Path(path).name: path for path in FIGURE_PATHS}

DashboardSection = Literal[
    "overview", "dataset", "perturbations", "metrics", "explorer", "predictors", "evidence"
]


class DashboardArtifactError(RuntimeError):
    """Raised when authoritative dashboard evidence is absent or inconsistent."""


def _repository_path(relative_path: str, repository_root: Path) -> Path:
    path = (repository_root / Path(relative_path)).resolve()
    if repository_root.resolve() not in path.parents:
        raise DashboardArtifactError(f"Artifact path escapes the repository: {relative_path}")
    return path


def _load_json(relative_path: str, repository_root: Path) -> dict[str, Any]:
    path = _repository_path(relative_path, repository_root)
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise DashboardArtifactError(f"Required C3 artifact is missing: {relative_path}") from error
    except json.JSONDecodeError as error:
        raise DashboardArtifactError(f"Required C3 artifact is invalid JSON: {relative_path}") from error
    if not isinstance(value, dict):
        raise DashboardArtifactError(f"Required C3 artifact must contain a JSON object: {relative_path}")
    return value


def _checksum(relative_path: str, repository_root: Path) -> str:
    path = _repository_path(relative_path, repository_root)
    try:
        return sha256(path.read_bytes()).hexdigest()
    except FileNotFoundError as error:
        raise DashboardArtifactError(f"Required C3 artifact is missing: {relative_path}") from error


def _validate_sources(source: dict[str, dict[str, Any]]) -> None:
    classification = source["manifest"].get("classification", {})
    if classification.get("software_testing_only") is not True:
        raise DashboardArtifactError("Run manifest must retain the software-testing-only classification.")
    if classification.get("scientific_result") is not False:
        raise DashboardArtifactError("Dummy results must not be classified as scientific.")
    if classification.get("real_predictor_scoring_completed") is not False:
        raise DashboardArtifactError("Dashboard evidence unexpectedly claims completed real-predictor scoring.")

    counts = source["manifest"].get("counts", {})
    by_type = counts.get("perturbations_by_type", {})
    if sum(by_type.get(kind, 0) for kind in ("P1", "P2", "P3")) != counts.get("perturbations_total"):
        raise DashboardArtifactError("Pilot perturbation counts do not reconcile.")
    production_counts = source["perturbations"].get("counts", {})
    accepted_by_type = production_counts.get("accepted_by_perturbation_type", {})
    if (
        production_counts.get("rejected_variant_count") != 0
        or sum(accepted_by_type.get(kind, 0) for kind in ("P1", "P2", "P3"))
        != production_counts.get("accepted_variant_count")
    ):
        raise DashboardArtifactError("The combined perturbation artifact does not reconcile as fully accepted.")
    if source["bcs"].get("validation", {}).get("status") != "PASS":
        raise DashboardArtifactError("The preliminary BCS artifact has not passed validation.")

    primary_rows = [row for row in source["sensitivity"].get("threshold_results", []) if row.get("is_primary")]
    if len(primary_rows) != 1:
        raise DashboardArtifactError("Exactly one primary delta-sensitivity result is required.")
    examples = source["inspection"].get("examples", [])
    if len(examples) != 6 or {row.get("perturbation_type") for row in examples} != {"P1", "P2", "P3"}:
        raise DashboardArtifactError("The dashboard requires six inspected examples spanning P1, P2, and P3.")


def build_dashboard_payload(repository_root: Path = REPOSITORY_ROOT) -> dict[str, Any]:
    """Build the browser contract directly from the versioned C3 evidence."""

    source = {key: _load_json(path, repository_root) for key, path in SOURCE_PATHS.items()}
    _validate_sources(source)
    manifest = source["manifest"]
    pfr_by_type = source["pfr"]["pfr"]["by_perturbation_type"]

    payload: dict[str, Any] = {
        "schemaVersion": "1.1",
        "apiVersion": "c3-dashboard-api-v1",
        "evidenceDate": manifest["run_date"],
        "classification": manifest["classification"],
        "configuration": {
            "seed": manifest["configuration"]["random_seed"],
            "redoxResidues": manifest["configuration"]["redox_residues"],
            "primaryDelta": manifest["configuration"]["primary_delta"],
            "sensitivityDeltas": manifest["configuration"]["sensitivity_deltas"],
            "blosumMinimum": manifest["configuration"]["blosum62"]["minimum_score"],
        },
        "overview": {
            "pilotSubjects": manifest["counts"]["peptides"],
            "pilotVariants": manifest["counts"]["perturbations_total"],
            "fullEligibleSubjects": source["perturbations"]["counts"]["input_peptide_count"],
            "fullVariants": source["perturbations"]["counts"]["accepted_variant_count"],
        },
        "datasetFunnel": [
            {"label": "Standardized candidates", "count": source["cleaning"]["counts"]["original_count"], "detail": "merged source records"},
            {"label": "Clean unique sequences", "count": source["cleaning"]["counts"]["retained_count"], "detail": "valid 3–50 aa peptides"},
            {"label": "CD-HIT representatives", "count": source["deduplication"]["counts"]["representative_count"], "detail": "90% identity clusters"},
            {"label": "Redox-eligible subjects", "count": source["eligibility"]["counts"]["eligible_count"], "detail": "contains W, Y, H, M or C"},
            {"label": "PP1 pilot subjects", "count": source["pilot"]["coverage"]["selected_subject_count"], "detail": "seeded coverage sample"},
        ],
        "coverage": {
            "lengthRange": f'{source["pilot"]["coverage"]["sequence_length_min"]}–{source["pilot"]["coverage"]["sequence_length_max"]} aa',
            "distinctLengths": source["pilot"]["coverage"]["distinct_sequence_lengths"],
            "redoxResidues": list(source["pilot"]["coverage"]["redox_residue_subject_counts"]),
            "evidenceTiers": list(source["pilot"]["coverage"]["evidence_tier_counts"]),
            "maximumVariantShare": source["countReview"]["dominance_review"]["maximum_contributor"]["variant_share"],
        },
        "perturbations": [
            {
                "id": "P1", "title": "Redox disruption", "subtitle": "Alanine scanning",
                "question": "Does the score change when a redox-active residue is removed?",
                "rule": "Replace each W/Y/H/M/C position with alanine.",
                "fullCount": source["perturbations"]["counts"]["accepted_by_perturbation_type"]["P1"],
                "pilotCount": manifest["counts"]["perturbations_by_type"]["P1"], "tone": "coral",
            },
            {
                "id": "P2", "title": "Conservative control", "subtitle": "BLOSUM62-guided",
                "question": "Does the score remain stable under a similar-residue edit?",
                "rule": f'Use the highest eligible BLOSUM62 replacement with score ≥ {manifest["configuration"]["blosum62"]["minimum_score"]}.',
                "fullCount": source["perturbations"]["counts"]["accepted_by_perturbation_type"]["P2"],
                "pilotCount": manifest["counts"]["perturbations_by_type"]["P2"], "tone": "teal",
            },
            {
                "id": "P3", "title": "Random control", "subtitle": "Seeded substitution",
                "question": "How does the response compare with a reproducible random edit?",
                "rule": f'Choose a different standard residue using master seed {manifest["configuration"]["random_seed"]}.',
                "fullCount": source["perturbations"]["counts"]["accepted_by_perturbation_type"]["P3"],
                "pilotCount": manifest["counts"]["perturbations_by_type"]["P3"], "tone": "violet",
            },
        ],
        "metrics": {
            "primaryDelta": manifest["configuration"]["primary_delta"],
            "invarianceRate": source["bcs"]["components"]["invariance_rate"]["value"],
            "invariantCount": source["bcs"]["components"]["invariance_rate"]["invariant_p2_count"],
            "invariantDenominator": source["bcs"]["components"]["invariance_rate"]["evaluated_p2_count"],
            "falseSensitivityRate": source["bcs"]["components"]["false_sensitivity_rate"]["value"],
            "insufficientCount": source["bcs"]["components"]["false_sensitivity_rate"]["insufficient_response_p1_count"],
            "insufficientDenominator": source["bcs"]["components"]["false_sensitivity_rate"]["evaluated_p1_count"],
            "preliminaryBcs": source["bcs"]["result"]["preliminary_bcs"],
            "overallPfr": source["pfr"]["pfr"]["overall"]["prediction_flip_rate"],
            "flipCount": source["pfr"]["pfr"]["overall"]["flip_count"],
            "flipDenominator": source["pfr"]["pfr"]["overall"]["perturbation_count"],
            "pfrByType": {key: value["prediction_flip_rate"] for key, value in pfr_by_type.items()},
        },
        "sensitivity": [
            {"delta": row["delta"], "primary": row["is_primary"], "ir": row["invariance_rate"], "fsr": row["false_sensitivity_rate"], "bcs": row["preliminary_bcs"]}
            for row in source["sensitivity"]["threshold_results"]
        ],
        "examples": source["inspection"]["examples"],
        "predictors": [
            {
                "id": predictor["predictor_id"], "name": predictor["display_name"],
                "tier": predictor["tier"], "order": predictor["integration_order"],
                "readiness": predictor["readiness"], "status": predictor["integration_status"],
                "rationale": predictor["rationale"],
            }
            for predictor in source["predictorPriority"]["priorities"]
        ],
        "provenance": {
            "runId": manifest["run_id"], "runDate": manifest["run_date"],
            "datasetVersion": manifest["dataset"]["version"],
            "predictorVersion": f'{manifest["predictor"]["predictor_id"]}@{manifest["predictor"]["version"]}',
            "codeCommit": manifest["code"]["git_commit"],
            "validationStatus": manifest["validation"]["status"],
            "missingScores": manifest["failures_and_missing_scores"]["pilot_perturbations_without_finite_scores"],
            "sourceArtifacts": [
                {"label": label, "path": path, "sha256": _checksum(path, repository_root)}
                for label, path in SOURCE_PATHS.items()
            ],
        },
        "figures": [
            {
                "sourcePath": path,
                "file": f'/api/v1/c3/figures/{Path(path).name}',
                "sha256": _checksum(path, repository_root),
            }
            for path in FIGURE_PATHS
        ],
    }
    return payload


def _payload_or_503() -> dict[str, Any]:
    try:
        return build_dashboard_payload()
    except DashboardArtifactError as error:
        raise HTTPException(status_code=503, detail=str(error)) from error


router = APIRouter(prefix="/api/v1/c3", tags=["c3-aop-bcs"])


@router.get("/health")
def health() -> dict[str, Any]:
    payload = _payload_or_503()
    return {
        "status": "ok",
        "component": "c3_aop_bcs",
        "api_version": payload["apiVersion"],
        "run_id": payload["provenance"]["runId"],
        "artifact_count": len(payload["provenance"]["sourceArtifacts"]),
    }


@router.get("/dashboard")
def dashboard() -> dict[str, Any]:
    return _payload_or_503()


@router.get("/sections/{section}")
def dashboard_section(section: DashboardSection) -> dict[str, Any]:
    payload = _payload_or_503()
    section_keys = {
        "overview": ("overview", "configuration", "classification", "provenance"),
        "dataset": ("datasetFunnel", "coverage", "overview", "provenance"),
        "perturbations": ("perturbations", "configuration", "overview", "classification"),
        "metrics": ("metrics", "sensitivity", "figures", "classification"),
        "explorer": ("examples", "perturbations", "classification"),
        "predictors": ("predictors", "classification"),
        "evidence": ("provenance", "figures", "classification"),
    }
    return {"section": section, **{key: payload[key] for key in section_keys[section]}}


@router.get("/figures/{filename}", response_class=FileResponse)
def figure(filename: str) -> FileResponse:
    relative_path = FIGURE_LOOKUP.get(filename)
    if relative_path is None:
        raise HTTPException(status_code=404, detail="Unknown C3 figure.")
    path = _repository_path(relative_path, REPOSITORY_ROOT)
    if not path.is_file():
        raise HTTPException(status_code=404, detail="C3 figure is missing.")
    return FileResponse(path, media_type="image/svg+xml", headers={"Cache-Control": "no-store"})


app = FastAPI(
    title="PlantAOx-RAISE Component 3 Dashboard",
    description="Artifact-backed API and dashboard for the AOP-BCS PP1 software pilot.",
    version="1.0.0",
)
app.include_router(router)
app.mount("/assets", StaticFiles(directory=FRONTEND_DIRECTORY / "assets"), name="c3-assets")


@app.get("/app.js", include_in_schema=False, response_class=FileResponse)
def frontend_script() -> FileResponse:
    return FileResponse(FRONTEND_DIRECTORY / "app.js", media_type="text/javascript", headers={"Cache-Control": "no-store"})


@app.get("/styles.css", include_in_schema=False, response_class=FileResponse)
def frontend_styles() -> FileResponse:
    return FileResponse(FRONTEND_DIRECTORY / "styles.css", media_type="text/css", headers={"Cache-Control": "no-store"})


@app.get("/", include_in_schema=False, response_class=FileResponse)
def frontend_index() -> FileResponse:
    return FileResponse(FRONTEND_DIRECTORY / "index.html", media_type="text/html", headers={"Cache-Control": "no-store"})


def main() -> None:
    """Run the self-contained C3 dashboard server."""

    import uvicorn

    uvicorn.run("plantaox.c3_aop_bcs.dashboard_backend:app", host="127.0.0.1", port=4313, reload=False)


if __name__ == "__main__":
    main()
