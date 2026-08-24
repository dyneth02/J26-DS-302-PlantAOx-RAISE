export interface ChallengePool {
  size: number;
  source: string;
  purpose: string;
}

export type ChallengePools = Record<string, ChallengePool>;

export interface RnisReport {
  classifier: string;
  mcc_c1_easy: number;
  mcc_c3_hard: number;
  rnis: number;
  interpretation: string;
}

export interface LiveRnisResult {
  pools_selected: string[];
  n_train: number;
  mcc_easy: number;
  mcc_hard: number;
  rnis: number;
  interpretation: string;
  live: true;
}
