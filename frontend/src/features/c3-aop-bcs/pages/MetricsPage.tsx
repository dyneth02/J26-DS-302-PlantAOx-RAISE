import { DataState } from "@/components/research/DataState";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import {
  DeltaDistributionChart,
  MetricSummaryChart,
  PredictionFlipChart,
  ScoreExamplesChart,
} from "@/features/c3-aop-bcs/components/MetricCharts";
import { ScientificBoundary } from "@/features/c3-aop-bcs/components/ScientificBoundary";
import { useDashboard } from "@/features/c3-aop-bcs/hooks/useDashboard";

const percent = (value: number) => `${(value * 100).toFixed(1)}%`;

export function MetricsPage() {
  const state = useDashboard();
  return <DataState state={state} render={(data) => {
    const metrics = [
      ["IR", data.metrics.invarianceRate, `${data.metrics.invariantCount}/${data.metrics.invariantDenominator}`, "P2 edits with |ΔScore| < δ"],
      ["FSR", data.metrics.falseSensitivityRate, `${data.metrics.insufficientCount}/${data.metrics.insufficientDenominator}`, "P1 edits with |ΔScore| < δ"],
      ["BCS", data.metrics.preliminaryBcs, "IR × (1 − FSR)", "Combined behavioural consistency"],
      ["PFR", data.metrics.overallPfr, `${data.metrics.flipCount}/${data.metrics.flipDenominator}`, "Prediction flips across all edits"],
    ] as const;
    return <div className="space-y-6">
      <div className="rounded-lg border px-4 py-3 text-sm" style={{ background: "var(--color-warning-bg)", borderColor: "var(--color-warning-border)", color: "var(--color-warning-text)" }}><strong>DUMMY PREDICTOR METRICS</strong><span className="ml-3">These values demonstrate the calculation pipeline only.</span></div>
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">{metrics.map(([name, value, count, hint]) => <Card key={name}><CardHeader title={name} subtitle={hint} /><div className="flex items-end justify-between gap-2"><strong className="text-3xl">{percent(value)}</strong><span className="text-xs text-muted">{count}</span></div><div className="mt-4 h-2 overflow-hidden rounded-full bg-border"><div className="h-full rounded-full" style={{ width: `${value * 100}%`, background: "var(--color-primary)" }} /></div></Card>)}</div>
      <Card><CardHeader title="Delta-threshold sensitivity" subtitle="Primary δ = 0.05; strict comparison uses |ΔScore| < δ." /><div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="text-xs uppercase text-muted"><tr><th className="py-2">Delta</th><th>IR</th><th>FSR</th><th>BCS</th></tr></thead><tbody>{data.sensitivity.map((row) => <tr key={row.delta} className="border-t" style={{ borderColor: "var(--color-border)" }}><th className="py-3">{row.delta.toFixed(2)} {row.primary && <span className="ml-2 text-xs" style={{ color: "var(--color-success-text)" }}>Primary</span>}</th><td>{row.ir.toFixed(3)}</td><td>{row.fsr.toFixed(3)}</td><td>{row.bcs.toFixed(3)}</td></tr>)}</tbody></table></div></Card>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-base font-semibold">Interactive pilot charts</h3>
          <p className="text-sm text-muted">Native Recharts views generated from the validated API payload—not embedded report images.</p>
        </div>
        <Badge tone="warning">Dummy software test only</Badge>
      </div>
      <div className="grid gap-4 xl:grid-cols-2">
        <Card>
          <CardHeader title="Absolute DeltaScore distributions" subtitle="Percentage of P1, P2, and P3 edits in each 0.05-wide bin; dashed marker shows primary δ." />
          <DeltaDistributionChart data={data.chartData.absoluteDeltaDistribution} />
        </Card>
        <Card>
          <CardHeader title="Original vs perturbed examples" subtitle="Six manually inspected examples retained in the Task 3.33 evidence." />
          <ScoreExamplesChart data={data.chartData.scoreExamples} />
        </Card>
        <Card>
          <CardHeader title="IR / FSR / BCS / PFR summary" subtitle="Pipeline metrics at the primary configuration; values are percentages." />
          <MetricSummaryChart data={data.chartData.metricSummary} />
        </Card>
        <Card>
          <CardHeader title="Prediction flips by perturbation" subtitle="P1, P2, and P3 prediction-flip rates under the dummy threshold of 0.5." />
          <PredictionFlipChart data={data.chartData.predictionFlips} />
        </Card>
      </div>
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs text-muted">
          <span className="min-w-0 break-all">Chart source: <code className="break-all">{data.chartData.source.path}</code></span>
          <span>{data.chartData.source.recordCount} validated rows</span>
          <span className="break-all font-mono">SHA-256: {data.chartData.source.sha256}</span>
        </div>
      </Card>
      <ScientificBoundary />
    </div>;
  }} />;
}
