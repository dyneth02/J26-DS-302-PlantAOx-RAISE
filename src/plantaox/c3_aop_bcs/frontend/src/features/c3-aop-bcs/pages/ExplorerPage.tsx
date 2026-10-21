import { useState } from "react";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader, StatTile } from "@/components/ui/Card";
import { ScientificBoundary } from "@/features/c3-aop-bcs/components/ScientificBoundary";
import { useDashboard } from "@/features/c3-aop-bcs/hooks/useDashboard";

type Kind = "P1" | "P2" | "P3";
function sequence(sequenceValue: string, position: number, className: string) {
  return [...sequenceValue].map((residue, index) => <span key={`${index}-${residue}`} className={index + 1 === position ? className : ""}>{residue}</span>);
}

export function ExplorerPage() {
  const state = useDashboard();
  const [kind, setKind] = useState<Kind>("P1");
  const [index, setIndex] = useState(0);
  return <DataState state={state} render={(data) => {
    const examples = data.examples.filter((row) => row.perturbation_type === kind);
    const currentIndex = ((index % examples.length) + examples.length) % examples.length;
    const row = examples[currentIndex];
    const metadata = kind === "P2" ? `BLOSUM62 score ${row.blosum62_score}` : kind === "P3" ? `Master seed ${row.random_seed}` : "Redox residue replaced by alanine";
    return <div className="space-y-6">
      <Card><CardHeader title="Variant explorer" subtitle="Inspect the six manually reviewed examples retained in the Task 3.33 artifact." /><div className="flex flex-wrap items-end justify-between gap-4"><label className="text-sm font-medium">Perturbation type<select aria-label="Perturbation type" className="mt-1 block rounded-lg border px-3 py-2" style={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }} value={kind} onChange={(event) => { setKind(event.target.value as Kind); setIndex(0); }}><option value="P1">P1 — Redox disruption</option><option value="P2">P2 — Conservative control</option><option value="P3">P3 — Random control</option></select></label><div className="flex items-center gap-2"><button className="rounded-lg border px-3 py-2 text-sm" style={{ borderColor: "var(--color-border)" }} onClick={() => setIndex(currentIndex - 1)}>Previous</button><span className="text-sm text-muted">{currentIndex + 1} of {examples.length}</span><button className="rounded-lg border px-3 py-2 text-sm" style={{ borderColor: "var(--color-border)" }} onClick={() => setIndex(currentIndex + 1)}>Next</button></div></div></Card>
      <Card><CardHeader title={`${row.mutation} · ${row.sequence_id}`} subtitle={row.variant_id} /><div className="grid gap-4 md:grid-cols-2"><div><p className="mb-2 text-sm font-semibold">Original sequence</p><div className="sequence rounded-lg border p-3" style={{ borderColor: "var(--color-border)" }}>{sequence(row.original_sequence, row.position, "residue-from")}</div></div><div><p className="mb-2 text-sm font-semibold">Perturbed sequence</p><div className="sequence rounded-lg border p-3" style={{ borderColor: "var(--color-border)" }}>{sequence(row.perturbed_sequence, row.position, "residue-to")}</div></div></div><div className="mt-6 grid grid-cols-2 gap-6 lg:grid-cols-4"><StatTile label="Position" value={`${row.position} of ${row.original_sequence.length}`} /><StatTile label="Substitution" value={`${row.original_residue} → ${row.substituted_residue}`} /><StatTile label="Method metadata" value={metadata} /><StatTile label="Inspection" value={row.inspection_status} hint="one-position edit verified" /></div></Card>
      <Card><CardHeader title="Dummy score comparison" subtitle="Software-pipeline evidence only." /><div className="grid grid-cols-3 gap-6"><StatTile label="Original score" value={row.original_score.toFixed(4)} /><StatTile label="Perturbed score" value={row.perturbed_score.toFixed(4)} /><StatTile label="DeltaScore" value={`${row.delta_score >= 0 ? "+" : ""}${row.delta_score.toFixed(4)}`} /></div></Card>
      <ScientificBoundary />
    </div>;
  }} />;
}
