from __future__ import annotations

from backend.app.schemas.c2_pu import CurriculumResponse, CurriculumStageMetrics
from backend.app.services.c2_pu.artifacts import load_processed_csv, load_processed_json

LIMITATIONS = [
    "Checkpoint selection at every stage (including C2 and C3) uses a C1-based "
    "surrogate validation risk, not a stage-matched validation signal.",
    "This is a single weighted curriculum run (C1 -> C2 -> C3), not compared "
    "against an unweighted baseline under matched conditions — stage-over-stage "
    "deltas should not be read as a controlled ablation.",
    "External-control MCC remains negative at every stage; later stages do not "
    "establish improved biological reliability, only different positive-recovery "
    "vs. control-discrimination tradeoffs.",
]


def get_curriculum() -> CurriculumResponse:
    summary = load_processed_json("fr4_curriculum_fold0_summary.json")
    matched = load_processed_csv("fr4_pp1_matched_curriculum_fold0.csv")

    config = summary["resolved_config"]["curriculum"]

    stages: list[CurriculumStageMetrics] = []
    for _, row in matched.iterrows():
        stages.append(
            CurriculumStageMetrics(
                condition=row["condition"],
                training_pool=row["training_pool"],
                best_validation_weighted_nnpu_risk=row["best_validation_weighted_nnpu_risk"],
                positive_recovery=row["positive_recovery"],
                c1_fraction_gt_0_5=row["c1_fraction_gt_0_5"],
                c2_fraction_gt_0_5=row["c2_fraction_gt_0_5"],
                c3_fraction_gt_0_5=row["c3_fraction_gt_0_5"],
                external_mcc=row["external_mcc"],
                external_auroc=row["external_auroc"],
                external_recall=row["external_recall"],
            )
        )

    return CurriculumResponse(
        fold_id=summary["resolved_config"]["fold_id"],
        stage_order=config["stage_order"],
        evidence_weights=config["positive_evidence_weights"],
        prior=config["prior"],
        stages=stages,
        limitations=LIMITATIONS,
    )
