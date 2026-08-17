from fastapi import APIRouter

router = APIRouter()

PROJECT_META = {
    "project": "PlantAOx-RAISE",
    "full_name": (
        "Reliable Learning, Evidence-backed Inflation scoring, and Faithfulness "
        "auditing Framework for plant antioxidant peptide discovery"
    ),
    "problem_statement": (
        "Published antioxidant peptide (AOP) predictors are typically benchmarked with "
        "positives-vs-random-negatives setups, which inflates apparent performance, are "
        "rarely audited for physicochemical faithfulness, and rarely report an "
        "applicability-domain check before ranking novel candidates. PlantAOx-RAISE is a "
        "reliability framework, not a new predictor: it audits and calibrates existing "
        "AOP discovery methods and applies the resulting reliability signals to plant "
        "digestome screening."
    ),
    "components": [
        {
            "id": "C1",
            "name": "AOP-ProCon",
            "title": "Mechanism-Aware Positive-Only Prototype Contrastive Representation Learning",
            "novelty": "Positive-only, mechanism-tier-aware representation space and the AOP-BenchPos benchmark.",
            "route": "/c1",
        },
        {
            "id": "C2",
            "name": "PU-AOP",
            "title": "Evidence-Tiered PU Learning and Random-Negative Inflation Scoring",
            "novelty": "RNIS as a formal metric for how much easy-negative benchmarking inflates reported performance.",
            "route": "/c2",
        },
        {
            "id": "C3",
            "name": "AOP-BCS",
            "title": "Perturbation-Based Faithfulness Auditing",
            "novelty": "Controlled alanine-scan / BLOSUM62 / random perturbations and the BCS behavioural-consistency score.",
            "route": "/c3",
        },
        {
            "id": "C4",
            "name": "PlantAOP-Screen",
            "title": "Plant Digestome Screening with Applicability-Domain Abstention",
            "novelty": "AD-tiered abstention, PARRS/PDSS/ARR, and evidence-backed candidate cards.",
            "route": "/c4",
        },
    ],
    "team_ownership": [
        {"component": "C1 AOP-ProCon", "responsibility": "Positive-only representation and AOP-BenchPos"},
        {"component": "C2 PU-AOP", "responsibility": "PU classifier and RNIS"},
        {"component": "C3 AOP-BCS", "responsibility": "Perturbation faithfulness audit"},
        {"component": "C4 PlantAOP-Screen", "responsibility": "Plant digestome screening and AD abstention"},
    ],
    "prototype_disclaimer": (
        "This is a proposal-stage prototype, not the final research system. Component "
        "curation, descriptors, embeddings, the trained classifier, the perturbation audit, "
        "and the screening pipeline all run on real data. The 2D embedding layout, negative "
        "sampling depth, and plant proteome size are reduced for a fast, offline demo -- see "
        "each page's data-mode banner for specifics."
    ),
}


@router.get("/project")
def get_project_meta():
    return PROJECT_META
