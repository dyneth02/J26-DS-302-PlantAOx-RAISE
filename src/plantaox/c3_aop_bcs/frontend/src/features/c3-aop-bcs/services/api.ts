import { apiGet } from "@/lib/api/client";
import type { DashboardPayload, HealthResponse } from "@/features/c3-aop-bcs/types";

const BASE = "/c3";
export const c3Api = {
  health: () => apiGet<HealthResponse>(`${BASE}/health`),
  dashboard: () => apiGet<DashboardPayload>(`${BASE}/dashboard`),
};
