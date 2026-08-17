from fastapi import APIRouter

from app.artifacts import load_json

router = APIRouter()


@router.get("/summary")
def get_summary():
    return load_json("c4", "c4_summary.json")


@router.get("/candidates")
def get_candidates():
    return load_json("c4", "plant_candidates.json")


@router.get("/ad-summary")
def get_ad_summary():
    return load_json("c4", "ad_summary.json")


@router.get("/parrs")
def get_parrs():
    return load_json("c4", "parrs_report.json")


@router.get("/pdss")
def get_pdss():
    return load_json("c4", "pdss_report.json")


@router.get("/arr")
def get_arr():
    return load_json("c4", "arr_report.json")


@router.get("/evidence-cards")
def get_evidence_cards():
    return load_json("c4", "evidence_cards.json")
