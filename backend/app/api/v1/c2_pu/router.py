from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.v1.c2_pu import artifacts, fr1, fr2, fr3, fr4, overview

router = APIRouter(prefix="/c2", tags=["c2-pu"])
router.include_router(overview.router)
router.include_router(fr1.router)
router.include_router(fr2.router)
router.include_router(fr3.router)
router.include_router(fr4.router)
router.include_router(artifacts.router)
