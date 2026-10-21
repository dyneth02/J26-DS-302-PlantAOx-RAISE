import type { ComponentType } from "react";
import { useApi } from "@/lib/api/useApi";
import { c2Api } from "@/features/c2-pu/services/api";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader, StatTile } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LimitationsPanel } from "@/components/research/LimitationsPanel";
import { BarChart3, Dna, FlaskConical, GitBranch, Layers, Lock, Sparkles } from "lucide-react";

const MILESTONE_ICONS: Record<string, ComponentType<{ size?: number }>> = {
  SO1: Dna,
  SO2: Layers,
  SO3: Sparkles,
  SO4: BarChart3,
};

const STATUS_ACCENT: Record<"technical" | "scientific" | "approval", string> = {
  technical: "var(--color-success-border)",
  scientific: "var(--color-danger-border)",
  approval: "var(--color-warning-border)",
};

export function OverviewPage() {
  const state = useApi(c2Api.overview, []);

  return (
    <DataState
      state={state}
      render={(overview) => {
        const milestoneEntries = Object.entries(overview.fr_milestones).sort(([a], [b]) => a.localeCompare(b));

        return (
          <div className="space-y-6">
            {/* Hero */}
            <Card className="relative overflow-hidden">
              <div
                aria-hidden="true"
                className="absolute inset-x-0 top-0 h-1"
                style={{ background: "linear-gradient(90deg, var(--color-primary), var(--color-accent))" }}
              />
              <div className="flex flex-wrap items-start justify-between gap-6 pt-1">
                <div className="max-w-3xl">
                  <Badge tone="accent">Component 02 · PU-AOP</Badge>
                  <h2 className="mt-3 text-2xl font-bold leading-tight">{overview.research_title}</h2>
                  <p className="mt-3 text-sm leading-relaxed" style={{ color: "var(--color-text-muted)" }}>
                    {overview.objective}
                  </p>
                </div>

                <div
                  className="flex min-w-[220px] flex-col gap-2 rounded-xl border p-4"
                  style={{ borderColor: "var(--color-border)", background: "var(--color-bg)" }}
                >
                  <div className="flex items-center gap-2">
                    <Lock size={14} style={{ color: "var(--color-text-muted)" }} />
                    <span className="text-xs font-semibold uppercase tracking-wide" style={{ color: "var(--color-text-muted)" }}>
                      Release Status
                    </span>
                  </div>
                  <Badge tone="warning">{overview.freeze_decision}</Badge>
                  <dl className="mt-1 space-y-1 text-xs" style={{ color: "var(--color-text-muted)" }}>
                    <div className="flex justify-between gap-3">
                      <dt>Freeze ID</dt>
                      <dd className="font-mono">{overview.freeze_id}</dd>
                    </div>
                    <div className="flex justify-between gap-3">
                      <dt>Tag</dt>
                      <dd className="font-mono">{overview.release_tag}</dd>
                    </div>
                    <div className="flex justify-between gap-3">
                      <dt>Frozen</dt>
                      <dd>{overview.freeze_date}</dd>
                    </div>
                  </dl>
                </div>
              </div>
            </Card>

            {/* Research workflow / SO milestones */}
            <Card>
              <CardHeader title="Research Workflow" subtitle="Sub-Objectives SO1-SO4, in execution order." />
              <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
                {milestoneEntries.map(([so, description], index) => {
                  const Icon = MILESTONE_ICONS[so] ?? GitBranch;
                  return (
                    <div
                      key={so}
                      className="relative flex flex-col gap-2 rounded-xl border p-4"
                      style={{ borderColor: "var(--color-border)" }}
                    >
                      <div className="flex items-center gap-2">
                        <div
                          className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg"
                          style={{ background: "var(--color-primary)", color: "white" }}
                        >
                          <Icon size={16} />
                        </div>
                        <span className="text-sm font-bold">{so}</span>
                      </div>
                      <p className="text-xs leading-relaxed" style={{ color: "var(--color-text-muted)" }}>
                        {description}
                      </p>
                      {index < milestoneEntries.length - 1 && (
                        <span
                          aria-hidden="true"
                          className="absolute top-1/2 -right-3 hidden -translate-y-1/2 text-sm lg:block"
                          style={{ color: "var(--color-text-muted)" }}
                        >
                          &rarr;
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </Card>

            {/* Data at a glance */}
            <Card>
              <CardHeader title="Accepted Data at a Glance" subtitle="Counts from the frozen PP1 release, not live-recomputed." />
              <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
                {Object.entries(overview.data_counts).map(([key, value]) => (
                  <StatTile key={key} label={key.replaceAll("_", " ")} value={value.toLocaleString()} />
                ))}
                <StatTile label="baseline models" value={overview.model_count} />
              </div>
            </Card>

            {/* Scientific status */}
            <Card>
              <CardHeader
                title="Scientific Status"
                subtitle="Technical reproducibility and scientific validation are different claims."
              />
              <div className="grid gap-4 sm:grid-cols-3">
                <StatusBlock
                  icon={FlaskConical}
                  accent={STATUS_ACCENT.technical}
                  label="Technical"
                  value="Accepted"
                  hint={overview.caveats.technical_status}
                />
                <StatusBlock
                  icon={Sparkles}
                  accent={STATUS_ACCENT.scientific}
                  label="Scientific"
                  value="Not Established"
                  hint={overview.caveats.scientific_status}
                />
                <StatusBlock
                  icon={GitBranch}
                  accent={STATUS_ACCENT.approval}
                  label="Supervisor Approval"
                  value="Pending Items"
                  hint={overview.caveats.supervisor_approval_status}
                />
              </div>
            </Card>

            <LimitationsPanel items={overview.caveats.known_limitations} />
          </div>
        );
      }}
    />
  );
}

function StatusBlock({
  icon: Icon,
  accent,
  label,
  value,
  hint,
}: {
  icon: ComponentType<{ size?: number }>;
  accent: string;
  label: string;
  value: string;
  hint: string;
}) {
  return (
    <div className="rounded-xl border-l-4 border-t border-r border-b p-4" style={{ borderColor: "var(--color-border)", borderLeftColor: accent }}>
      <div className="mb-2 flex items-center gap-2" style={{ color: "var(--color-text-muted)" }}>
        <Icon size={14} />
        <span className="text-xs font-semibold uppercase tracking-wide">{label}</span>
      </div>
      <p className="text-lg font-semibold">{value}</p>
      <p className="mt-1 text-xs" style={{ color: "var(--color-text-muted)" }}>
        {hint}
      </p>
    </div>
  );
}
