from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.c1_procon import OverviewResponse
from backend.app.services.c1_procon.overview import get_overview

router = APIRouter()


@router.get("/overview", response_model=OverviewResponse)
def overview() -> OverviewResponse:
    return get_overview()
