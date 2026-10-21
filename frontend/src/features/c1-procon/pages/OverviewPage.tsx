import { useApi } from "@/lib/api/useApi";
import { c1Api } from "@/features/c1-procon/services/api";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LimitationsPanel } from "@/components/research/LimitationsPanel";
import { C1_COLORS, Callout, HeroStat } from "@/features/c1-procon/components/charts";

const FINDING_TITLES = ["Retrieval", "Supervised probe", "Leakage", "Confound controls"];
const FINDING_BADGES: ["warning" | "danger" | "neutral" | "success", string][] = [
  ["danger", "negative result"],
  ["warning", "weak signal"],
  ["success", "measured"],
  ["warning", "no extra signal"],
];

export function OverviewPage() {
  const state = useApi(c1Api.overview, []);

  return (
    <DataState
      state={state}
      render={(overview) => (
        <div className="space-y-6">
          <Card>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <Badge tone="accent">Component 01 - AOP-ProCon</Badge>
                <h2 className="mt-2 text-xl font-bold">{overview.research_title}</h2>
                <p className="mt-2 max-w-3xl text-sm" style={{ color: "var(--color-text-muted)" }}>
                  {overview.objective}
                </p>
              </div>
              <div className="flex flex-col items-end gap-1 text-right text-xs" style={{ color: "var(--color-text-muted)" }}>
                <Badge tone="warning">Negative result, rigorous evaluation</Badge>
                <span>Benchmark fingerprint: {overview.benchmark_fingerprint}</span>
              </div>
            </div>
          </Card>

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {overview.hero_stats.map((stat, i) => (
              <HeroStat
                key={stat.label}
                value={stat.value}
                label={stat.label}
                hint={stat.hint}
                accent={i === 1 ? C1_COLORS.bad : i === 0 ? C1_COLORS.frs : undefined}
              />
            ))}
          </div>

          <Callout title="The one-sentence story" tone="info" defaultOpen>
            A clean, leak-checked benchmark was built, and a trained contrastive model was compared honestly with simple baselines. The simple baselines win, so the main
            contribution is the benchmark and the evaluation that shows why; the model itself still needs improvement.
          </Callout>

          <Card>
            <CardHeader title="What we found" subtitle="Every number is read from the accepted result tables." />
            <div className="grid gap-3 md:grid-cols-2">
              {overview.headline_findings.map((finding, i) => (
                <div key={finding} className="rounded-xl border p-4" style={{ borderColor: "var(--color-border)" }}>
                  <div className="flex items-center justify-between gap-2">
                    <span className="text-sm font-semibold">{FINDING_TITLES[i] ?? "Finding"}</span>
                    <Badge tone={FINDING_BADGES[i]?.[0] ?? "neutral"}>{FINDING_BADGES[i]?.[1] ?? ""}</Badge>
                  </div>
                  <p className="mt-2 text-sm" style={{ color: "var(--color-text-muted)" }}>
                    {finding}
                  </p>
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <CardHeader title="Pipeline - Steps 1 to 8" subtitle="Notebooks in notebooks/c1_procon; all steps complete and checked." />
            <ol className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              {overview.pipeline_steps.map((step) => (
                <li key={step.step} className="rounded-xl border p-3" style={{ borderColor: "var(--color-border)" }}>
                  <div className="flex items-center gap-2">
                    <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full text-xs font-bold text-white" style={{ background: "var(--color-primary)" }}>
                      {step.step}
                    </span>
                    <span className="text-sm font-semibold">{step.title}</span>
                  </div>
                  <p className="mt-2 text-xs" style={{ color: "var(--color-text-muted)" }}>
                    {step.summary}
                  </p>
                </li>
              ))}
            </ol>
          </Card>

          <LimitationsPanel items={overview.caveats.known_limitations} />
        </div>
      )}
    />
  );
}
