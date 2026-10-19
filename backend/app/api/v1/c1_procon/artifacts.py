from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.c1_procon import ArtifactStatusResponse
from backend.app.services.c1_procon.status import get_artifact_status

router = APIRouter()


@router.get("/artifacts/status", response_model=ArtifactStatusResponse)
def artifact_status() -> ArtifactStatusResponse:
    return get_artifact_status()
