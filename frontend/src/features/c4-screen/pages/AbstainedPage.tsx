import { useState } from "react";
import { useApi } from "@/lib/api/useApi";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader } from "@/components/ui/Card";
import { DemoMarker, TierBadge } from "@/features/c4-screen/components/Provenance";
import { c4Api } from "@/features/c4-screen/services/api";
import type { Plant } from "@/features/c4-screen/types";

const plants: Plant[] = ["soybean", "rice", "rapeseed", "olive"];
const pageSize = 25;

export function AbstainedPage() {
  const [plant, setPlant] = useState<Plant>("rice");
  const [page, setPage] = useState(1);
  const state = useApi(() => c4Api.abstained(plant, page, pageSize), [plant, page]);
  return (
    <Card>
      <div className="flex flex-wrap items-end justify-between gap-4"><div><CardHeader title="Abstained candidates" subtitle="Tier 3 is excluded from ranking and shown separately with CS = 0." /></div>
        <label className="text-sm font-medium">Plant<select value={plant} onChange={(event) => { setPlant(event.target.value as Plant); setPage(1); }} className="ml-2 rounded border px-3 py-2" style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}>{plants.map((item) => <option key={item} value={item}>{item}</option>)}</select></label>
      </div>
      <DataState state={state} render={(data) => <>
        <p className="mb-3 text-sm">{data.total.toLocaleString()} Tier 3 rows for {plant}.</p>
        <div className="overflow-x-auto"><table className="w-full min-w-[680px] text-left text-sm">
          <caption className="sr-only">Tier 3 candidates abstained from ranking</caption>
          <thead><tr className="border-b text-xs uppercase" style={{ borderColor: "var(--color-border)" }}><th className="p-2">Sequence</th><th className="p-2">Tier / flag</th><th className="p-2">CS</th><th className="p-2">d_AD</th><th className="p-2">Demo marker</th></tr></thead>
          <tbody>{data.items.map((item) => <tr key={item.peptide_id} className="border-b" style={{ borderColor: "var(--color-border)" }}><td className="p-2 font-mono">{item.sequence}</td><td className="p-2"><TierBadge tier={3} flag="RED" /></td><td className="p-2">0</td><td className="p-2">{item.d_AD.toFixed(4)}</td><td className="p-2"><DemoMarker injected={item.injected_demo_case} /></td></tr>)}</tbody>
        </table></div>
        <div className="mt-4 flex items-center justify-between text-sm"><span>Page {page}</span><div className="flex gap-2"><button type="button" disabled={page <= 1} onClick={() => setPage((value) => value - 1)} className="rounded border px-3 py-1.5 disabled:opacity-50" style={{ borderColor: "var(--color-border)" }}>Previous</button><button type="button" disabled={page * pageSize >= data.total} onClick={() => setPage((value) => value + 1)} className="rounded border px-3 py-1.5 disabled:opacity-50" style={{ borderColor: "var(--color-border)" }}>Next</button></div></div>
      </>} />
    </Card>
  );
}
