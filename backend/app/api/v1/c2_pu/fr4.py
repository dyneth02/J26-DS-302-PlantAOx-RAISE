from __future__ import annotations

from fastapi import APIRouter

from backend.app.schemas.c2_pu import CurriculumResponse, Fr4EvaluationResponse
from backend.app.services.c2_pu.curriculum import get_curriculum
from backend.app.services.c2_pu.fr4 import get_fr4_evaluation

router = APIRouter()


@router.get("/fr4/evaluation", response_model=Fr4EvaluationResponse)
def fr4_evaluation() -> Fr4EvaluationResponse:
    return get_fr4_evaluation()


@router.get("/fr4/curriculum", response_model=CurriculumResponse)
def fr4_curriculum() -> CurriculumResponse:
    return get_curriculum()
