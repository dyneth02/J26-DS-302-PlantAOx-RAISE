from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.c1_procon import DatasetResponse
from backend.app.services.c1_procon.dataset import get_dataset

router = APIRouter()


@router.get("/dataset", response_model=DatasetResponse)
def dataset() -> DatasetResponse:
    return get_dataset()
