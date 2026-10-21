import { useApi } from "@/lib/api/useApi";
import { c2Api } from "@/features/c2-pu/services/api";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader, StatTile } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LimitationsPanel } from "@/components/research/LimitationsPanel";
import type { TrackedSourceReport } from "@/features/c2-pu/types";

const STATUS_BADGE: Record<TrackedSourceReport["status"], { tone: "success" | "danger" | "neutral"; label: string }> = {
  verified: { tone: "success", label: "Verified" },
  present: { tone: "neutral", label: "Present" },
  modified: { tone: "success", label: "Modified" },
  missing: { tone: "danger", label: "Missing" },
};

export function EvidencePage() {
  const state = useApi(c2Api.artifactStatus, []);

  return (
    <DataState
      state={state}
      render={(status) => (
        <div className="space-y-6">
          <Card>
            <CardHeader
              title="Research Evidence & Reproducibility"
              subtitle={`Freeze: ${status.freeze_id} (${status.release_tag})`}
            />
            <div className="mb-4">
              <Badge tone="warning">{status.freeze_decision}</Badge>
            </div>
            <div className="grid grid-cols-2 gap-6 sm:grid-cols-3">
              <StatTile label="Tracked artifacts" value={status.total_tracked} />
              <StatTile label="Present on this checkout" value={status.present_count} />
              <StatTile label="Missing on this checkout" value={status.missing_count} />
            </div>
            <p className="mt-4 text-xs" style={{ color: "var(--color-text-muted)" }}>
              Existence check only (no re-hashing on every request) for the full 170-file
              inventory. For a byte-for-byte integrity re-verification, run{" "}
              <code className="rounded bg-black/10 px-1 py-0.5">
                python -m plantaox.c2_pu.pp1_freeze verify
              </code>{" "}
              offline, per docs/PP1_DASHBOARD_SETUP.md.
            </p>
          </Card>

          <Card className="overflow-x-auto">
            <CardHeader
              title="Tracked Source Reports"
              subtitle="SHA-256 is recomputed live by the API for each file below, then compared against the frozen manifest."
            />
            <table className="w-full min-w-[640px] text-left text-sm">
              <thead>
                <tr className="text-xs uppercase" style={{ color: "var(--color-text-muted)" }}>
                  <th className="pb-2">Category</th>
                  <th className="pb-2">File</th>
                  <th className="pb-2">SHA-256</th>
                  <th className="pb-2">Status</th>
                </tr>
              </thead>
              <tbody>
                {status.tracked_source_reports.map((report) => {
                  const badge = STATUS_BADGE[report.status];
                  return (
                    <tr key={report.path} className="border-t" style={{ borderColor: "var(--color-border)" }}>
                      <th className="py-3 pr-4 text-left font-medium" style={{ color: "var(--color-text)" }}>
                        {report.category}
                        <div className="text-xs font-normal" style={{ color: "var(--color-text-muted)" }}>
                          {report.label}
                        </div>
                      </th>
                      <td className="max-w-md break-all py-3 pr-4 font-mono text-xs">{report.path}</td>
                      <td className="py-3 pr-4 font-mono text-xs">
                        {report.sha256 ? `${report.sha256.slice(0, 12)}...` : "N/A"}
                      </td>
                      <td className="py-3">
                        <Badge tone={badge.tone}>{badge.label}</Badge>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </Card>

          {status.missing_count > 0 && (
            <Card>
              <CardHeader title="Missing Artifacts on This Checkout" />
              <ul className="list-disc space-y-1 pl-4 text-sm font-mono">
                {status.missing_paths.map((path) => (
                  <li key={path}>{path}</li>
                ))}
              </ul>
            </Card>
          )}

          <LimitationsPanel title="Open Supervisor Decisions" items={status.pending_decisions} />
        </div>
      )}
    />
  );
}
