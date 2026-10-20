import { Outlet } from "react-router-dom";
import { Badge } from "@/components/ui/Badge";
import { C3Nav } from "@/features/c3-aop-bcs/components/C3Nav";

export function C3Shell() {
  return <section className="space-y-5">
    <div role="status" className="rounded-lg border px-4 py-3 text-sm" style={{ background: "var(--color-warning-bg)", borderColor: "var(--color-warning-border)", color: "var(--color-warning-text)" }}><strong>SOFTWARE-TESTING DATA ONLY</strong><span className="ml-3">Dummy predictor outputs are pipeline evidence, not scientific AOP results.</span></div>
    <div className="flex flex-wrap items-center justify-between gap-3"><div><p className="text-xs font-semibold uppercase tracking-wider text-muted">Component 03</p><h2 className="text-xl font-bold">AOP-BCS</h2></div><Badge tone="warning">Real predictor scoring pending</Badge></div>
    <C3Nav />
    <Outlet />
  </section>;
}
