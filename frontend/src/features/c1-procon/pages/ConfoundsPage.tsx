import { useApi } from "@/lib/api/useApi";
import { c1Api } from "@/features/c1-procon/services/api";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader } from "@/components/ui/Card";
import { C1_COLORS, Callout, HBarChart, Legend } from "@/features/c1-procon/components/charts";
import type { BarItem } from "@/features/c1-procon/components/charts";
import type { ConfoundRow } from "@/features/c1-procon/types";

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
        const lengthMatched: BarItem[] = data.length_matched
          .filter((r) => r.pool === "strict" && !r.features.startsWith("DELTA"))
          .map((r) => ({ label: r.features, value: r.auroc_mean, lo: r.auroc_p2_5, hi: r.auroc_p97_5, color: isEsm(r.features) ? C1_COLORS.trained : C1_COLORS.baseline }));

        return (
          <div className="space-y-6">
            <Callout title="Step 8 verdict" tone="warn" defaultOpen>
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

          </div>
        );
      }}
    />
  );
}
