import { DataState } from "@/components/research/DataState";
import { Card, CardHeader } from "@/components/ui/Card";
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
      <div className="grid gap-4 md:grid-cols-2">{data.figures.map((figure) => <Card key={figure.file}><img src={figure.file} alt="AOP-BCS dummy software-pilot result" className="w-full" loading="lazy" /><p className="mt-3 break-all text-xs text-muted">SHA-256: {figure.sha256}</p></Card>)}</div>
      <ScientificBoundary />
    </div>;
  }} />;
}
