from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.c2_pu import OverviewResponse
from backend.app.services.c2_pu.overview import get_overview

router = APIRouter()


@router.get("/overview", response_model=OverviewResponse)
def overview() -> OverviewResponse:
    return get_overview()
