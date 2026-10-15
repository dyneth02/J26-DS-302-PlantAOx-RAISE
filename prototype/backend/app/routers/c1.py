from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.artifacts import load_json
from app.live import c1_retrieval

router = APIRouter()


class LiveRetrievalRequest(BaseModel):
    query_id: str
    top_k: int = 10


@router.get("/summary")
def get_summary():
    return load_json("c1", "c1_summary.json")


@router.get("/umap")
def get_umap():
    return load_json("c1", "c1_umap_coordinates.json")


@router.get("/prototypes")
def get_prototypes():
    return load_json("c1", "c1_prototypes.json")


@router.get("/retrieval")
def get_retrieval():
    return load_json("c1", "c1_retrieval_demo.json")


@router.get("/cloud-stats")
def get_cloud_stats():
    return load_json("c1", "c1_embedding_cloud_stats.json")


@router.get("/data-sufficiency")
def get_data_sufficiency():
    return load_json("c1", "c1_data_sufficiency_alert.json")


@router.get("/scaling-ablation")
def get_scaling_ablation():
    return load_json("c1", "c1_scaling_ablation.json")


# --- Real trained model (Google Colab run, Phase 4/4v2/5/5b/5.3) ---

@router.get("/trained-summary")
def get_trained_summary():
    return load_json("c1", "c1_trained_summary.json")


@router.get("/trained-embedding")
def get_trained_embedding():
    return load_json("c1", "c1_trained_embedding_coordinates.json")


@router.get("/trained-prototypes")
def get_trained_prototypes():
    return load_json("c1", "c1_trained_prototypes.json")


@router.get("/trained-retrieval")
def get_trained_retrieval():
    return load_json("c1", "c1_trained_retrieval_demo.json")


@router.get("/ablation-comparison")
def get_ablation_comparison():
    return load_json("c1", "c1_ablation_comparison.json")


@router.get("/training-history")
def get_training_history():
    return load_json("c1", "c1_training_history.json")


@router.get("/statistical-tests")
def get_statistical_tests():
    return load_json("c1", "c1_statistical_tests.json")


@router.get("/tier3-summary")
def get_tier3_summary():
    return load_json("c1", "c1_tier3_soft_assignment_summary.json")


# --- Improvement experiment: k-NN pairing (Option 1) vs ARI-based checkpointing (Option 2) ---

@router.get("/improvement-experiment")
def get_improvement_experiment():
    return load_json("c1", "c1_improvement_experiment.json")


# --- Live retrieval: real cosine-similarity search over the full 781-sequence pool ---

@router.get("/live-pool")
def get_live_pool():
    """Lightweight id/sequence/tier list for the frontend's searchable query picker."""
    return c1_retrieval.get_live_pool()


@router.post("/live-retrieval")
def post_live_retrieval(body: LiveRetrievalRequest):
    try:
        return c1_retrieval.live_retrieval(body.query_id, top_k=body.top_k)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
