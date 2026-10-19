from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query
from fastapi.responses import Response

from backend.app.schemas.c4_screen import (
    C4MetaResponse,
    CandidateCardsResponse,
    CandidateDetail,
    CandidatePage,
    AbstainedPage,
    FunnelRow,
    HistogramResponse,
    LengthsResponse,
    TierSummaryResponse,
)
from backend.app.services.c4_screen import artifacts

router = APIRouter(prefix="/c4", tags=["c4-screen"])
Plant = Literal["soybean", "rice", "rapeseed", "olive"]


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "component": "c4_screen"}


@router.get("/meta", response_model=C4MetaResponse)
def meta() -> dict:
    return artifacts.get_meta()


@router.get("/funnel", response_model=list[FunnelRow])
def funnel() -> list[dict]:
    return artifacts.get_funnel()


@router.get("/tiers/summary", response_model=TierSummaryResponse)
def tiers_summary(plant: Plant | None = None) -> dict:
    return artifacts.get_tier_summary(plant)


@router.get("/ad/histogram", response_model=HistogramResponse)
def ad_histogram(plant: Plant | None = None, bins: int = Query(default=30, ge=5, le=100)) -> dict:
    return artifacts.get_ad_histogram(plant=plant, bins=bins)


@router.get("/lengths", response_model=LengthsResponse)
def lengths() -> dict:
    return artifacts.get_lengths()


@router.get("/candidates", response_model=CandidatePage)
def candidates(
    plant: Plant | None = None,
    tier: int | None = Query(default=None, ge=1, le=3),
    len_min: int | None = Query(default=None, ge=3, le=20),
    len_max: int | None = Query(default=None, ge=3, le=20),
    q: str | None = Query(default=None, max_length=64),
    sort: Literal["sequence", "peptide_id", "plant", "tier", "length", "d_AD", "CS", "rank"] = "rank",
    order: Literal["asc", "desc"] = "asc",
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> dict:
    if len_min is not None and len_max is not None and len_min > len_max:
        from fastapi import HTTPException

        raise HTTPException(status_code=422, detail="len_min must be less than or equal to len_max")
    return artifacts.query_candidates(
        plant=plant, tier=tier, len_min=len_min, len_max=len_max, q=q,
        sort=sort, order=order, page=page, page_size=page_size,
    )


@router.get("/candidates/{peptide_id}", response_model=CandidateDetail)
def candidate_detail(peptide_id: str) -> dict:
    return artifacts.get_candidate(peptide_id)


@router.get("/cards/{plant}", response_model=CandidateCardsResponse)
def cards(plant: Plant, limit: int = Query(default=50, ge=1, le=50)) -> dict:
    return {"plant": plant, "cards": artifacts.get_cards(plant, limit)}


@router.get("/abstained/{plant}", response_model=AbstainedPage)
def abstained(
    plant: Plant,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> dict:
    return artifacts.get_abstained(plant, page, page_size)


@router.get("/export/cards.csv")
def export_cards(plant: Plant | None = None) -> Response:
    csv = artifacts.cards_csv(plant)
    return Response(
        content=csv,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="c4_screen_cards.csv"'},
    )
