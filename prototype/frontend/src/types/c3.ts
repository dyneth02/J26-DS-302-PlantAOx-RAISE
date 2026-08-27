export interface PerturbationResultRow {
  peptide_id: string;
  sequence: string;
  mechanism_tier: string;
  original_score: number;
  p1_sequence: string;
  p1_score: number;
  p1_delta: number;
  p2_sequence: string;
  p2_score: number;
  p2_delta: number;
  p3_sequence: string;
  p3_score: number;
  p3_delta: number;
}

export interface LivePerturbationEntry {
  type: "P1_alanine_scan" | "P2_blosum62_conservative" | "P3_random_control";
  position: number;
  original_residue: string;
  new_residue?: string;
  sequence: string;
  score: number;
  delta: number;
}

export interface LivePerturbationResult {
  sequence: string;
  original_score: number;
  perturbations: LivePerturbationEntry[];
  predictor: "c2_logreg";
  live: true;
}
