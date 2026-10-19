import { useApi } from "@/lib/api/useApi";
import { c1Api } from "@/features/c1-procon/services/api";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { C1_COLORS, Callout, HBarChart, Legend } from "@/features/c1-procon/components/charts";
import type { BarItem } from "@/features/c1-procon/components/charts";
import { SimpleTable, ci, fmt } from "@/features/c1-procon/components/SimpleTable";
import { CartesianGrid, Legend as ChartLegend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ConfoundRow } from "@/features/c1-procon/types";

const TOOLTIP_STYLE = { background: "var(--color-surface)", borderColor: "var(--color-border)" };
const LINE_COLORS = ["var(--color-primary)", "var(--color-accent)", "var(--color-danger-text)", "var(--color-warning-text)"];
const isEsm = (name: string) => name.startsWith("ESM-2");

function rowsToBars(rows: ConfoundRow[]): BarItem[] {
  return rows
    .filter((r) => !r.features.startsWith("RANDOM noise") && !r.features.startsWith("NULL band"))
    .map((r) => ({ label: r.features, value: r.auroc, lo: r.lo, hi: r.hi, color: isEsm(r.features) ? C1_COLORS.trained : C1_COLORS.baseline }));
}

export function ConfoundsPage() {
  const state = useApi(c1Api.confounds, []);

  return (
    <DataState
      state={state}
      render={(data) => {
        const nullStrict = data.strict.find((r) => r.features.startsWith("NULL band"));
        const nullAnox = data.anoxpepred_only.find((r) => r.features.startsWith("NULL band"));
        const curveFeatures = Array.from(new Set(data.learning_curve.map((p) => p.features)));
        const fractions = Array.from(new Set(data.learning_curve.map((p) => p.train_frac))).sort((a, b) => a - b);
        const curveData = fractions.map((frac) => {
          const row: Record<string, number | string> = { fraction: `${Math.round(frac * 100)}%` };
          for (const feature of curveFeatures) {
            const point = data.learning_curve.find((p) => p.features === feature && p.train_frac === frac);
            if (point) row[feature] = Number(point.auroc.toFixed(3));
          }
          return row;
        });
        const lengthMatched: BarItem[] = data.length_matched
          .filter((r) => r.pool === "strict" && !r.features.startsWith("DELTA"))
          .map((r) => ({ label: r.features, value: r.auroc_mean, lo: r.auroc_p2_5, hi: r.auroc_p97_5, color: isEsm(r.features) ? C1_COLORS.trained : C1_COLORS.baseline }));

        return (
          <div className="space-y-6">
            <Callout title="Step 8 verdict" tone="warn">
              {data.verdict}
            </Callout>

            <Card>
              <CardHeader title="Strict pool - what each feature set can do" subtitle="Fold-mean AUROC with 95% group-bootstrap whiskers; the shaded band is pure noise." />
              <HBarChart
                items={rowsToBars(data.strict)}
                min={0.4}
                max={0.9}
                decimals={3}
                labelWidth={250}
                bands={nullStrict ? [{ lo: nullStrict.lo, hi: nullStrict.hi, label: "chance band" }] : []}
                ariaLabel="Strict pool probe AUROC"
              />
              <Legend entries={[[C1_COLORS.baseline, "simple features"], [C1_COLORS.trained, "ESM-2 features"]]} />
              <div className="mt-4">
                <Callout title="What this shows" tone="info">
                  Data source alone is already as good as ESM-2, and composition + length + source is better than any ESM-2 row. The AI model is not finding something the simple
                  features miss.
                </Callout>
              </div>
            </Card>

            <Card>
              <CardHeader title="Removing the source shortcut (AnOxPePred only: 75 MC-active vs 565 FRS-only)" subtitle="Both classes now come from one database, so the source cannot help." />
              <HBarChart
                items={rowsToBars(data.anoxpepred_only)}
                min={0.4}
                max={0.85}
                decimals={3}
                labelWidth={250}
                bands={nullAnox ? [{ lo: nullAnox.lo, hi: nullAnox.hi, label: "chance band" }] : []}
                ariaLabel="AnOxPePred-only probe AUROC"
              />
            </Card>

            <Card>
              <CardHeader title="Does ESM-2 add anything on top of simple features?" subtitle="Paired ΔAUROC; a CI that includes 0 means no gain was detected." />
              <SimpleTable
                headers={["Context", "Model", "Reference", "ΔAUROC", "95% CI", "Verdict"]}
                rows={data.esm_over_confounds.map((d) => [
                  d.context,
                  d.model,
                  d.reference,
                  fmt(d.delta_auroc),
                  ci(d.lo, d.hi),
                  <Badge key={`${d.context}-${d.model}`} tone={d.verdict === "no difference detected" ? "neutral" : "warning"}>{d.verdict}</Badge>,
                ])}
              />
            </Card>

            <Card>
              <CardHeader
                title="Removing the length shortcut (same tripeptide share in both classes)"
                subtitle="Mean of 20 random subsamples. A length-only score below 0.5 means the length signal is gone."
              />
              <HBarChart items={lengthMatched} min={0.3} max={0.8} decimals={3} labelWidth={200} refs={[{ value: 0.5, label: "random guess 0.5", color: C1_COLORS.muted }]} ariaLabel="Length-matched probe AUROC" />
              <div className="mt-4">
                <Callout title="What this shows" tone="good">
                  After matching lengths, length alone drops to 0.41, so its earlier signal was a confound. Composition and ESM-2 stay around 0.58 to 0.60, a weak
                  composition-level difference.
                </Callout>
              </div>
            </Card>

            <Card>
              <CardHeader title="Does more data help? Learning curve (strict pool)" subtitle="Most curves are flat after about half of the training groups: more of the same data is not the bottleneck." />
              <div style={{ width: "100%", height: 320 }}>
                <ResponsiveContainer>
                  <LineChart data={curveData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis dataKey="fraction" stroke="var(--color-text-muted)" fontSize={12} />
                    <YAxis stroke="var(--color-text-muted)" fontSize={12} domain={[0.45, 0.8]} />
                    <Tooltip contentStyle={TOOLTIP_STYLE} />
                    <ChartLegend />
                    {curveFeatures.map((feature, i) => (
                      <Line key={feature} type="monotone" dataKey={feature} stroke={LINE_COLORS[i % LINE_COLORS.length]} dot={false} strokeWidth={2} />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card>
              <CardHeader title="Why single-split numbers are not quoted" subtitle="The same recipe gives different AUROCs under different split designs." />
              <SimpleTable
                headers={["Feature set", "Split design", "Pooled AUROC", "Fold-mean AUROC"]}
                rows={data.cv_design.map((r) => [r.features, r.design, fmt(r.auroc_pooled), fmt(r.auroc_foldmean)])}
              />
            </Card>
          </div>
        );
      }}
    />
  );
}
