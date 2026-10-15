// Scoped to the shapes the new interactive components consume -- not a full retrofit
// of every `any` already in C1Page.tsx.

export interface LivePoolEntry {
  id: string;
  sequence: string;
  mechanism_tier: string;
}

export interface RetrievalMatch {
  rank: number;
  id?: string;
  sequence: string;
  mechanism_tier: string;
  similarity: number;
}

export interface LiveRetrievalResult {
  query: { id?: string; sequence: string; mechanism_tier: string };
  top_matches: RetrievalMatch[];
  pool_size: number;
  live: true;
}

export interface AblationRow {
  model: string;
  "recall@10": number;
  "tier2_recall@5": number;
  ari: number;
}

export interface AblationComparison {
  description: string;
  results: AblationRow[];
}
