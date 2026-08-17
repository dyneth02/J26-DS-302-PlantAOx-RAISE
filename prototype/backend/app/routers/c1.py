from fastapi import APIRouter

from app.artifacts import load_json

router = APIRouter()


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
