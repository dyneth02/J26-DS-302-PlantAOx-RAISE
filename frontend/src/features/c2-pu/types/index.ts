// Mirrors backend/app/schemas/c2_pu.py. Kept hand-written (not codegen) --
// the research JSON's nested shapes are stable per the frozen PP1 release,
// and codegen would be overkill for a single component's read-only API.

export interface ScientificCaveats {
  technical_status: string;
  scientific_status: string;
  supervisor_approval_status: string;
  known_limitations: string[];
}

export interface OverviewResponse {
  component_id: string;
  research_title: string;
  objective: string;
  freeze_id: string;
  release_tag: string;
  freeze_decision: string;
  freeze_date: string;
  fr_milestones: Record<string, string>;
  data_counts: Record<string, number>;
  model_count: number;
  caveats: ScientificCaveats;
}

export interface Fr1SummaryResponse {
  version_id: string;
  positive_pool_provisional: number;
  evidence_tiers: { e1: number; e2: number; total: number };
  cross_source_conflicts_excluded: number;
  cdhit_clusters: number;
  graphpart_retained: number;
  graphpart_excluded_for_homology: number;
  fold_sizes: Record<string, number>;
  known_limitations: string[];
  pending_supervisor_approvals: string[];
}

export interface ChallengePoolSummary {
  pool: string;
  description: string;
  record_count: number;
  unique_sequence_count: number | null;
}

export interface Fr2PoolsResponse {
  version_id: string;
  pools: ChallengePoolSummary[];
  c3_ranking_total_rows: number;
  c3_selected_per_fold: number;
  external_control_records: number;
  known_limitations: string[];
}

export interface Fr2FoldChallengesResponse {
  fold_id: number;
  n_rows: number;
  top_examples: Array<{ peptide_id: string; sequence: string; rank: number; cosine_similarity: number }>;
}

export interface Fr3ExampleResponse {
  peptide_id: string;
  role: string;
  sequence: string;
  length: number;
  valid_alphabet_and_length: boolean;
  descriptors: Record<string, number> | null;
  embedding_available: boolean;
  embedding_dim: number | null;
  fused_dim: number | null;
}

export interface Fr3SummaryResponse {
  fold_id: number;
  descriptor_names: string[];
  embedding_model: string;
  embedding_dim: number;
  fused_dim: number;
  pool_coverage: Record<string, number>;
  feature_cache_available: boolean;
  examples: Fr3ExampleResponse[];
}

export interface ModelMetrics {
  model_id: string;
  model: string;
  mcc: number;
  average_precision: number;
  auroc: number;
  precision: number;
  recall: number;
  f1: number;
  balanced_accuracy: number;
  confusion_matrix: { tp: number; tn: number; fp: number; fn: number };
  n_positive: number;
  n_control: number;
  evaluation_population: string;
}

export interface Fr4EvaluationResponse {
  fold_id: number;
  models: ModelMetrics[];
  evaluation_note: string;
  challenge_behavior_note: string;
  challenge_score_fractions: Record<string, Record<string, number>>;
}

export interface CurriculumStageMetrics {
  condition: string;
  training_pool: string;
  best_validation_weighted_nnpu_risk: number;
  positive_recovery: number;
  c1_fraction_gt_0_5: number;
  c2_fraction_gt_0_5: number;
  c3_fraction_gt_0_5: number;
  external_mcc: number;
  external_auroc: number;
  external_recall: number;
}

export interface CurriculumResponse {
  fold_id: number;
  stage_order: string[];
  evidence_weights: Record<string, number>;
  prior: number;
  stages: CurriculumStageMetrics[];
  limitations: string[];
}

export interface TrackedSourceReport {
  label: string;
  category: string;
  path: string;
  sha256: string | null;
  status: "verified" | "modified" | "present" | "missing";
}

export interface ArtifactStatusResponse {
  freeze_id: string;
  release_tag: string;
  freeze_decision: string;
  total_tracked: number;
  present_count: number;
  missing_count: number;
  missing_paths: string[];
  pending_decisions: string[];
  tracked_source_reports: TrackedSourceReport[];
}
