from __future__ import annotations

from fastapi import APIRouter, Path

from backend.app.schemas.c2_pu import Fr2FoldChallengesResponse, Fr2PoolsResponse
from backend.app.services.c2_pu.fr2 import N_FOLDS, get_fr2_fold_challenges, get_fr2_pools

router = APIRouter()


@router.get("/fr2/pools", response_model=Fr2PoolsResponse)
def fr2_pools() -> Fr2PoolsResponse:
    return get_fr2_pools()


@router.get("/fr2/c3-folds/{fold_id}", response_model=Fr2FoldChallengesResponse)
def fr2_c3_fold(fold_id: int = Path(..., ge=0, lt=N_FOLDS)) -> Fr2FoldChallengesResponse:
    return get_fr2_fold_challenges(fold_id)
