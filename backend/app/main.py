"""PlantAOx-RAISE PP1 demonstration API.

Entry point stays small: CORS + exception handlers + the single composed
v1 router. Research logic lives in ``services/<component>/``, never here.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.v1.router import router as api_v1_router
from backend.app.core.config import get_settings
from backend.app.core.errors import register_exception_handlers

app = FastAPI(
    title="PlantAOx-RAISE PP1 API",
    description="Read-only demonstration API over accepted PlantAOx-RAISE research artifacts.",
    version="0.1.0",
)

settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_v1_router)
