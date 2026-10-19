from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.c1_procon import RetrievalResponse
from backend.app.services.c1_procon.retrieval import get_retrieval

router = APIRouter()


@router.get("/retrieval", response_model=RetrievalResponse)
def retrieval() -> RetrievalResponse:
    return get_retrieval()
