import { apiGet } from "@/lib/api/client";
import type {
  ArtifactStatusResponse,
  ConfoundsResponse,
  DatasetResponse,
  EmbeddingResponse,
  LookupResponse,
  OverviewResponse,
  ProbeResponse,
  RetrievalResponse,
} from "@/features/c1-procon/types";

const BASE = "/c1";

export const c1Api = {
  overview: () => apiGet<OverviewResponse>(`${BASE}/overview`),
  dataset: () => apiGet<DatasetResponse>(`${BASE}/dataset`),
  embedding: () => apiGet<EmbeddingResponse>(`${BASE}/embedding`),
  lookup: (sequence: string) => apiGet<LookupResponse>(`${BASE}/lookup?sequence=${encodeURIComponent(sequence)}`),
  retrieval: () => apiGet<RetrievalResponse>(`${BASE}/retrieval`),
  probe: () => apiGet<ProbeResponse>(`${BASE}/probe`),
  confounds: () => apiGet<ConfoundsResponse>(`${BASE}/confounds`),
  artifactStatus: () => apiGet<ArtifactStatusResponse>(`${BASE}/artifacts/status`),
};
