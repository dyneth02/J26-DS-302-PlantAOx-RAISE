from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.artifacts import load_json
from app.live import c2_rnis

router = APIRouter()


class LiveRnisRequest(BaseModel):
    pools: list[str]


@router.get("/summary")
def get_summary():
    return load_json("c2", "c2_summary.json")


@router.get("/pools")
def get_pools():
    return load_json("c2", "challenge_pools.json")


@router.get("/rnis")
def get_rnis():
    return load_json("c2", "rnis_report.json")


@router.get("/classification-metrics")
def get_classification_metrics():
    return load_json("c2", "classification_metrics.json")


@router.get("/calibration")
def get_calibration():
    return load_json("c2", "calibration_metrics.json")


@router.get("/stage-comparison")
def get_stage_comparison():
    return load_json("c2", "stage_comparison.json")


# --- Live RNIS: real MCC/RNIS recomputed for a user-chosen negative-pool combination ---

@router.post("/live-rnis")
def post_live_rnis(body: LiveRnisRequest):
    try:
        return c2_rnis.live_rnis(body.pools)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/live-calibration")
def post_live_calibration(body: LiveRnisRequest):
    try:
        return c2_rnis.live_calibration(body.pools)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
