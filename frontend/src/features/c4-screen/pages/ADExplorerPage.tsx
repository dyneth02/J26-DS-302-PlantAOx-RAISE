import { useState } from "react";
import { useApi } from "@/lib/api/useApi";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader } from "@/components/ui/Card";
import { ADHistogram, LengthComparison, TierStackedBars } from "@/features/c4-screen/components/Charts";
import { ProvenanceChips } from "@/features/c4-screen/components/Provenance";
import { c4Api } from "@/features/c4-screen/services/api";
import type { Plant } from "@/features/c4-screen/types";

const plants: Plant[] = ["soybean", "rice", "rapeseed", "olive"];

export function ADExplorerPage() {
  const [plant, setPlant] = useState<Plant>("rice");
  const [showSensitivity, setShowSensitivity] = useState(false);
  const tiers = useApi(() => c4Api.tierSummary(plant), [plant]);
  const histogram = useApi(() => c4Api.adHistogram(plant), [plant]);
  const lengths = useApi(c4Api.lengths, []);

  return (
    <div className="space-y-5">
      <Card>
        <div className="flex flex-wrap items-end justify-between gap-4">
          <div><CardHeader title="Applicability-domain explorer" subtitle="Production tiers use the frozen reference-cloud calibration; no threshold tuning is performed here." /><ProvenanceChips /></div>
          <label className="text-sm font-medium">Plant
            <select className="ml-2 rounded border px-3 py-2" style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }} value={plant} onChange={(event) => setPlant(event.target.value as Plant)}>
              {plants.map((item) => <option key={item} value={item}>{item}</option>)}
            </select>
          </label>
        </div>
      </Card>
      <div className="grid gap-5 xl:grid-cols-2">
        <Card><CardHeader title="d_AD histogram" subtitle="Leave-one-out cloud distances versus candidate distances; dashed lines show t1/t2." /><DataState state={histogram} render={(data) => <ADHistogram data={data} />} /></Card>
        <Card><CardHeader title="Tier fractions by length bin" subtitle="3–10 and 11–20 amino-acid groups." /><DataState state={tiers} render={(data) => <TierStackedBars rows={data.by_length_bin} plants={[plant]} />} /></Card>
      </div>
      <Card><CardHeader title="Tier fractions for selected plant" /><DataState state={tiers} render={(data) => <TierStackedBars rows={data.overall} plants={[plant]} />} /></Card>
      <Card><CardHeader title="Candidate versus cloud lengths" subtitle="Bars are normalized within each source; counts are available from the API." /><DataState state={lengths} render={(data) => <LengthComparison rows={data.distributions} />} /></Card>
      <Card>
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div><CardHeader title="Mean-centering sensitivity" subtitle="Sensitivity only; it does not replace production tiers or alter frozen thresholds." /></div>
          <button type="button" aria-expanded={showSensitivity} onClick={() => setShowSensitivity((value) => !value)} className="rounded-lg border px-3 py-2 text-sm font-medium" style={{ borderColor: "var(--color-border)" }}>
            {showSensitivity ? "Hide sensitivity" : "Show sensitivity"}
          </button>
        </div>
        {showSensitivity && <DataState state={tiers} render={(data) => (
          <div className="overflow-x-auto">
            <p className="mb-3 text-sm font-semibold">Sensitivity, not production · source: {data.mean_centering_sensitivity?.[0]?.reference_source ?? "not recorded"}</p>
            <table className="w-full min-w-[600px] text-left text-sm">
              <thead><tr className="border-b text-xs uppercase" style={{ borderColor: "var(--color-border)" }}><th className="p-2">Group</th><th className="p-2">Length bin</th><th className="p-2">Tier</th><th className="p-2">Baseline</th><th className="p-2">Mean-centered</th><th className="p-2">Δ</th></tr></thead>
              <tbody>{(data.mean_centering_sensitivity ?? []).filter((row) => row.group === plant).map((row) => <tr key={`${row.group}-${row.length_bin}-${row.tier}`} className="border-b" style={{ borderColor: "var(--color-border)" }}>
                <td className="p-2 capitalize">{row.group}</td><td className="p-2">{row.length_bin}</td><td className="p-2">Tier {row.tier}</td><td className="p-2">{((row.baseline_fraction ?? 0) * 100).toFixed(2)}%</td><td className="p-2">{((row.mean_centered_fraction ?? 0) * 100).toFixed(2)}%</td><td className="p-2">{((row.fraction_delta ?? 0) * 100).toFixed(2)} pp</td>
              </tr>)}</tbody>
            </table>
          </div>
        )} />}
      </Card>
    </div>
  );
}
