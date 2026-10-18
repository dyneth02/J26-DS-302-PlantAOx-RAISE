from __future__ import annotations

from backend.app.schemas.c2_pu import Fr4EvaluationResponse, ModelMetrics
from backend.app.services.c2_pu.artifacts import load_processed_csv, load_processed_json

EVALUATION_NOTE = (
    "Metrics are computed against 124 held-out positives vs 38 AnOxPePred "
    "assay-inactive external controls (fold 0 only). Scores are uncalibrated "
    "model outputs, not validated biological probabilities. All five "
    "configurations show negative MCC and sub-0.5 AUROC on this evaluation — "
    "a technically reproducible prototype, not a scientifically validated "
    "antioxidant-activity classifier."
)
CHALLENGE_BEHAVIOR_NOTE = (
    "C1/C2/C3 are unlabeled challenge pools, not confirmed non-antioxidant "
    "peptides. 'Fraction scored > 0.5' below describes model scoring behavior "
    "on these unlabeled pools; it is not a measured false-positive rate."
)


def get_fr4_evaluation() -> Fr4EvaluationResponse:
    comparison = load_processed_csv("fr4_baseline_comparison_fold0.csv")
    detailed = load_processed_json("fr4_baseline_evaluation_fold0.json")

    models: list[ModelMetrics] = []
    challenge_fractions: dict[str, dict[str, float]] = {}

    for _, row in comparison.iterrows():
        model_id = row["model_id"]
        models.append(
            ModelMetrics(
                model_id=model_id,
                model=row["model"],
                mcc=row["mcc"],
                average_precision=row["average_precision"],
                auroc=row["auroc"],
                precision=row["precision"],
                recall=row["recall"],
                f1=row["f1"],
                balanced_accuracy=row["balanced_accuracy"],
                confusion_matrix={
                    "tp": int(row["tp"]),
                    "tn": int(row["tn"]),
                    "fp": int(row["fp"]),
                    "fn": int(row["fn"]),
                },
                n_positive=int(row["n_positive"]),
                n_control=int(row["n_control"]),
                evaluation_population=row["evaluation"],
            )
        )

        model_detail = detailed.get("models", {}).get(model_id, {})
        challenge_behavior = model_detail.get("challenge_behavior", {})
        challenge_fractions[model_id] = {
            pool: pool_data.get("bounded_score_summary", {}).get("fraction_gt_0_5")
            for pool, pool_data in challenge_behavior.items()
            if pool_data.get("bounded_score_summary", {}).get("fraction_gt_0_5") is not None
        }

    return Fr4EvaluationResponse(
        fold_id=0,
        models=models,
        evaluation_note=EVALUATION_NOTE,
        challenge_behavior_note=CHALLENGE_BEHAVIOR_NOTE,
        challenge_score_fractions=challenge_fractions,
    )
