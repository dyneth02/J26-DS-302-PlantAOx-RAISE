import { DataState } from "@/components/research/DataState";
import { Badge } from "@/components/ui/Badge";
import { Card, CardHeader, StatTile } from "@/components/ui/Card";
import { LimitationsPanel } from "@/components/research/LimitationsPanel";
import { useDashboard } from "@/features/c3-aop-bcs/hooks/useDashboard";

export function EvidencePage() {
  const state = useDashboard();
  return <DataState state={state} render={(data) => <div className="space-y-6">
    <Card><CardHeader title="Research evidence & reproducibility" subtitle="The C3 backend validates and reads these versioned reports for every request." /><div className="grid grid-cols-2 gap-6 lg:grid-cols-4"><StatTile label="Source reports" value={data.provenance.sourceArtifacts.length} /><StatTile label="Generated figures" value={data.figures.length} /><StatTile label="Validation" value={data.provenance.validationStatus} /><StatTile label="Missing pilot scores" value={data.provenance.missingScores} /></div></Card>
    <Card><CardHeader title="Run provenance" subtitle="Frozen software-pilot identity." /><dl className="grid gap-4 md:grid-cols-2">{[["Run ID", data.provenance.runId], ["Run date", data.provenance.runDate], ["Dataset", data.provenance.datasetVersion], ["Predictor", data.provenance.predictorVersion], ["Code commit", data.provenance.codeCommit], ["Validation", data.provenance.validationStatus]].map(([label, value]) => <div key={label} className="rounded-lg border p-3" style={{ borderColor: "var(--color-border)" }}><dt className="text-xs font-semibold uppercase text-muted">{label}</dt><dd className="mt-1 break-all font-mono text-xs">{value}</dd></div>)}</dl></Card>
    <Card><CardHeader title="Tracked source reports" subtitle="Checksums are recalculated by the API before this table is returned." /><div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="text-xs uppercase text-muted"><tr><th className="py-2">Category</th><th>File</th><th>SHA-256</th><th>Status</th></tr></thead><tbody>{data.provenance.sourceArtifacts.map((artifact) => <tr key={artifact.label} className="border-t" style={{ borderColor: "var(--color-border)" }}><th className="py-3 font-medium">{artifact.label}</th><td className="max-w-lg break-all font-mono text-xs">{artifact.path}</td><td className="font-mono text-xs">{artifact.sha256.slice(0, 12)}…</td><td><Badge tone="success">present</Badge></td></tr>)}</tbody></table></div></Card>
    <LimitationsPanel title="Current limitations" items={["No real predictor has produced a retained score through the C3 interface.", "PU-AOP depends on a frozen Component 2 handoff.", "Current IR, FSR, BCS, PFR, and ΔScore values have no biological interpretation.", "The KernelSHAP backend and full faithfulness experiment remain later work."]} />
  </div>} />;
}
