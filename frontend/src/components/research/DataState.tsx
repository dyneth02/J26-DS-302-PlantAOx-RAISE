import type { ReactNode } from "react";
import type { ApiState } from "@/lib/api/useApi";
import { ApiError } from "@/lib/api/client";
import { Card } from "@/components/ui/Card";

/**
 * Shared loading/error/empty rendering for every dashboard page. An
 * artifact-unavailable (503) response renders as a distinct, explanatory
 * "capability unavailable" state rather than a generic error, per the
 * platform's read-only / graceful-degradation contract.
 */
export function DataState<T>({
  state,
  render,
}: {
  state: ApiState<T>;
  render: (data: T) => ReactNode;
}) {
  if (state.status === "loading") {
    return (
      <div className="animate-pulse space-y-3" aria-busy="true" aria-live="polite">
        <div className="h-4 w-1/3 rounded" style={{ background: "var(--color-border)" }} />
        <div className="h-24 w-full rounded" style={{ background: "var(--color-border)" }} />
      </div>
    );
  }

  if (state.status === "error") {
    const isUnavailable = state.error instanceof ApiError && state.error.status === 503;
    return (
      <Card>
        <p className="text-sm font-semibold" style={{ color: "var(--color-danger-text)" }}>
          {isUnavailable ? "Artifact unavailable in this checkout" : "Could not load this data"}
        </p>
        <p className="mt-1 text-sm" style={{ color: "var(--color-text-muted)" }}>
          {state.error.message}
        </p>
        {isUnavailable && (
          <p className="mt-2 text-xs" style={{ color: "var(--color-text-muted)" }}>
            This can occur when Git-ignored research artifacts are absent from the checkout.
            Check the relevant component handover for recovery instructions.
          </p>
        )}
      </Card>
    );
  }

  return <>{render(state.data)}</>;
}
