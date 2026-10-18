import { useApi } from "@/lib/api/useApi";
import { c2Api } from "@/features/c2-pu/services/api";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader, StatTile } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LimitationsPanel } from "@/components/research/LimitationsPanel";

export function OverviewPage() {
  const state = useApi(c2Api.overview, []);

  return (
    <DataState
      state={state}
      render={(overview) => (
        <div className="space-y-6">
          <Card>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <Badge tone="accent">Component 02 — PU-AOP</Badge>
                <h2 className="mt-2 text-xl font-bold">{overview.research_title}</h2>
                <p className="mt-2 max-w-3xl text-sm" style={{ color: "var(--color-text-muted)" }}>
                  {overview.objective}
                </p>
              </div>
              <div className="flex flex-col items-end gap-1 text-right text-xs" style={{ color: "var(--color-text-muted)" }}>
                <Badge tone="warning">{overview.freeze_decision}</Badge>
                <span>Freeze: {overview.freeze_id}</span>
                <span>Tag: {overview.release_tag}</span>
                <span>Frozen: {overview.freeze_date}</span>
              </div>
            </div>
          </Card>

          <Card>
            <CardHeader title="FR1–FR4 milestones" />
            <dl className="grid gap-4 sm:grid-cols-2">
              {Object.entries(overview.fr_milestones).map(([fr, description]) => (
                <div key={fr}>
                  <dt className="text-sm font-semibold">{fr}</dt>
                  <dd className="text-sm" style={{ color: "var(--color-text-muted)" }}>
                    {description}
                  </dd>
                </div>
              ))}
            </dl>
          </Card>

          <Card>
            <CardHeader title="Accepted data at a glance" />
            <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
              {Object.entries(overview.data_counts).map(([key, value]) => (
                <StatTile key={key} label={key.replaceAll("_", " ")} value={value.toLocaleString()} />
              ))}
              <StatTile label="baseline models" value={overview.model_count} />
            </div>
          </Card>

          <Card>
            <CardHeader title="Scientific status" subtitle="Technical reproducibility and scientific validation are different claims." />
            <div className="grid gap-4 sm:grid-cols-3">
              <StatTile label="Technical" value="Accepted" hint={overview.caveats.technical_status} />
              <StatTile label="Scientific" value="Not established" hint={overview.caveats.scientific_status} />
              <StatTile label="Supervisor approval" value="Pending items" hint={overview.caveats.supervisor_approval_status} />
            </div>
          </Card>

          <LimitationsPanel items={overview.caveats.known_limitations} />
        </div>
      )}
    />
  );
}
