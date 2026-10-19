from __future__ import annotations

from fastapi import APIRouter

from backend.app.api.v1.c1_procon import artifacts, confounds, dataset, embedding, lookup, overview, probe, retrieval

router = APIRouter(prefix="/c1", tags=["c1-procon"])
router.include_router(overview.router)
router.include_router(dataset.router)
router.include_router(embedding.router)
router.include_router(lookup.router)
router.include_router(retrieval.router)
router.include_router(probe.router)
router.include_router(confounds.router)
router.include_router(artifacts.router)
