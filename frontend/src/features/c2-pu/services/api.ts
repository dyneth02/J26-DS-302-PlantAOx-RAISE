import { apiGet } from "@/lib/api/client";
import type {
  ArtifactStatusResponse,
  CurriculumResponse,
  Fr1SummaryResponse,
  Fr2FoldChallengesResponse,
  Fr2PoolsResponse,
  Fr3SummaryResponse,
  Fr4EvaluationResponse,
  OverviewResponse,
} from "@/features/c2-pu/types";

const BASE = "/c2";

export const c2Api = {
  overview: () => apiGet<OverviewResponse>(`${BASE}/overview`),
  fr1Summary: () => apiGet<Fr1SummaryResponse>(`${BASE}/fr1/summary`),
  fr2Pools: () => apiGet<Fr2PoolsResponse>(`${BASE}/fr2/pools`),
  fr2FoldChallenges: (foldId: number) => apiGet<Fr2FoldChallengesResponse>(`${BASE}/fr2/c3-folds/${foldId}`),
  fr3Examples: () => apiGet<Fr3SummaryResponse>(`${BASE}/fr3/examples`),
  fr4Evaluation: () => apiGet<Fr4EvaluationResponse>(`${BASE}/fr4/evaluation`),
  curriculum: () => apiGet<CurriculumResponse>(`${BASE}/fr4/curriculum`),
  artifactStatus: () => apiGet<ArtifactStatusResponse>(`${BASE}/artifacts/status`),
};
