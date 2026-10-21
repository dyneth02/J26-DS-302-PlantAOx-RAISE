"""Response models for the C2 / PU-AOP API.

Top-level fields are explicitly typed; deeply nested per-model / per-metric
blocks (whose shape is owned by the research JSON artifacts, not by this
API) are passed through as ``dict``/``list`` so the API never silently
drops or reshapes a field the research side considers part of the
accepted record.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel


class ScientificCaveats(BaseModel):
    technical_status: str
    scientific_status: str
    supervisor_approval_status: str
    known_limitations: list[str]


class OverviewResponse(BaseModel):
    component_id: str = "c2_pu"
    research_title: str
    objective: str
    freeze_id: str
    release_tag: str
    freeze_decision: str
    freeze_date: str
    fr_milestones: dict[str, str]
    data_counts: dict[str, int]
    model_count: int
    caveats: ScientificCaveats


class EvidenceTierBreakdown(BaseModel):
    e1: int
    e2: int
    total: int


class Fr1SummaryResponse(BaseModel):
    version_id: str
    positive_pool_provisional: int
    evidence_tiers: EvidenceTierBreakdown
    cross_source_conflicts_excluded: int
    cdhit_clusters: int
    graphpart_retained: int
    graphpart_excluded_for_homology: int
    fold_sizes: dict[str, int]
    known_limitations: list[str]
    pending_supervisor_approvals: list[str]


class ChallengePoolSummary(BaseModel):
    pool: str
    description: str
    record_count: int
    unique_sequence_count: int | None = None


class Fr2PoolsResponse(BaseModel):
    version_id: str
    pools: list[ChallengePoolSummary]
    c3_ranking_total_rows: int
    c3_selected_per_fold: int
    external_control_records: int
    known_limitations: list[str]


class Fr2FoldChallengesResponse(BaseModel):
    fold_id: int
    n_rows: int
    top_examples: list[dict[str, Any]]


class Fr3ExampleResponse(BaseModel):
    peptide_id: str
    role: str
    sequence: str
    length: int
    valid_alphabet_and_length: bool
    descriptors: dict[str, float] | None = None
    embedding_available: bool
    embedding_dim: int | None = None
    fused_dim: int | None = None


class Fr3SummaryResponse(BaseModel):
    fold_id: int
    descriptor_names: list[str]
    embedding_model: str
    embedding_dim: int
    fused_dim: int
    pool_coverage: dict[str, int]
    feature_cache_available: bool
    examples: list[Fr3ExampleResponse]


class ModelMetrics(BaseModel):
    model_id: str
    model: str
    mcc: float
    average_precision: float
    auroc: float
    precision: float
    recall: float
    f1: float
    balanced_accuracy: float
    confusion_matrix: dict[str, int]
    n_positive: int
    n_control: int
    evaluation_population: str


class Fr4EvaluationResponse(BaseModel):
    fold_id: int
    models: list[ModelMetrics]
    evaluation_note: str
    challenge_behavior_note: str
    challenge_score_fractions: dict[str, dict[str, float]]


class CurriculumStageMetrics(BaseModel):
    condition: str
    training_pool: str
    best_validation_weighted_nnpu_risk: float
    positive_recovery: float
    c1_fraction_gt_0_5: float
    c2_fraction_gt_0_5: float
    c3_fraction_gt_0_5: float
    external_mcc: float
    external_auroc: float
    external_recall: float


class CurriculumResponse(BaseModel):
    fold_id: int
    stage_order: list[str]
    evidence_weights: dict[str, float]
    prior: float
    stages: list[CurriculumStageMetrics]
    limitations: list[str]


class TrackedSourceReport(BaseModel):
    label: str
    category: str
    path: str
    sha256: str | None
    status: str
    """One of 'verified' (hash matches the frozen manifest), 'modified'
    (present but hash no longer matches), 'present' (present, no recorded
    hash to check against), or 'missing'."""


class ArtifactStatusResponse(BaseModel):
    freeze_id: str
    release_tag: str
    freeze_decision: str
    total_tracked: int
    present_count: int
    missing_count: int
    missing_paths: list[str]
    pending_decisions: list[str]
    tracked_source_reports: list[TrackedSourceReport]
