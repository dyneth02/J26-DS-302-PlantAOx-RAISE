from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.c2_pu import Fr1SummaryResponse
from backend.app.services.c2_pu.fr1 import get_fr1_summary

router = APIRouter()


@router.get("/fr1/summary", response_model=Fr1SummaryResponse)
def fr1_summary() -> Fr1SummaryResponse:
    return get_fr1_summary()
