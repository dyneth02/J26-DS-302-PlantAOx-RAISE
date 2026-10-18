from __future__ import annotations

from backend.app.schemas.c2_pu import EvidenceTierBreakdown, Fr1SummaryResponse
from backend.app.services.c2_pu.artifacts import load_frozen_json


def get_fr1_summary() -> Fr1SummaryResponse:
    pp1 = load_frozen_json("pp1_baseline_v1")
    counts = pp1["counts"]
    fold_sizes = {str(int(float(k))): v for k, v in counts["fold_sizes"].items()}

    return Fr1SummaryResponse(
        version_id=pp1["version_id"],
        positive_pool_provisional=counts["positive_pool_provisional"],
        evidence_tiers=EvidenceTierBreakdown(
            e1=counts["positive_pool_provisional_e1"],
            e2=counts["positive_pool_provisional_e2"],
            total=counts["positive_pool_provisional"],
        ),
        cross_source_conflicts_excluded=counts["label_conflicts_excluded"],
        cdhit_clusters=counts["cdhit_clusters"],
        graphpart_retained=counts["graphpart_retained"],
        graphpart_excluded_for_homology=counts["graphpart_excluded_for_homology"],
        fold_sizes=fold_sizes,
        known_limitations=pp1["known_limitations"],
        pending_supervisor_approvals=pp1["pending_supervisor_approvals"],
    )
