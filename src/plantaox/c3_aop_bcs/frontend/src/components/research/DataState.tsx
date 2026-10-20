import type { ReactNode } from "react";
import { Card } from "@/components/ui/Card";
import { ApiError } from "@/lib/api/client";
import type { ApiState } from "@/lib/api/useApi";

export function DataState<T>({ state, render }: { state: ApiState<T>; render: (data: T) => ReactNode }) {
  if (state.status === "loading") return <div className="animate-pulse space-y-3" aria-busy="true"><div className="h-4 w-1/3 rounded bg-border" /><div className="h-28 rounded bg-border" /></div>;
  if (state.status === "error") {
    const unavailable = state.error instanceof ApiError && state.error.status === 503;
    return <Card><p className="text-sm font-semibold text-danger">{unavailable ? "C3 artifact unavailable" : "Could not load AOP-BCS data"}</p><p className="mt-1 text-sm text-muted">{state.error.message}</p>{unavailable && <p className="mt-2 text-xs text-muted">Restore the required versioned C3 artifacts and reload this page.</p>}</Card>;
  }
  return <>{render(state.data)}</>;
}
