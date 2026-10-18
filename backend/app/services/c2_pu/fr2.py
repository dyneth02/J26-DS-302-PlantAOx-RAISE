from __future__ import annotations

from backend.app.core import plantaox_bridge  # noqa: F401  (sys.path side effect)
from backend.app.core.errors import ArtifactUnavailableError, ResourceNotFoundError
from backend.app.schemas.c2_pu import ChallengePoolSummary, Fr2FoldChallengesResponse, Fr2PoolsResponse
from backend.app.services.c2_pu.artifacts import c2_processed_dir, load_frozen_json

N_FOLDS = 5


def get_fr2_pools() -> Fr2PoolsResponse:
    pp2 = load_frozen_json("pp2_baseline_v1")
    counts = pp2["counts"]

    pools = [
        ChallengePoolSummary(
            pool="C1",
            description=(
                "Random/uncharacterized reviewed-UniProt decoy peptides. "
                "Unlabeled, not confirmed non-antioxidant."
            ),
            record_count=counts["c1_v3_records"],
            unique_sequence_count=counts["c1_v3_unique_sequences"],
        ),
        ChallengePoolSummary(
            pool="C2",
            description=(
                "Bioactive peptides without this project's antioxidant annotation. "
                "Unlabeled, not confirmed non-antioxidant."
            ),
            record_count=counts["c2_v2_records"],
            unique_sequence_count=counts["c2_v2_records"],
        ),
        ChallengePoolSummary(
            pool="C3",
            description=(
                "ESM-2 embedding-nearest hard challenges, built with fold-safe "
                "training-only centroids. The full union is NOT a valid per-fold "
                "challenge set — use the fold-specific endpoint."
            ),
            record_count=counts["c3_union_records"],
            unique_sequence_count=counts["c3_union_records"],
        ),
        ChallengePoolSummary(
            pool="external_control",
            description=(
                "AnOxPePred assay-inactive peptides under recorded assay conditions. "
                "Evaluation-only — kept separate from training/challenge pools, and "
                "not a claim of universal inactivity across all assays/conditions."
            ),
            record_count=counts["external_control_records"],
            unique_sequence_count=counts["external_control_records"],
        ),
    ]

    return Fr2PoolsResponse(
        version_id=pp2["version_id"],
        pools=pools,
        c3_ranking_total_rows=counts["c3_ranking_rows"],
        c3_selected_per_fold=counts["c3_ranking_rows"] // N_FOLDS,
        external_control_records=counts["external_control_records"],
        known_limitations=pp2["known_limitations"],
    )


def get_fr2_fold_challenges(fold_id: int) -> Fr2FoldChallengesResponse:
    if fold_id not in range(N_FOLDS):
        raise ResourceNotFoundError(f"fold_id must be in 0..{N_FOLDS - 1}, got {fold_id}")

    from plantaox.c2_pu.curation.c3 import load_fold_challenges

    ranking_path = c2_processed_dir() / "c3_similarity_ranking.csv"
    if not ranking_path.exists():
        raise ArtifactUnavailableError(
            "C3 similarity ranking artifact is missing from this checkout.",
            artifact_path=str(ranking_path),
        )

    fold_df = load_fold_challenges(ranking_path, fold_id)
    top_examples = fold_df.head(10)[["peptide_id", "sequence", "rank", "cosine_similarity"]].to_dict(
        orient="records"
    )

    return Fr2FoldChallengesResponse(
        fold_id=fold_id,
        n_rows=len(fold_df),
        top_examples=top_examples,
    )
