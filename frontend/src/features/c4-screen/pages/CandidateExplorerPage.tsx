import { useState } from "react";
import { useApi } from "@/lib/api/useApi";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader } from "@/components/ui/Card";
import { CandidateProvenance, DemoMarker, TierBadge } from "@/features/c4-screen/components/Provenance";
import { c4Api } from "@/features/c4-screen/services/api";
import type { CandidateQuery } from "@/features/c4-screen/services/api";
import type { Plant, Tier } from "@/features/c4-screen/types";

const plants: Plant[] = ["soybean", "rice", "rapeseed", "olive"];

export function CandidateExplorerPage() {
  const [plant, setPlant] = useState<Plant | "">("");
  const [tier, setTier] = useState<Tier | "">("");
  const [lenMin, setLenMin] = useState(3);
  const [lenMax, setLenMax] = useState(20);
  const [csMin, setCsMin] = useState(0);
  const [csMax, setCsMax] = useState(1);
  const [query, setQuery] = useState("");
  const [sort, setSort] = useState<CandidateQuery["sort"]>("rank");
  const [order, setOrder] = useState<CandidateQuery["order"]>("asc");
  const [page, setPage] = useState(1);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const pageSize = 25;
  const request: CandidateQuery = {
    plant: plant || undefined,
    tier: tier || undefined,
    len_min: lenMin,
    len_max: lenMax,
    cs_min: csMin,
    cs_max: csMax,
    q: query.trim() || undefined,
    sort,
    order,
    page,
    page_size: pageSize,
  };
  const results = useApi(() => c4Api.candidates(request), [plant, tier, lenMin, lenMax, csMin, csMax, query, sort, order, page]);
  const detail = useApi(() => selectedId ? c4Api.candidate(selectedId) : Promise.resolve(null), [selectedId]);

  return (
    <div className="space-y-5">
      <Card>
        <CardHeader title="Candidate explorer" subtitle="Search by sequence and narrow the ranked table by plant, tier, peptide length, or combined score." />
        <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <label className="text-xs font-medium">Sequence contains
            <input value={query} onChange={(event) => { setQuery(event.target.value); setPage(1); }} placeholder="e.g. YMVIR" className="mt-1 w-full rounded border px-3 py-2 text-sm" style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }} />
          </label>
          <label className="text-xs font-medium">Plant
            <select value={plant} onChange={(event) => { setPlant(event.target.value as Plant | ""); setPage(1); }} className="mt-1 w-full rounded border px-3 py-2 text-sm" style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}>
              <option value="">All plants</option>{plants.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
          <label className="text-xs font-medium">Tier
            <select value={tier} onChange={(event) => { setTier(event.target.value ? Number(event.target.value) as Tier : ""); setPage(1); }} className="mt-1 w-full rounded border px-3 py-2 text-sm" style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}>
              <option value="">All tiers</option><option value="1">Tier 1</option><option value="2">Tier 2</option><option value="3">Tier 3 · abstained</option>
            </select>
          </label>
          <div className="grid grid-cols-2 gap-2">
            <label className="text-xs font-medium">Length min<input type="number" min="3" max="20" value={lenMin} onChange={(event) => { setLenMin(Number(event.target.value)); setPage(1); }} className="mt-1 w-full rounded border px-2 py-2 text-sm" style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }} /></label>
            <label className="text-xs font-medium">Length max<input type="number" min="3" max="20" value={lenMax} onChange={(event) => { setLenMax(Number(event.target.value)); setPage(1); }} className="mt-1 w-full rounded border px-2 py-2 text-sm" style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }} /></label>
          </div>
          <label className="text-xs font-medium">Minimum CS ({csMin.toFixed(2)})<input type="range" min="0" max="1" step="0.01" value={csMin} onChange={(event) => { setCsMin(Math.min(Number(event.target.value), csMax)); setPage(1); }} className="mt-2 block w-full" /></label>
          <label className="text-xs font-medium">Maximum CS ({csMax.toFixed(2)})<input type="range" min="0" max="1" step="0.01" value={csMax} onChange={(event) => { setCsMax(Math.max(Number(event.target.value), csMin)); setPage(1); }} className="mt-2 block w-full" /></label>
          <label className="text-xs font-medium">Sort by
            <select value={sort} onChange={(event) => setSort(event.target.value as CandidateQuery["sort"])} className="mt-1 w-full rounded border px-3 py-2 text-sm" style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}>
              <option value="rank">Rank</option><option value="CS">Combined score</option><option value="sequence">Sequence</option><option value="length">Length</option><option value="tier">Tier</option><option value="d_AD">d_AD</option>
            </select>
          </label>
          <button type="button" onClick={() => setOrder((value) => value === "asc" ? "desc" : "asc")} className="self-end rounded border px-3 py-2 text-sm" style={{ borderColor: "var(--color-border)" }} aria-label={`Change sort order, currently ${order}`}>
            Order: {order === "asc" ? "Ascending" : "Descending"}
          </button>
        </div>
      </Card>
      <div className="grid gap-5 2xl:grid-cols-[minmax(0,1fr)_24rem]">
        <Card>
          <CardHeader title="Ranked candidates" />
          <DataState state={results} render={(data) => <>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[780px] text-left text-sm">
                <caption className="sr-only">Filtered candidate results</caption>
                <thead><tr className="border-b text-xs uppercase" style={{ borderColor: "var(--color-border)", color: "var(--color-text-muted)" }}><th className="p-2">Sequence</th><th className="p-2">Plant</th><th className="p-2">Tier</th><th className="p-2">Length</th><th className="p-2">d_AD</th><th className="p-2">CS</th><th className="p-2">Rank</th></tr></thead>
                <tbody>{data.items.map((row) => <tr key={`${row.plant}-${row.peptide_id}`} className="border-b" style={{ borderColor: "var(--color-border)" }}>
                  <td className="p-2"><button type="button" className="font-mono font-semibold underline decoration-dotted underline-offset-2" onClick={() => setSelectedId(row.peptide_id)}>{row.sequence}</button></td>
                  <td className="p-2 capitalize">{row.plant}</td><td className="p-2"><TierBadge tier={row.tier} /></td><td className="p-2">{row.length}</td><td className="p-2">{row.d_AD.toFixed(4)}</td><td className="p-2">{row.CS.toFixed(4)}</td><td className="p-2">{row.rank ?? "—"}</td>
                </tr>)}</tbody>
              </table>
            </div>
            <div className="mt-4 flex items-center justify-between gap-3 text-sm">
              <span>{data.total.toLocaleString()} results · page {data.page}</span>
              <div className="flex gap-2"><button type="button" disabled={page <= 1} onClick={() => setPage((value) => value - 1)} className="rounded border px-3 py-1.5 disabled:opacity-50" style={{ borderColor: "var(--color-border)" }}>Previous</button><button type="button" disabled={page * pageSize >= data.total} onClick={() => setPage((value) => value + 1)} className="rounded border px-3 py-1.5 disabled:opacity-50" style={{ borderColor: "var(--color-border)" }}>Next</button></div>
            </div>
          </>} />
        </Card>
        {selectedId && <Card className="h-fit">
          <div className="flex items-start justify-between gap-2"><CardHeader title="Evidence card" subtitle={`ID ${selectedId}`} /><button type="button" onClick={() => setSelectedId(null)} aria-label="Close evidence card" className="rounded border px-2 py-1 text-sm" style={{ borderColor: "var(--color-border)" }}>Close</button></div>
          <DataState state={detail} render={(candidate) => candidate ? <div className="space-y-4">
            <div className="flex flex-wrap items-center gap-2"><TierBadge tier={candidate.tier} /><DemoMarker injected={candidate.injected_demo_case} /></div>
            <p className="break-all font-mono text-lg font-semibold">{candidate.sequence}</p><p className="text-sm">{candidate.species} · CS {candidate.CS.toFixed(4)} · d_AD {candidate.d_AD.toFixed(4)}</p>
            <dl className="grid grid-cols-2 gap-2 text-xs">{Object.entries(candidate.physicochemical).map(([name, value]) => <div key={name}><dt className="capitalize" style={{ color: "var(--color-text-muted)" }}>{name.replaceAll("_", " ")}</dt><dd>{value.toFixed(3)}</dd></div>)}</dl>
            <CandidateProvenance candidate={candidate} />
            <div className="space-y-2 text-xs">{candidate.provenance.map((item, index) => <p key={`${item.parent_accession}-${item.start}-${index}`}>{item.parent_accession} · {item.start}–{item.end} · {item.enzyme_path}</p>)}</div>
          </div> : <p>No evidence card available.</p>} />
        </Card>}
      </div>
    </div>
  );
}
