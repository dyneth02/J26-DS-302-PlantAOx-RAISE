import { useApi } from "@/lib/api/useApi";
import { c1Api } from "@/features/c1-procon/services/api";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader, StatTile } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LimitationsPanel } from "@/components/research/LimitationsPanel";
import { C1_COLORS, Callout, HBarChart, Legend } from "@/features/c1-procon/components/charts";
import type { BarItem } from "@/features/c1-procon/components/charts";
import { SimpleTable, ci, fmt } from "@/features/c1-procon/components/SimpleTable";

const SIMPLE = new Set(["SOURCE", "LENGTH", "AAC-20", "DESC-14", "AAC-20 + LENGTH", "AAC-20 + LENGTH + SOURCE"]);

export function ProbePage() {
  const state = useApi(c1Api.probe, []);

  return (
    <DataState
      state={state}
      render={(data) => {
        const items: BarItem[] = data.grouped.map((r) => ({
          label: r.features,
          value: r.auroc,
          lo: r.lo,
          hi: r.hi,
          color: SIMPLE.has(r.features) ? C1_COLORS.baseline : C1_COLORS.trained,
        }));
        const leakyItems: BarItem[] = data.leaky.flatMap((l) => {
          const g = data.grouped.find((r) => r.features === l.features);
          return [
            { label: `${l.features} - honest (grouped folds)`, value: g?.auroc ?? 0, color: C1_COLORS.baseline },
            { label: `${l.features} - leaky (random folds)`, value: l.auroc, color: C1_COLORS.bad },
          ];
        });

        return (
          <div className="space-y-6">
            <Card>
              <CardHeader title="Step 5 - Supervised probe (MC-active vs FRS-only)" subtitle={`${data.mode} mode · repeated grouped cross-validation`} />
              <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>
                {data.evaluation_note}
              </p>
              <div className="mt-4 grid grid-cols-2 gap-6 sm:grid-cols-4">
                <StatTile label="chance (noise null band)" value={data.null_band.auroc.toFixed(3)} hint={`2.5-97.5%: ${ci(data.null_band.lo, data.null_band.hi)}`} />
                {Object.entries(data.leakage_inflation).map(([name, value]) => (
                  <StatTile key={name} label={`leakage inflation, ${name}`} value={`+${value.toFixed(3)}`} hint="leaky minus grouped folds" />
                ))}
              </div>
            </Card>

            <Card>
              <CardHeader title="Fold-mean AUROC by feature set" subtitle="Whiskers are 95% bootstrap intervals; the shaded band is what pure noise scores (20 random draws)." />
              <HBarChart
                items={items}
                min={0.4}
                max={0.85}
                decimals={3}
                labelWidth={290}
                bands={[{ lo: data.null_band.lo, hi: data.null_band.hi, label: `chance band ${data.null_band.lo.toFixed(2)}-${data.null_band.hi.toFixed(2)}` }]}
                refs={[{ value: 0.5, label: "random guess 0.5", color: C1_COLORS.muted }]}
                ariaLabel="Probe AUROC per feature set"
              />
              <Legend entries={[[C1_COLORS.baseline, "simple features (source, length, composition, descriptors)"], [C1_COLORS.trained, "feature sets that include ESM-2"]]} />
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <Callout title="What this shows" tone="warn">
                  A single yes/no feature, which database a peptide came from, scores about as high as ESM-2. Composition + length + source together are the best, and adding ESM-2 650M on
                  top changes the score by about +0.005 (no real gain).
                </Callout>
                <Callout title="Why it is not mechanism evidence" tone="info">
                  The two classes were collected from different places and have different peptide lengths, so a model can score above chance by learning those shortcuts instead
                  of the antioxidant mechanism (see the Confounds page).
                </Callout>
              </div>
            </Card>

            <Card>
              <CardHeader title="Leaky versus honest splits" subtitle="The same probe, with similar peptides allowed on both sides of the split (red) or kept together (teal)." />
              <HBarChart items={leakyItems} min={0.4} max={0.85} decimals={3} labelWidth={330} ariaLabel="Probe AUROC with grouped and leaky folds" />
              <div className="mt-4">
                <Callout title="Why we group similar peptides" tone="bad">
                  With leaky folds the score looks 0.13 to 0.19 better. That gain is memorisation of near-duplicates, not learning, which is why every number in this project uses
                  grouped folds.
                </Callout>
              </div>
            </Card>

            <Card>
              <CardHeader title="Paired differences" subtitle="Same folds, same bootstrap resamples. A CI that includes 0 means no difference was detected." />
              <SimpleTable
                headers={["A", "B", "ΔAUROC (A − B)", "95% CI", "Repeats with Δ>0", "Verdict"]}
                rows={data.paired.map((p) => [
                  p.model_a,
                  p.model_b,
                  fmt(p.delta_auroc),
                  ci(p.ci_lo, p.ci_hi),
                  `${p.repeats_delta_gt_0} of 10`,
                  <Badge key={`${p.model_a}-${p.model_b}`} tone={p.verdict === "no difference detected" ? "neutral" : "warning"}>{p.verdict}</Badge>,
                ])}
              />
            </Card>

            <LimitationsPanel
              title="Reading these scores"
              items={[
                "A single noise draw is not chance: the 20-seed null band is the chance reference.",
                "Single-split or pooled AUROC values are not reported on their own; they move by up to 0.06 between splits.",
              ]}
            />
          </div>
        );
      }}
    />
  );
}
