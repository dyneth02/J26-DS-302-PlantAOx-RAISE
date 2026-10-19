from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.c1_procon import ConfoundsResponse
from backend.app.services.c1_procon.confounds import get_confounds

router = APIRouter()


@router.get("/confounds", response_model=ConfoundsResponse)
def confounds() -> ConfoundsResponse:
    return get_confounds()
