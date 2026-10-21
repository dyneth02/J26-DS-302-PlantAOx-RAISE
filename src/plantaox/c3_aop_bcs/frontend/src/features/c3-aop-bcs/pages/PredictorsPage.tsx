import { DataState } from "@/components/research/DataState";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader } from "@/components/ui/Card";
import { ScientificBoundary } from "@/features/c3-aop-bcs/components/ScientificBoundary";
import { useDashboard } from "@/features/c3-aop-bcs/hooks/useDashboard";

export function PredictorsPage() {
  const state = useDashboard();
  return <DataState state={state} render={(data) => <div className="space-y-6">
    <Card><CardHeader title="Predictor integration status" subtitle="A predictor stays not integrated until C3 retains a verified finite real score and its runtime/model evidence." /><div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="text-xs uppercase text-muted"><tr><th className="py-2">Order</th><th>Predictor</th><th>Tier</th><th>Readiness</th><th>Status</th></tr></thead><tbody>{data.predictors.map((predictor) => <tr key={predictor.id} className="border-t align-top" style={{ borderColor: "var(--color-border)" }}><td className="py-3">{String(predictor.order).padStart(2, "0")}</td><th className="py-3 font-medium">{predictor.name}<p className="mt-1 max-w-xl text-xs font-normal text-muted">{predictor.rationale}</p></th><td className="py-3"><Badge tone={predictor.tier === "primary" ? "accent" : "neutral"}>{predictor.tier}</Badge></td><td className="py-3 text-muted">{predictor.readiness.replaceAll("-", " ").replaceAll("_", " ")}</td><td className="py-3"><Badge tone="danger">Not integrated</Badge></td></tr>)}</tbody></table></div></Card>
    <div className="grid gap-4 md:grid-cols-2"><Card><CardHeader title="PP1 minimum viable set" subtitle="Priority is based on reproducibility and access readiness." /><ol className="list-decimal space-y-2 pl-5 text-sm"><li>AOPxSVM</li><li>AnOxPePred</li><li>PU-AOP after the Component 2 handoff</li></ol></Card><Card><CardHeader title="PU-AOP dependency" subtitle="Component 2 handoff remains pending." /><p className="text-sm text-muted">Required: frozen model selection, checkpoint and hash, preprocessing lineage, inference entry point, score semantics, dependencies, and a reference sequence with its expected score.</p><div className="mt-3"><Badge tone="warning">C3 will not guess the model</Badge></div></Card></div>
    <ScientificBoundary />
  </div>} />;
}
