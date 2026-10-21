import { DataState } from "@/components/research/DataState";
import { Card, CardHeader, StatTile } from "@/components/ui/Card";
import { useDashboard } from "@/features/c3-aop-bcs/hooks/useDashboard";

export function DatasetPage() {
  const state = useDashboard();

  return (
    <DataState
      state={state}
      render={(data) => {
        const maximum = data.datasetFunnel[0]?.count || 1;
        return (
          <div className="space-y-6">
            <Card>
              <CardHeader title="Audit-dataset preparation" subtitle="Versioned counts from cleaning, CD-HIT, eligibility, and pilot reports." />
              <div className="space-y-4">
                {data.datasetFunnel.map((stage) => (
                  <div key={stage.label} className="grid items-center gap-3 sm:grid-cols-[13rem_1fr_5rem]">
                    <div><p className="text-sm font-semibold">{stage.label}</p><p className="text-xs text-muted">{stage.detail}</p></div>
                    <div className="h-2 overflow-hidden rounded-full bg-border"><div className="h-full rounded-full" style={{ width: `${Math.max(4, stage.count / maximum * 100)}%`, background: "var(--color-primary)" }} /></div>
                    <strong className="text-right text-sm">{stage.count.toLocaleString()}</strong>
                  </div>
                ))}
              </div>
            </Card>

            <div className="grid gap-4 md:grid-cols-2">
              <Card><CardHeader title="Pilot coverage" subtitle="Coverage-first selection using fixed seed 42." /><dl className="grid grid-cols-2 gap-5"><StatTile label="Length range" value={data.coverage.lengthRange} /><StatTile label="Distinct lengths" value={data.coverage.distinctLengths} /><StatTile label="Redox residues" value={data.coverage.redoxResidues.join(" · ")} /><StatTile label="Evidence tiers" value={data.coverage.evidenceTiers.join(" and ")} /></dl></Card>
              <Card><CardHeader title="Count quality control" subtitle="No subject exceeds the prespecified 20% dominance flag." /><div className="grid grid-cols-2 gap-6"><StatTile label="Maximum subject share" value={`${(data.coverage.maximumVariantShare * 100).toFixed(1)}%`} hint="below 20%" /><StatTile label="Missing scores" value={data.provenance.missingScores} hint="pilot rows" /></div></Card>
            </div>

            <Card>
              <CardHeader title="Dataset stages" subtitle="Traceable preparation summary." />
              <div className="overflow-x-auto"><table className="w-full text-left text-sm"><thead className="text-xs uppercase text-muted"><tr><th className="py-2">Stage</th><th>Records</th><th>Rule/output</th></tr></thead><tbody>{data.datasetFunnel.map((stage, index) => <tr key={stage.label} className="border-t" style={{ borderColor: "var(--color-border)" }}><th className="py-3 font-medium">{index + 1}. {stage.label}</th><td>{stage.count.toLocaleString()}</td><td className="text-muted">{stage.detail}</td></tr>)}</tbody></table></div>
            </Card>
          </div>
        );
      }}
    />
  );
}
