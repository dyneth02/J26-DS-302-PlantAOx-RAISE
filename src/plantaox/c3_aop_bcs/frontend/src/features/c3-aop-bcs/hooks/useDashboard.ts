import { c3Api } from "@/features/c3-aop-bcs/services/api";
import { useApi } from "@/lib/api/useApi";

export function useDashboard() {
  return useApi(c3Api.dashboard, []);
}
