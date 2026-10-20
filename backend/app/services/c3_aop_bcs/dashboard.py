"""Read-only adapter from validated C3 evidence to the shared API."""

from __future__ import annotations

from pathlib import Path

from backend.app.core import plantaox_bridge  # noqa: F401  (adds src/ to sys.path)
from backend.app.core.config import get_settings
from backend.app.core.errors import ArtifactUnavailableError, ResourceNotFoundError
from backend.app.schemas.c3_aop_bcs import (
    C3HealthResponse,
    DashboardResponse,
    DashboardSectionResponse,
)
from plantaox.c3_aop_bcs.dashboard_backend import (
    DashboardArtifactError,
    FIGURE_LOOKUP,
    build_dashboard_payload,
)

SECTION_KEYS: dict[str, tuple[str, ...]] = {
    "overview": ("overview", "configuration", "classification", "provenance"),
    "dataset": ("datasetFunnel", "coverage", "overview", "provenance"),
    "perturbations": ("perturbations", "configuration", "overview", "classification"),
    "metrics": ("metrics", "sensitivity", "figures", "classification"),
    "explorer": ("examples", "perturbations", "classification"),
    "predictors": ("predictors", "classification"),
    "evidence": ("provenance", "figures", "classification"),
}


def _payload() -> DashboardResponse:
    try:
        payload = build_dashboard_payload(get_settings().repo_root)
    except DashboardArtifactError as exc:
        raise ArtifactUnavailableError(str(exc)) from exc
    return DashboardResponse.model_validate(payload)


def get_health() -> C3HealthResponse:
    dashboard = _payload()
    return C3HealthResponse(
        status="ok",
        component="c3_aop_bcs",
        api_version=dashboard.apiVersion,
        run_id=dashboard.provenance.runId,
        artifact_count=len(dashboard.provenance.sourceArtifacts),
    )


def get_dashboard() -> DashboardResponse:
    return _payload()


def get_section(section: str) -> DashboardSectionResponse:
    keys = SECTION_KEYS.get(section)
    if keys is None:
        raise ResourceNotFoundError(f"Unknown C3 dashboard section: {section!r}")
    payload = _payload().model_dump()
    return DashboardSectionResponse.model_validate(
        {"section": section, **{key: payload[key] for key in keys}}
    )


def get_figure_path(filename: str) -> Path:
    relative_path = FIGURE_LOOKUP.get(filename)
    if relative_path is None:
        raise ResourceNotFoundError(f"Unknown C3 figure: {filename!r}")
    root = get_settings().repo_root.resolve()
    path = (root / relative_path).resolve()
    if root not in path.parents:
        raise ArtifactUnavailableError("C3 figure path escapes the repository.")
    if not path.is_file():
        raise ArtifactUnavailableError(
            f"Required C3 figure is missing: {filename}", artifact_path=str(path)
        )
    return path

