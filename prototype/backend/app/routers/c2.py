from fastapi import APIRouter

from app.artifacts import load_json

router = APIRouter()


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
