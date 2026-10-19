import { useApi } from "@/lib/api/useApi";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader, StatTile } from "@/components/ui/Card";
import { ProvenanceChips } from "@/features/c4-screen/components/Provenance";
import { c4Api } from "@/features/c4-screen/services/api";

export function OverviewPage() {
  const state = useApi(c4Api.meta, []);
  return (
    <DataState state={state} render={(meta) => (
      <div className="space-y-5">
        <Card>
          <CardHeader title="Plant proteome peptide screening" subtitle="Sequential in-silico digestion, ESM-2 applicability-domain tiers, and evidence-aware demonstration ranking." />
          <ProvenanceChips />
        </Card>
        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          <Card><StatTile label="Candidate embeddings" value={Number(meta.embedding_manifest_summary.n ?? 0).toLocaleString()} hint={`${meta.embedding_manifest_summary.dim ?? "?"} dimensions`} /></Card>
          <Card><StatTile label="Reference cloud size" value={meta.cloud.n.toLocaleString()} hint={`${meta.cloud.source} · ${meta.cloud.status}`} /></Card>
          <Card><StatTile label="Tier 1 threshold · t1" value={Number(meta.ad_params.t1).toPrecision(4)} hint="Frozen cloud calibration" /></Card>
          <Card><StatTile label="Tier 2 threshold · t2" value={Number(meta.ad_params.t2).toPrecision(4)} hint="Frozen cloud calibration" /></Card>
        </div>
        <Card>
          <CardHeader title="Data status" subtitle="Technical outputs, provisional choices, and mock inputs are distinguished explicitly." />
          <dl className="grid gap-4 sm:grid-cols-3">
            <div><dt className="font-semibold">Implemented</dt><dd className="mt-1 text-sm" style={{ color: "var(--color-text-muted)" }}>Reviewed proteome digestome candidates and ESM-2 vectors supplied by the Colab handoff.</dd></div>
            <div><dt className="font-semibold">C4-provisional</dt><dd className="mt-1 text-sm" style={{ color: "var(--color-text-muted)" }}>Applicability-domain calibration, BCS cutoffs, and the layer-33 mean-residue pooling assumption.</dd></div>
            <div><dt className="font-semibold">Mock</dt><dd className="mt-1 text-sm" style={{ color: "var(--color-text-muted)" }}>The current reference cloud and all C1/C2/C3 signals. Rankings are demonstrations, not biological evidence.</dd></div>
          </dl>
        </Card>
        <Card>
          <CardHeader title="Warnings and provenance" />
          <ul className="list-disc space-y-1 pl-5 text-sm">
            {meta.warnings.map((warning) => <li key={warning}>{warning}</li>)}
          </ul>
          <p className="mt-3 break-all text-xs" style={{ color: "var(--color-text-muted)" }}>Output manifest SHA-256: {meta.output_manifest_hash}</p>
          <p className="mt-1 text-xs" style={{ color: "var(--color-text-muted)" }}>Interface: {meta.spec_version ?? "provisional"} · Release: {meta.tag ?? "not tagged"}</p>
        </Card>
      </div>
    )} />
  );
}
