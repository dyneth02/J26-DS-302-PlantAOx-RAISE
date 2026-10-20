"""Shared API composition root.

Adding a new component's router is the only thing a teammate needs to do
here: import their router module and ``include_router`` it, exactly like
``c2_pu.router`` below. Nothing in this file is C2-specific.
"""

from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.v1 import health
from backend.app.api.v1.c4_screen.router import router as c4_screen_router
from backend.app.api.v1.c1_procon.router import router as c1_procon_router
from backend.app.api.v1.c2_pu.router import router as c2_pu_router

router = APIRouter(prefix="/api/v1")
router.include_router(health.router)
router.include_router(c1_procon_router)
router.include_router(c2_pu_router)
router.include_router(c4_screen_router)
