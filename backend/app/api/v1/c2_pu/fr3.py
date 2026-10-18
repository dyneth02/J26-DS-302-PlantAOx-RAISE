from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.c2_pu import Fr3ExampleResponse, Fr3SummaryResponse
from backend.app.services.c2_pu.fr3 import get_fr3_example, list_fr3_examples

router = APIRouter()


@router.get("/fr3/examples", response_model=Fr3SummaryResponse)
def fr3_examples() -> Fr3SummaryResponse:
    return list_fr3_examples()


@router.get("/fr3/features/{peptide_id}", response_model=Fr3ExampleResponse)
def fr3_features(peptide_id: str) -> Fr3ExampleResponse:
    return get_fr3_example(peptide_id)
