from __future__ import annotations

from fastapi import APIRouter, Query

from backend.app.schemas.c1_procon import LookupResponse
from backend.app.services.c1_procon.lookup import MAX_QUERY_LENGTH, lookup_peptide

router = APIRouter()


@router.get("/lookup", response_model=LookupResponse)
def lookup(sequence: str = Query(default="", max_length=MAX_QUERY_LENGTH + 50)) -> LookupResponse:
    return lookup_peptide(sequence)
