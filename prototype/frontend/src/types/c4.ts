export interface PhysicochemicalSummary {
  molecular_weight: number;
  gravy: number;
  net_charge: number;
  aromaticity: number;
}

export interface EvidenceCard {
  candidate_id: string;
  sequence: string;
  source_protein: string;
  plant_species: string;
  enzyme: string;
  length: number;
  ad_distance: number;
  sim_c1: number;
  ad_tier: string;
  prob_c2: number;
  combined_score: number;
  abstention_flag: string;
  predictor_reliability: Record<string, string>;
  physicochemical_summary: PhysicochemicalSummary;
  interpretation?: string;
}
