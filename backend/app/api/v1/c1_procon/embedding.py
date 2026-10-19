from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.c1_procon import EmbeddingResponse
from backend.app.services.c1_procon.embedding import get_embedding

router = APIRouter()


@router.get("/embedding", response_model=EmbeddingResponse)
def embedding() -> EmbeddingResponse:
    return get_embedding()
