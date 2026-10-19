import { useApi } from "@/lib/api/useApi";
import { c1Api } from "@/features/c1-procon/services/api";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader, StatTile } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { SimpleTable } from "@/features/c1-procon/components/SimpleTable";

export function EvidencePage() {
  const state = useApi(c1Api.artifactStatus, []);

  return (
    <DataState
      state={state}
      render={(status) => (
        <div className="space-y-6">
          <Card>
            <CardHeader title="Research evidence & reproducibility" subtitle="Existence check of the accepted result tables this dashboard reads." />
            <div className="grid grid-cols-2 gap-6 sm:grid-cols-3">
              <StatTile label="Tracked artifacts" value={status.artifacts.length} />
              <StatTile label="Present on this checkout" value={status.artifacts.filter((a) => a.exists).length} />
              <StatTile label="Missing on this checkout" value={status.missing.length} />
            </div>
            <p className="mt-4 text-xs" style={{ color: "var(--color-text-muted)" }}>
              Every notebook asserts the benchmark fingerprint and the SHA-256 of its inputs; trained checkpoints are not committed
              (their SHA-256 is in data/processed/c1_procon/results/checkpoint_sha256.csv).
            </p>
          </Card>

          <Card>
            <SimpleTable
              headers={["Category", "File", "Present"]}
              rows={status.artifacts.map((a) => [
                a.category,
                <code key={a.path} className="text-xs">{a.path}</code>,
                <Badge key={`${a.path}-badge`} tone={a.exists ? "success" : "danger"}>{a.exists ? "yes" : "missing"}</Badge>,
              ])}
            />
          </Card>
        </div>
      )}
    />
  );
}
