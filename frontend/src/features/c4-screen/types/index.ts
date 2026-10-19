export type Plant = "soybean" | "rice" | "rapeseed" | "olive";
export type Tier = 1 | 2 | 3;

export interface C4Meta {
  ad_params: Record<string, number | string | boolean>;
  cloud: { source: string; n: number; status: string };
  signal_sources: Record<string, string>;
  spec_version: string | null;
  embedding_manifest_summary: Record<string, string | number | null>;
  output_manifest_hash: string;
  tag: string | null;
  warnings: string[];
}

export interface FunnelRow {
  plant: Plant;
  proteins: number;
  protein_exclusions: number;
  raw_fragments: number;
  length_filtered: number;
  composition_filtered: number;
  deduplicated: number;
  embedded: number;
}

export interface TierFraction {
  plant?: Plant | "all_candidates";
  tier: Tier;
  fraction: number;
  n: number;
  length_bin?: "all" | "3-10" | "11-20";
  baseline_fraction?: number;
  mean_centered_fraction?: number;
  fraction_delta?: number;
  reference_source?: string;
  label?: string;
}

export interface TierSummary {
  plant: Plant | null;
  overall: Array<TierFraction & { plant: Plant }>;
  by_length_bin: Array<TierFraction & { plant: Plant; length_bin: "3-10" | "11-20" }>;
  mean_centering_sensitivity: SensitivityFraction[] | null;
  sensitivity_label: string;
}

export interface Histogram {
  plant: Plant | null;
  bins: number;
  edges: number[];
  cloud: { source: string; counts: number[] };
  candidates: { source: string; counts: number[] };
  t1: number;
  t2: number;
  cloud_source: string;
}

export interface LengthDistribution {
  length: number;
  candidate_count: number;
  cloud_count: number;
}

export interface Lengths {
  candidate_source: string;
  cloud_source: string;
  distributions: LengthDistribution[];
}

export interface CandidateRow {
  peptide_id: string;
  sequence: string;
  plant: Plant;
  tier: Tier;
  d_AD: number;
  CS: number;
  rank: number | null;
  length: number;
  [key: string]: unknown;
}

export interface CandidatePage {
  items: CandidateRow[];
  total: number;
  page: number;
  page_size: number;
}

export interface Provenance {
  parent_accession: string;
  plant: Plant;
  start: number;
  end: number;
  enzyme_path: string;
}

export interface CandidateDetail {
  sequence: string;
  peptide_id: string;
  species: string;
  plant: Plant;
  provenance: Provenance[];
  parent_accessions: string[];
  enzymes: string[];
  physicochemical: { molecular_weight: number; pI: number; GRAVY: number; net_charge_ph7: number };
  SIM_C1: number | null;
  PROB_C2: number | null;
  evidence_tier: string | null;
  tier: Tier;
  flag?: "GREEN" | "AMBER" | "RED";
  d_AD: number;
  CS: number;
  rank: number | null;
  BCS: number | null;
  BCS_flag: "LOW" | "MEDIUM" | "HIGH" | null;
  BCS_threshold_status: string;
  signal_sources: Record<string, string>;
  cloud_source: string;
  injected_demo_case: boolean;
  notice: string;
}

export interface CandidateCards {
  plant: Plant;
  cards: CandidateDetail[];
}

export interface AbstainedPage {
  items: CandidateDetail[];
  total: number;
  page: number;
  page_size: number;
}

// Sensitivity diagnostics are grouped separately from production plant summaries.
export interface SensitivityFraction extends TierFraction {
  group: string;
}