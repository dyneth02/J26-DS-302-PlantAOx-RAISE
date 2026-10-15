from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.artifacts import load_json
from app.live import c3_perturbation

router = APIRouter()

DEFAULT_PREDICTOR = "c2_logreg"


class LivePerturbationRequest(BaseModel):
    sequence: str


@router.get("/summary")
def get_summary():
    return load_json("c3", "c3_summary.json")


@router.get("/predictors")
def get_predictors():
    return load_json("c3", "predictors.json")


@router.get("/reliability-flags")
def get_reliability_flags():
    return load_json("c3", "predictor_reliability_flags.json")


@router.get("/bcs")
def get_bcs(predictor: str = DEFAULT_PREDICTOR):
    return load_json("c3", f"bcs_report__{predictor}.json")


@router.get("/example-perturbation")
def get_example_perturbation(predictor: str = DEFAULT_PREDICTOR):
    return load_json("c3", f"example_perturbation__{predictor}.json")


@router.get("/perturbation-results")
def get_perturbation_results(predictor: str = DEFAULT_PREDICTOR):
    return load_json("c3", f"perturbation_results__{predictor}.json")


# --- Live perturbation scoring: user-supplied sequence, c2_logreg only ---

@router.post("/live-perturbation")
def post_live_perturbation(body: LivePerturbationRequest):
    try:
        return c3_perturbation.live_perturbation(body.sequence)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
