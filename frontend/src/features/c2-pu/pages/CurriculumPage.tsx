import { useApi } from "@/lib/api/useApi";
import { c2Api } from "@/features/c2-pu/services/api";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader, StatTile } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { LimitationsPanel } from "@/components/research/LimitationsPanel";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";

export function CurriculumPage() {
  const state = useApi(c2Api.curriculum, []);

  return (
    <DataState
      state={state}
      render={(curriculum) => {
        const chartData = curriculum.stages.map((s) => ({
          stage: s.training_pool,
          "Positive recovery": s.positive_recovery,
          "External MCC": s.external_mcc,
          "External AUROC": s.external_auroc,
        }));

        return (
          <div className="space-y-6">
            <Card>
              <CardHeader
                title="Evidence-weighted curriculum: C1 → C2 → C3"
                subtitle={`Fold ${curriculum.fold_id}. Corrective nnPU, prior π=${curriculum.prior}, evidence weights E1=${curriculum.evidence_weights.E1}, E2=${curriculum.evidence_weights.E2}.`}
              />
              <div className="flex items-center gap-3">
                {curriculum.stage_order.map((stage, i) => (
                  <div key={stage} className="flex items-center gap-3">
                    <Badge tone="accent">{stage}</Badge>
                    {i < curriculum.stage_order.length - 1 && <span style={{ color: "var(--color-text-muted)" }}>→</span>}
                  </div>
                ))}
              </div>
            </Card>

            <Card>
              <CardHeader
                title="Positive recovery vs. external-control discrimination, by stage"
                subtitle="Checkpoint selection at every stage uses a C1-based surrogate risk. Read the trend, not a controlled ablation."
              />
              <div style={{ width: "100%", height: 280 }}>
                <ResponsiveContainer>
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis dataKey="stage" stroke="var(--color-text-muted)" fontSize={12} />
                    <YAxis stroke="var(--color-text-muted)" fontSize={12} />
                    <Tooltip contentStyle={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }} />
                    <Legend />
                    <Line type="monotone" dataKey="Positive recovery" stroke="var(--color-primary)" strokeWidth={2} />
                    <Line type="monotone" dataKey="External MCC" stroke="var(--color-danger-text)" strokeWidth={2} />
                    <Line type="monotone" dataKey="External AUROC" stroke="var(--color-accent)" strokeWidth={2} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card className="overflow-x-auto">
              <CardHeader title="Per-stage metrics" />
              <table className="w-full min-w-[700px] text-left text-sm">
                <thead>
                  <tr style={{ color: "var(--color-text-muted)" }}>
                    <th className="pb-2">Stage</th>
                    <th className="pb-2">Validation nnPU risk</th>
                    <th className="pb-2">Positive recovery</th>
                    <th className="pb-2">C1 frac &gt; 0.5</th>
                    <th className="pb-2">C2 frac &gt; 0.5</th>
                    <th className="pb-2">C3 frac &gt; 0.5</th>
                    <th className="pb-2">External MCC</th>
                    <th className="pb-2">External AUROC</th>
                  </tr>
                </thead>
                <tbody>
                  {curriculum.stages.map((s) => (
                    <tr key={s.condition} className="border-t" style={{ borderColor: "var(--color-border)" }}>
                      <td className="py-1.5 font-medium">{s.training_pool}</td>
                      <td className="py-1.5">{s.best_validation_weighted_nnpu_risk.toFixed(4)}</td>
                      <td className="py-1.5">{s.positive_recovery.toFixed(3)}</td>
                      <td className="py-1.5">{s.c1_fraction_gt_0_5.toFixed(3)}</td>
                      <td className="py-1.5">{s.c2_fraction_gt_0_5.toFixed(3)}</td>
                      <td className="py-1.5">{s.c3_fraction_gt_0_5.toFixed(3)}</td>
                      <td className="py-1.5">
                        <Badge tone={s.external_mcc < 0 ? "danger" : "success"}>{s.external_mcc.toFixed(3)}</Badge>
                      </td>
                      <td className="py-1.5">
                        <Badge tone={s.external_auroc < 0.5 ? "danger" : "success"}>{s.external_auroc.toFixed(3)}</Badge>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>

            <div className="grid gap-4 sm:grid-cols-3">
              {curriculum.stages.map((s) => (
                <Card key={s.condition}>
                  <StatTile
                    label={`${s.training_pool} external recall`}
                    value={s.external_recall.toFixed(3)}
                    hint="Held-out positives vs. external assay-inactive controls"
                  />
                </Card>
              ))}
            </div>

            <LimitationsPanel items={curriculum.limitations} />
          </div>
        );
      }}
    />
  );
}
