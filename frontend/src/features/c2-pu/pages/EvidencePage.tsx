import { useApi } from "@/lib/api/useApi";
import { c2Api } from "@/features/c2-pu/services/api";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader, StatTile } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LimitationsPanel } from "@/components/research/LimitationsPanel";

export function EvidencePage() {
  const state = useApi(c2Api.artifactStatus, []);

  return (
    <DataState
      state={state}
      render={(status) => (
        <div className="space-y-6">
          <Card>
            <CardHeader title="Research evidence & reproducibility" subtitle={`Freeze: ${status.freeze_id} (${status.release_tag})`} />
            <div className="mb-4">
              <Badge tone="warning">{status.freeze_decision}</Badge>
            </div>
            <div className="grid grid-cols-2 gap-6 sm:grid-cols-3">
              <StatTile label="Tracked artifacts" value={status.total_tracked} />
              <StatTile label="Present on this checkout" value={status.present_count} />
              <StatTile label="Missing on this checkout" value={status.missing_count} />
            </div>
            <p className="mt-4 text-xs" style={{ color: "var(--color-text-muted)" }}>
              Existence check only (no re-hashing on every request). For a byte-for-byte integrity
              re-verification, run{" "}
              <code className="rounded bg-black/10 px-1 py-0.5">
                python -m plantaox.c2_pu.pp1_freeze verify
              </code>{" "}
              offline, per docs/PP1_DASHBOARD_SETUP.md.
            </p>
          </Card>

          {status.missing_count > 0 && (
            <Card>
              <CardHeader title="Missing artifacts on this checkout" />
              <ul className="list-disc space-y-1 pl-4 text-sm font-mono">
                {status.missing_paths.map((path) => (
                  <li key={path}>{path}</li>
                ))}
              </ul>
            </Card>
          )}

          <LimitationsPanel title="Open supervisor decisions" items={status.pending_decisions} />
        </div>
      )}
    />
  );
}
