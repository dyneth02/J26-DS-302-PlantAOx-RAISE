import { apiGet } from "@/lib/api/client";
import type {
  AbstainedPage,
  CandidateCards,
  CandidateDetail,
  CandidatePage,
  Histogram,
  Lengths,
  Plant,
  TierSummary,
  C4Meta,
  FunnelRow,
} from "@/features/c4-screen/types";

const BASE = "/c4";
const withQuery = (path: string, values: Record<string, string | number | undefined>) => {
  const query = new URLSearchParams();
  for (const [key, value] of Object.entries(values)) {
    if (value !== undefined && value !== "") query.set(key, String(value));
  }
  const suffix = query.toString();
  return suffix ? `${path}?${suffix}` : path;
};

export interface CandidateQuery {
  plant?: Plant;
  tier?: number;
  len_min?: number;
  len_max?: number;
  cs_min?: number;
  cs_max?: number;
  q?: string;
  sort?: "sequence" | "peptide_id" | "plant" | "tier" | "length" | "d_AD" | "CS" | "rank";
  order?: "asc" | "desc";
  page?: number;
  page_size?: number;
}

export const c4Api = {
  meta: () => apiGet<C4Meta>(`${BASE}/meta`),
  funnel: () => apiGet<FunnelRow[]>(`${BASE}/funnel`),
  tierSummary: (plant?: Plant) => apiGet<TierSummary>(withQuery(`${BASE}/tiers/summary`, { plant })),
  adHistogram: (plant?: Plant, bins = 30) =>
    apiGet<Histogram>(withQuery(`${BASE}/ad/histogram`, { plant, bins })),
  lengths: () => apiGet<Lengths>(`${BASE}/lengths`),
  candidates: (query: CandidateQuery = {}) => apiGet<CandidatePage>(withQuery(`${BASE}/candidates`, { ...query })),
  candidate: (peptideId: string) => apiGet<CandidateDetail>(`${BASE}/candidates/${encodeURIComponent(peptideId)}`),
  cards: (plant: Plant, limit = 50) => apiGet<CandidateCards>(`${BASE}/cards/${plant}?limit=${limit}`),
  abstained: (plant: Plant, page = 1, pageSize = 50) =>
    apiGet<AbstainedPage>(withQuery(`${BASE}/abstained/${plant}`, { page, page_size: pageSize })),
  cardsExportHref: (plant?: Plant) => `/api/v1${withQuery(`${BASE}/export/cards.csv`, { plant })}`,
};
