import { useApi } from "@/lib/api/useApi";
import { c2Api } from "@/features/c2-pu/services/api";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader, StatTile } from "@/components/ui/Card";
import { LimitationsPanel } from "@/components/research/LimitationsPanel";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";

export function So1Page() {
  const state = useApi(c2Api.fr1Summary, []);

  return (
    <DataState
      state={state}
      render={(fr1) => {
        const foldData = Object.entries(fr1.fold_sizes)
          .sort(([a], [b]) => Number(a) - Number(b))
          .map(([fold, size]) => ({ fold: `Fold ${fold}`, size }));

        return (
          <div className="space-y-6">
            <Card>
              <CardHeader
                title="SO1 - Evidence-Tiered Positive-Pool Curation"
                subtitle={`Frozen as ${fr1.version_id}`}
              />
              <div className="grid grid-cols-2 gap-6 sm:grid-cols-4">
                <StatTile label="Accepted positives" value={fr1.positive_pool_provisional} />
                <StatTile label="E1 (confirmed)" value={fr1.evidence_tiers.e1} />
                <StatTile label="E2 (provisional)" value={fr1.evidence_tiers.e2} hint="Not assay-confirmed" />
                <StatTile label="Cross-source conflicts excluded" value={fr1.cross_source_conflicts_excluded} />
                <StatTile label="CD-HIT clusters (90% identity)" value={fr1.cdhit_clusters} />
                <StatTile label="GraphPart retained" value={fr1.graphpart_retained} />
                <StatTile label="Excluded for cross-fold homology" value={fr1.graphpart_excluded_for_homology} />
              </div>
            </Card>

            <Card>
              <CardHeader title="GraphPart 5-fold distribution" subtitle="Homology-controlled at 40% identity" />
              <div style={{ width: "100%", height: 260 }}>
                <ResponsiveContainer>
                  <BarChart data={foldData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis dataKey="fold" stroke="var(--color-text-muted)" fontSize={12} />
                    <YAxis stroke="var(--color-text-muted)" fontSize={12} />
                    <Tooltip
                      contentStyle={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }}
                    />
                    <Bar dataKey="size" fill="var(--color-primary)" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <LimitationsPanel items={fr1.known_limitations} />
            <LimitationsPanel title="Pending supervisor approvals" items={fr1.pending_supervisor_approvals} />
          </div>
        );
      }}
    />
  );
}
