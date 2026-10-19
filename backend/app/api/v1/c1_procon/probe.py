from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.c1_procon import ProbeResponse
from backend.app.services.c1_procon.probe import get_probe

router = APIRouter()


@router.get("/probe", response_model=ProbeResponse)
def probe() -> ProbeResponse:
    return get_probe()
