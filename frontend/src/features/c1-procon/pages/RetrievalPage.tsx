import { useApi } from "@/lib/api/useApi";
import { c1Api } from "@/features/c1-procon/services/api";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader, StatTile } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { C1_COLORS, Callout, HBarChart, Legend } from "@/features/c1-procon/components/charts";
import type { BarItem } from "@/features/c1-procon/components/charts";
import { SimpleTable, ci, fmt } from "@/features/c1-procon/components/SimpleTable";

export function RetrievalPage() {
  const state = useApi(c1Api.retrieval, []);

  return (
    <DataState
      state={state}
      render={(data) => {
        const apItems: BarItem[] = data.representations
          .filter((r) => r.kind !== "chance")
          .sort((a, b) => b.ap - a.ap)
          .map((r) => ({
            label: r.representation,
            value: r.ap,
            lo: r.ap_lo,
            hi: r.ap_hi,
            color: r.kind === "baseline" ? C1_COLORS.baseline : C1_COLORS.trained,
          }));
        const untrained = data.representations.find((r) => r.representation === "RAW 650M")?.ap ?? 0;

        return (
          <div className="space-y-6">
            <Card>
              <CardHeader title="Steps 4-6 - Metal-chelation retrieval" subtitle={`${data.mode} mode · ${data.n_queries} MC-active queries`} />
              <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>
                {data.note}
              </p>
              <div className="mt-4 grid grid-cols-2 gap-6 sm:grid-cols-4">
                <StatTile label="trained runs" value={data.trained_runs_total} hint="5 recipes × 5 seeds" />
                <StatTile label="above untrained embedding" value={`${data.trained_runs_above_untrained} of ${data.trained_runs_total}`} />
                <StatTile label="chance AP" value={data.chance_ap.toFixed(3)} hint="random ranking" />
                <StatTile label="untrained ESM-2 AP" value={untrained.toFixed(3)} hint="the bar to beat" />
              </div>
            </Card>

            <Card>
              <CardHeader
                title="Average precision by representation"
                subtitle="Longer bar = better. Whiskers are 95% confidence intervals; the dashed line is a random ranking."
              />
              <HBarChart
                items={apItems}
                min={0}
                max={0.27}
                decimals={3}
                labelWidth={190}
                refs={[{ value: data.chance_ap, label: `random ranking ${data.chance_ap.toFixed(3)}` }]}
                ariaLabel="Average precision per representation"
              />
              <Legend entries={[[C1_COLORS.baseline, "simple baselines (length, composition, untrained ESM-2)"], [C1_COLORS.trained, "trained contrastive heads"]]} />
              <div className="mt-4">
                <Callout title="What this shows" tone="bad">
                  The green bars (no training) are longer than the purple bars (trained heads). The best simple rule, peptide length alone, beats the main trained model
                  (Primary) by a wide margin. Training the contrastive head did not add useful mechanism information.
                </Callout>
              </div>
            </Card>

            <Card>
              <CardHeader title="Main trained model against the baselines" subtitle="Paired differences in AP on the same queries; Holm-corrected p-values." />
              <SimpleTable
                headers={["Comparison", "AP (A)", "AP (B)", "ΔAP", "95% CI", "p (Holm)", "Verdict"]}
                rows={data.paired
                  .filter((p) => p.comparison.startsWith("Primary vs"))
                  .map((p) => [p.comparison, fmt(p.ap_a), fmt(p.ap_b), fmt(p.delta_ap), ci(p.ci_lo, p.ci_hi), p.p_holm.toExponential(1), <Badge key={p.comparison} tone="warning">{p.verdict}</Badge>])}
              />
            </Card>

          </div>
        );
      }}
    />
  );
}
