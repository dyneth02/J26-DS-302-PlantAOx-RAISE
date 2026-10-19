// Hand-written to match backend/app/schemas/c1_procon.py (snake_case, as the API returns it).

export interface PipelineStep { step: number; title: string; status: string; summary: string; notebook: string }
export interface ScientificCaveats { technical_status: string; scientific_status: string; known_limitations: string[] }

export interface HeroStatItem { value: string; label: string; hint: string }

export interface OverviewResponse {
  research_title: string;
  objective: string;
  benchmark_fingerprint: string;
  counts: Record<string, number>;
  label_counts: Record<string, number>;
  pipeline_steps: PipelineStep[];
  hero_stats: HeroStatItem[];
  headline_findings: string[];
  caveats: ScientificCaveats;
}

export interface DatasetResponse {
  fingerprint: string;
  split_type: string;
  near_duplicate_rule: string;
  label_counts: { label: string; count: number }[];
  strict_pool: { peptides: number; mc_active: number; frs_only: number };
  source_by_class: { source_group: string; mc_active: number; frs_only: number }[];
  length_bins: { length_bin: string; mc_active: number; frs_only: number }[];
  tripeptide_share: { mc_active: number; frs_only: number };
  mean_length: { mc_active: number; frs_only: number };
  notes: string[];
}

export interface RetrievalRow {
  representation: string; kind: string; ap: number; ap_lo: number | null; ap_hi: number | null;
  lift: number; recall_at_5: number; chance_recall_at_5: number;
}
export interface PairedRow { comparison: string; ap_a: number; ap_b: number; delta_ap: number; ci_lo: number; ci_hi: number; p_holm: number; verdict: string }
export interface SeedRow { model: string; ap_mean: number; ap_sd: number; delta_ap_mean: number; seeds_below_untrained: number; n_seeds: number }
export interface ScaleRow { scale: string; model: string; ap_untrained: number; ap_trained_mean: number; delta_ap_mean: number; seeds_below_untrained: number; n_seeds: number }
export interface CollapseRow { model: string; mean_cos_heldout: number; eff_rank_heldout: number }

export interface RetrievalResponse {
  mode: string; n_queries: number; chance_ap: number; chance_recall_at_5: number;
  representations: RetrievalRow[]; paired: PairedRow[]; seeds: SeedRow[]; scale: ScaleRow[]; collapse: CollapseRow[];
  trained_runs_total: number; trained_runs_above_untrained: number; note: string;
}

export interface ProbeRow { features: string; auroc: number; lo: number; hi: number; rep_min: number | null; rep_max: number | null }
export interface ProbePairedRow { model_a: string; model_b: string; delta_auroc: number; ci_lo: number; ci_hi: number; repeats_delta_gt_0: number; verdict: string }
export interface ProbeResponse {
  mode: string; evaluation_note: string; null_band: ProbeRow; grouped: ProbeRow[]; leaky: ProbeRow[];
  leakage_inflation: Record<string, number>; paired: ProbePairedRow[];
}

export interface ConfoundRow { pool: string; features: string; auroc: number; lo: number; hi: number; above_null_97_5: boolean }
export interface DeltaRow { context: string; model: string; reference: string; delta_auroc: number; lo: number; hi: number; repeats_delta_gt_0: number; verdict: string }
export interface LengthMatchedRow {
  features: string; pool: string; auroc_mean: number; auroc_p2_5: number; auroc_p97_5: number;
  tripeptide_share_mc: number | null; tripeptide_share_frs: number | null;
}
export interface LearningCurvePoint { features: string; train_frac: number; auroc: number }
export interface CvDesignRow { features: string; design: string; auroc_pooled: number | null; auroc_foldmean: number | null }
export interface ConfoundsResponse {
  verdict: string; strict: ConfoundRow[]; anoxpepred_only: ConfoundRow[]; esm_over_confounds: DeltaRow[];
  length_matched: LengthMatchedRow[]; learning_curve: LearningCurvePoint[]; cv_design: CvDesignRow[]; headline: Record<string, string>;
}

export interface ArtifactStatusItem { name: string; path: string; exists: boolean; category: string }
export interface ArtifactStatusResponse { all_present: boolean; missing: string[]; artifacts: ArtifactStatusItem[] }

export interface EmbeddingSpace {
  key: string; name: string; dim: number; pc_variance_share: number[];
  within_mc: number; within_frs: number; between: number; all_pairs: number; separation: number;
  mc_neighbour_purity: number; pc1_length_correlation: number;
}
export interface EmbeddingPoint {
  sequence: string; label: string; length: number; source_group: string | null; strict_class: string;
  coords: Record<string, number[]>;
}
export interface PairSetCount { pair_set: string; description: string; pairs: number }
export interface PairExample { mechanism: string; seq1: string; seq2: string; distance: number }
export interface EmbeddingMeta {
  n_peptides: number; n_strict: number; n_mc_active: number; chance_mc_neighbour_purity: number; neighbours: number;
  pooling_rule: string; peptides_ge_10_aa: number; peptides_lt_10_aa: number;
}
export interface EmbeddingResponse {
  meta: EmbeddingMeta; spaces: EmbeddingSpace[]; points: EmbeddingPoint[]; pair_counts: PairSetCount[];
  pair_examples: PairExample[]; reading_guide: string[];
}

export interface LookupRecord {
  sequence: string; labels: string; length: number; source_group: string | null; fold: number | null;
  homology_group: number | null; strict_evidence: boolean | null; oof_mc_score_strict: number | null; oof_mc_score_extended: number | null;
}
export interface NearestPeptide { sequence: string; labels: string; length: number; cosine: number }
export interface LookupResponse {
  query: string; valid: boolean; problems: string[]; in_benchmark: boolean; record: LookupRecord | null;
  composition: Record<string, number>; nearest: NearestPeptide[]; notes: string[];
}
