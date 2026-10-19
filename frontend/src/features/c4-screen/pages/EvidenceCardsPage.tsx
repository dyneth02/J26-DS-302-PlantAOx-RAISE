import { useState } from "react";
import { useApi } from "@/lib/api/useApi";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader } from "@/components/ui/Card";
import { CandidateProvenance, DemoMarker, TierBadge } from "@/features/c4-screen/components/Provenance";
import { c4Api } from "@/features/c4-screen/services/api";
import type { Plant } from "@/features/c4-screen/types";

const plants: Plant[] = ["soybean", "rice", "rapeseed", "olive"];

export function EvidenceCardsPage() {
  const [plant, setPlant] = useState<Plant>("rice");
  const cards = useApi(() => c4Api.cards(plant, 50), [plant]);
  return (
    <div className="space-y-5">
      <Card>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div><CardHeader title="Evidence cards" subtitle="Top Tier 1/2 candidates for the selected plant. Tier 3 is only shown in Abstained." /></div>
          <div className="flex items-end gap-2">
            <label className="text-sm font-medium">Plant<select value={plant} onChange={(event) => setPlant(event.target.value as Plant)} className="ml-2 rounded border px-3 py-2" style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}>{plants.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
            <a href={c4Api.cardsExportHref(plant)} className="rounded-lg border px-3 py-2 text-sm font-semibold" style={{ borderColor: "var(--color-border)", color: "var(--color-primary)" }}>Export CSV</a>
          </div>
        </div>
        <CandidateProvenanceIntro />
      </Card>
      <DataState state={cards} render={(data) => (
        <>
          <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>Showing {data.cards.length} cards. Every card below is Tier 1 or Tier 2.</p>
          <div className="grid gap-4 xl:grid-cols-2">
            {data.cards.map((candidate) => <Card key={`${candidate.plant}-${candidate.peptide_id}`}>
              <div className="flex flex-wrap items-center justify-between gap-2">
                <TierBadge tier={candidate.tier} flag={candidate.flag} />
                <DemoMarker injected={candidate.injected_demo_case} />
              </div>
              <p className="mt-3 break-all font-mono text-lg font-bold">{candidate.sequence}</p>
              <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>{candidate.species} · {candidate.sequence.length} aa · rank {candidate.rank ?? "—"}</p>
              <div className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
                <Metric label="CS" value={candidate.CS.toFixed(3)} /><Metric label="d_AD" value={candidate.d_AD.toFixed(4)} />
                <Metric label="SIM_C1 · mock" value={candidate.SIM_C1?.toFixed(3) ?? "—"} /><Metric label="PROB_C2 · mock" value={candidate.PROB_C2?.toFixed(3) ?? "—"} />
              </div>
              <div className="mt-3 rounded-lg border p-3 text-sm" style={{ borderColor: "var(--color-warning-border)", background: "var(--color-warning-bg)", color: "var(--color-warning-text)" }}>
                BCS: {candidate.BCS?.toFixed(3) ?? "unavailable"} · {candidate.BCS_flag ?? "unclassified"} · C4-provisional. This is a mock reliability demonstration, not biological evidence.
              </div>
              <details className="mt-3">
                <summary className="cursor-pointer text-sm font-semibold">Provenance and descriptors</summary>
                <div className="mt-3 space-y-3"><CandidateProvenance candidate={candidate} />
                  <p className="text-xs">MW {candidate.physicochemical.molecular_weight.toFixed(2)} · pI {candidate.physicochemical.pI.toFixed(2)} · GRAVY {candidate.physicochemical.GRAVY.toFixed(3)} · charge pH 7 {candidate.physicochemical.net_charge_ph7.toFixed(3)}</p>
                  {candidate.provenance.map((source, index) => <p key={`${source.parent_accession}-${source.start}-${index}`} className="text-xs">{source.parent_accession} · {source.start}–{source.end} · {source.enzyme_path}</p>)}
                </div>
              </details>
            </Card>)}
          </div>
        </>
      )} />
    </div>
  );
}

function CandidateProvenanceIntro() {
  return <p className="mt-2 text-xs" style={{ color: "var(--color-text-muted)" }}>Signals and cloud are mock. No retrieval-performance metric is computed on these rows.</p>;
}

function Metric({ label, value }: { label: string; value: string }) {
  return <div><p className="text-xs" style={{ color: "var(--color-text-muted)" }}>{label}</p><p className="font-semibold">{value}</p></div>;
}
