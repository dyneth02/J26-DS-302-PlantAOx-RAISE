from __future__ import annotations

from typing import Literal

from fastapi import APIRouter
from fastapi.responses import FileResponse

from backend.app.schemas.c3_aop_bcs import (
    C3HealthResponse,
    DashboardResponse,
    DashboardSectionResponse,
)
from backend.app.services.c3_aop_bcs import dashboard

DashboardSection = Literal[
    "overview", "dataset", "perturbations", "metrics", "explorer", "predictors", "evidence"
]

router = APIRouter(prefix="/c3", tags=["c3-aop-bcs"])


@router.get("/health", response_model=C3HealthResponse)
def health() -> C3HealthResponse:
    return dashboard.get_health()


@router.get("/dashboard", response_model=DashboardResponse)
def dashboard_payload() -> DashboardResponse:
    return dashboard.get_dashboard()


@router.get("/sections/{section}", response_model=DashboardSectionResponse)
def dashboard_section(section: DashboardSection) -> DashboardSectionResponse:
    return dashboard.get_section(section)


@router.get("/figures/{filename}", response_class=FileResponse)
def figure(filename: str) -> FileResponse:
    return FileResponse(
        dashboard.get_figure_path(filename),
        media_type="image/svg+xml",
        headers={"Cache-Control": "no-store"},
    )
