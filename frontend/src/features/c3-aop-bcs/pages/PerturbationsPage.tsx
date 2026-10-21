import { DataState } from "@/components/research/DataState";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader, StatTile } from "@/components/ui/Card";
import { useDashboard } from "@/features/c3-aop-bcs/hooks/useDashboard";

const substitutions = { P1: "WYHMC → A", P2: "BLOSUM62 ≥ 1", P3: "Seeded random" };

export function PerturbationsPage() {
  const state = useDashboard();
  return <DataState state={state} render={(data) => <div className="space-y-6">
    <div className="grid gap-4 lg:grid-cols-3">{data.perturbations.map((item) => <Card key={item.id}><div className="flex items-center justify-between gap-2"><Badge tone={item.id === "P1" ? "danger" : item.id === "P2" ? "success" : "accent"}>{item.id}</Badge><code className="text-xs text-muted">{substitutions[item.id]}</code></div><h3 className="mt-4 font-semibold">{item.title}</h3><p className="text-xs text-muted">{item.subtitle}</p><p className="mt-3 text-sm font-medium">{item.question}</p><p className="mt-2 text-sm text-muted">{item.rule}</p><div className="mt-5 grid grid-cols-2 gap-4"><StatTile label="Pilot" value={item.pilotCount} /><StatTile label="Full" value={item.fullCount.toLocaleString()} /></div></Card>)}</div>
    <Card><CardHeader title="Frozen perturbation configuration" subtitle="Loaded from the C3 run manifest and research configuration." /><div className="grid grid-cols-2 gap-6 lg:grid-cols-4"><StatTile label="Redox set" value={data.configuration.redoxResidues.join(", ")} /><StatTile label="Master seed" value={data.configuration.seed} /><StatTile label="P2 minimum BLOSUM62" value={`≥ ${data.configuration.blosumMinimum}`} /><StatTile label="Primary threshold" value={`δ = ${data.configuration.primaryDelta}`} /></div></Card>
    <Card><CardHeader title="Automatic validation" subtitle="Required for every accepted variant." /><div className="grid gap-4 md:grid-cols-2"><div className="rounded-lg border p-4" style={{ borderColor: "var(--color-border)" }}><strong className="text-sm">Structural checks</strong><p className="mt-1 text-sm text-muted">Exactly one declared position changes and sequence length remains unchanged.</p></div><div className="rounded-lg border p-4" style={{ borderColor: "var(--color-border)" }}><strong className="text-sm">Rule-specific checks</strong><p className="mt-1 text-sm text-muted">P1 redox-to-A, P2 eligible BLOSUM62 edit, and P3 seeded non-self substitution.</p></div></div></Card>
  </div>} />;
}
