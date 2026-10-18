from __future__ import annotations

from backend.app.schemas.c2_pu import OverviewResponse, ScientificCaveats
from backend.app.services.c2_pu.artifacts import load_frozen_json, load_freeze_manifest

RESEARCH_TITLE = (
    "PU-AOP: Evidence-Tiered Positive-Unlabeled Curriculum Classifier "
    "with Random-Negative Inflation Audit"
)
OBJECTIVE = (
    "Improve antioxidant-peptide discovery under scarce/unreliable negative labels, "
    "using evidence-tiered positive curation, positive-unlabeled learning, "
    "biologically differentiated unlabeled challenge pools, and an "
    "evidence-weighted staged curriculum (C1 -> C2 -> C3)."
)


def get_overview() -> OverviewResponse:
    manifest = load_freeze_manifest()
    pp1 = load_frozen_json("pp1_baseline_v1")
    pp2 = load_frozen_json("pp2_baseline_v1")

    data_counts = {
        "accepted_positives": pp1["counts"]["positive_pool_provisional"],
        "graphpart_retained_positives": pp1["counts"]["graphpart_retained"],
        "c1_unique_sequences": pp2["counts"]["c1_v3_unique_sequences"],
        "c2_unique_sequences": pp2["counts"]["c2_v2_records"],
        "c3_union_unique_sequences": pp2["counts"]["c3_union_records"],
        "external_control_records": pp2["counts"]["external_control_records"],
        "feature_dimension": manifest["dependencies"]["fr3"]["feature_dimension"],
    }

    fr_milestones = {
        "FR1": "Evidence-tiered positive-pool curation — accepted, frozen as pp1_baseline_v1",
        "FR2": "Challenge-pool construction (C1/C2/C3) — accepted, frozen as pp2_baseline_v1",
        "FR3": "Feature engineering (descriptors + ESM-2 fusion + fold scaling) — accepted",
        "FR4": "Baseline classifiers + evidence-weighted curriculum — accepted with documented scientific limitations",
    }

    caveats = ScientificCaveats(
        technical_status=manifest["validation_status"]["technical"],
        scientific_status=manifest["validation_status"]["scientific"],
        supervisor_approval_status=manifest["validation_status"]["supervisor_approval"],
        known_limitations=manifest["known_limitations"],
    )

    return OverviewResponse(
        research_title=RESEARCH_TITLE,
        objective=OBJECTIVE,
        freeze_id=manifest["release"]["id"],
        release_tag=manifest["source_control"]["release_tag"],
        freeze_decision=manifest["release"]["decision"],
        freeze_date=manifest["release"]["freeze_date"],
        fr_milestones=fr_milestones,
        data_counts=data_counts,
        model_count=len(manifest["accepted_models"]),
        caveats=caveats,
    )
