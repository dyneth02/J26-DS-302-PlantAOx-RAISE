"""Response models for Component 01 (AOP-ProCon).

Hand-written to match the accepted tables under ``data/processed/c1_procon``.
These are intentionally NOT shared with C2: the two components have different
evaluation semantics (C1 reports retrieval AP and probe AUROC against simple
baselines; C2 reports MCC against external assay-inactive controls).
"""

from __future__ import annotations

from pydantic import BaseModel


class PipelineStep(BaseModel):
    step: int
    title: str
    status: str
    summary: str
    notebook: str


class ScientificCaveats(BaseModel):
    technical_status: str
    scientific_status: str
    known_limitations: list[str]


class HeroStat(BaseModel):
    value: str
    label: str
    hint: str


class OverviewResponse(BaseModel):
    research_title: str
    objective: str
    benchmark_fingerprint: str
    counts: dict[str, int]
    label_counts: dict[str, int]
    pipeline_steps: list[PipelineStep]
    hero_stats: list[HeroStat]
    headline_findings: list[str]
    caveats: ScientificCaveats


class LabelCount(BaseModel):
    label: str
    count: int


class SourceByClass(BaseModel):
    source_group: str
    mc_active: int
    frs_only: int


class LengthBin(BaseModel):
    length_bin: str
    mc_active: int
    frs_only: int


class DatasetResponse(BaseModel):
    fingerprint: str
    split_type: str
    near_duplicate_rule: str
    label_counts: list[LabelCount]
    strict_pool: dict[str, int]
    source_by_class: list[SourceByClass]
    length_bins: list[LengthBin]
    tripeptide_share: dict[str, float]
    mean_length: dict[str, float]
    notes: list[str]


class RetrievalRow(BaseModel):
    representation: str
    kind: str
    ap: float
    ap_lo: float | None = None
    ap_hi: float | None = None
    lift: float
    recall_at_5: float
    chance_recall_at_5: float


class PairedRow(BaseModel):
    comparison: str
    ap_a: float
    ap_b: float
    delta_ap: float
    ci_lo: float
    ci_hi: float
    p_holm: float
    verdict: str


class SeedRow(BaseModel):
    model: str
    ap_mean: float
    ap_sd: float
    delta_ap_mean: float
    seeds_below_untrained: int
    n_seeds: int


class ScaleRow(BaseModel):
    scale: str
    model: str
    ap_untrained: float
    ap_trained_mean: float
    delta_ap_mean: float
    seeds_below_untrained: int
    n_seeds: int


class CollapseRow(BaseModel):
    model: str
    mean_cos_heldout: float
    eff_rank_heldout: float


class RetrievalResponse(BaseModel):
    mode: str
    n_queries: int
    chance_ap: float
    chance_recall_at_5: float
    representations: list[RetrievalRow]
    paired: list[PairedRow]
    seeds: list[SeedRow]
    scale: list[ScaleRow]
    collapse: list[CollapseRow]
    trained_runs_total: int
    trained_runs_above_untrained: int
    note: str


class ProbeRow(BaseModel):
    features: str
    auroc: float
    lo: float
    hi: float
    rep_min: float | None = None
    rep_max: float | None = None


class ProbePairedRow(BaseModel):
    model_a: str
    model_b: str
    delta_auroc: float
    ci_lo: float
    ci_hi: float
    repeats_delta_gt_0: int
    verdict: str


class ProbeResponse(BaseModel):
    mode: str
    evaluation_note: str
    null_band: ProbeRow
    grouped: list[ProbeRow]
    leaky: list[ProbeRow]
    leakage_inflation: dict[str, float]
    paired: list[ProbePairedRow]


class ConfoundRow(BaseModel):
    pool: str
    features: str
    auroc: float
    lo: float
    hi: float
    above_null_97_5: bool


class DeltaRow(BaseModel):
    context: str
    model: str
    reference: str
    delta_auroc: float
    lo: float
    hi: float
    repeats_delta_gt_0: int
    verdict: str


class LengthMatchedRow(BaseModel):
    features: str
    pool: str
    auroc_mean: float
    auroc_p2_5: float
    auroc_p97_5: float
    tripeptide_share_mc: float | None = None
    tripeptide_share_frs: float | None = None


class LearningCurvePoint(BaseModel):
    features: str
    train_frac: float
    auroc: float


class CvDesignRow(BaseModel):
    features: str
    design: str
    auroc_pooled: float | None = None
    auroc_foldmean: float | None = None


class ConfoundsResponse(BaseModel):
    verdict: str
    strict: list[ConfoundRow]
    anoxpepred_only: list[ConfoundRow]
    esm_over_confounds: list[DeltaRow]
    length_matched: list[LengthMatchedRow]
    learning_curve: list[LearningCurvePoint]
    cv_design: list[CvDesignRow]
    headline: dict[str, str]


class ArtifactStatusItem(BaseModel):
    name: str
    path: str
    exists: bool
    category: str


class ArtifactStatusResponse(BaseModel):
    all_present: bool
    missing: list[str]
    artifacts: list[ArtifactStatusItem]


class EmbeddingSpace(BaseModel):
    key: str
    name: str
    dim: int
    pc_variance_share: list[float]
    within_mc: float
    within_frs: float
    between: float
    all_pairs: float
    separation: float
    mc_neighbour_purity: float
    pc1_length_correlation: float


class EmbeddingPoint(BaseModel):
    sequence: str
    label: str
    length: int
    source_group: str | None = None
    strict_class: str
    coords: dict[str, list[float]]


class PairSetCount(BaseModel):
    pair_set: str
    description: str
    pairs: int


class PairExample(BaseModel):
    mechanism: str
    seq1: str
    seq2: str
    distance: float


class EmbeddingMeta(BaseModel):
    n_peptides: int
    n_strict: int
    n_mc_active: int
    chance_mc_neighbour_purity: float
    neighbours: int
    pooling_rule: str
    peptides_ge_10_aa: int
    peptides_lt_10_aa: int


class EmbeddingResponse(BaseModel):
    meta: EmbeddingMeta
    spaces: list[EmbeddingSpace]
    points: list[EmbeddingPoint]
    pair_counts: list[PairSetCount]
    pair_examples: list[PairExample]
    reading_guide: list[str]


class LookupRecord(BaseModel):
    sequence: str
    labels: str
    length: int
    source_group: str | None = None
    fold: int | None = None
    homology_group: int | None = None
    strict_evidence: bool | None = None
    oof_mc_score_strict: float | None = None
    oof_mc_score_extended: float | None = None


class NearestPeptide(BaseModel):
    sequence: str
    labels: str
    length: int
    cosine: float


class LookupResponse(BaseModel):
    query: str
    valid: bool
    problems: list[str]
    in_benchmark: bool
    record: LookupRecord | None = None
    composition: dict[str, float]
    nearest: list[NearestPeptide]
    notes: list[str]
