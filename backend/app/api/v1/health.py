from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.common import ComponentInfo, HealthResponse

router = APIRouter(tags=["platform"])

COMPONENTS: list[ComponentInfo] = [
    ComponentInfo(
        id="c1_procon",
        code="C1",
        title="AOP-ProCon",
        owner_note="Mechanism-aware representation and prototype analysis",
        status="not_integrated",
    ),
    ComponentInfo(
        id="c2_pu",
        code="C2",
        title="PU-AOP",
        owner_note="Positive-unlabeled antioxidant peptide classification and curriculum learning",
        status="implemented",
        base_path="/api/v1/c2",
    ),
    ComponentInfo(
        id="c3_aop_bcs",
        code="C3",
        title="AOP-BCS",
        owner_note="Predictor behavioral-consistency and reliability auditing",
        status="not_integrated",
    ),
    ComponentInfo(
        id="c4_plantaop_screen",
        code="C4",
        title="PlantAOP-Screen",
        owner_note="Plant-derived peptide screening and reliability-aware prioritization",
        status="implemented",
        base_path="/c4",
    ),
]


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok", service="plantaox-raise-api")


@router.get("/components", response_model=list[ComponentInfo])
def components() -> list[ComponentInfo]:
    return COMPONENTS
