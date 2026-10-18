from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.c2_pu import ArtifactStatusResponse
from backend.app.services.c2_pu.status import get_artifact_status

router = APIRouter()


@router.get("/artifacts/status", response_model=ArtifactStatusResponse)
def artifacts_status() -> ArtifactStatusResponse:
    return get_artifact_status()
