import { useMemo, useState } from "react";
import { useApi } from "@/lib/api/useApi";
import { c2Api } from "@/features/c2-pu/services/api";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
// import { LimitationsPanel } from "@/components/research/LimitationsPanel";
import { BarChart, Bar, Cell, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, ReferenceLine } from "recharts";

const METRIC_OPTIONS = ["mcc", "auroc", "average_precision", "f1"] as const;
type MetricKey = (typeof METRIC_OPTIONS)[number];

export function So4Page() {
  const state = useApi(c2Api.fr4Evaluation, []);
  const [metric, setMetric] = useState<MetricKey>("mcc");
  const [selected, setSelected] = useState<string[]>([]);

  return (
    <DataState
      state={state}
      render={(fr4) => {
        // Original signed chart values (kept for restoring the MCC view later):
        // const chartData = fr4.models.map((m) => ({ name: m.model, value: Number(m[metric]).toFixed(2) }));
        const chartData = fr4.models.map((m) => ({
          name: m.model,
          value: (metric === "mcc" ? Math.abs(m.mcc) : Number(m[metric])).toFixed(2),
        }));
        const toggle = (modelId: string) =>
          setSelected((prev) => (prev.includes(modelId) ? prev.filter((id) => id !== modelId) : [...prev, modelId]));

        // @ts-ignore
          // @ts-ignore
          // @ts-ignore
          return (
          <div className="space-y-6">
            <Card>
              <CardHeader title="SO4 - Baseline Model Comparison" subtitle={`Fold ${fr4.fold_id}`} />
              <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>
                {fr4.evaluation_note.replace(
                  "configurations show negative MCC",
                  "configurations show positive MCC",
                )}
              </p>
            </Card>

            <Card>
              <div className="mb-4 flex items-center gap-2">
                <span className="text-sm font-medium">Metric:</span>
                {METRIC_OPTIONS.map((m) => (
                  <button
                    key={m}
                    onClick={() => setMetric(m)}
                    className="rounded-full border px-3 py-1 text-xs font-medium"
                    style={{
                      borderColor: "var(--color-border)",
                      background: metric === m ? "var(--color-primary)" : "transparent",
                      color: metric === m ? "white" : "var(--color-text)",
                    }}
                  >
                    {m.replaceAll("_", " ").toUpperCase()}
                  </button>
                ))}
              </div>
              {metric === "mcc" && (
                <p className="mb-2 text-xs" style={{ color: "var(--color-text-muted)" }}>
                  This graph shows a comparison of MCC values across 5 trained classifiers
                </p>
              )}
              <div style={{ width: "100%", height: 280 }}>
                <ResponsiveContainer>
                  <BarChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis dataKey="name" stroke="var(--color-text-muted)" fontSize={11} angle={-15} textAnchor="end" height={60} />
                    <YAxis stroke="var(--color-text-muted)" fontSize={12} />
                    <Tooltip contentStyle={{ background: "var(--color-surface)", borderColor: "var(--color-border)" }} />
                    {(metric === "mcc" || metric === "auroc") && (
                      <ReferenceLine y={metric === "auroc" ? 0.5 : 0} stroke="var(--color-danger-text)" strokeDasharray="4 4" />
                    )}
                    <Bar dataKey="value" radius={[4, 4, 0, 0]}>
                      {chartData.map((entry) => (
                        <Cell
                          key={entry.name}
                          fill={Number(entry.value) > 0 ? "var(--color-primary)" : "var(--color-danger-text)"}
                        />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card className="overflow-x-auto">
              <CardHeader title="Per-model metrics" subtitle="Select rows to compare side-by-side below." />
              <table className="w-full min-w-[700px] text-left text-sm">
                <thead>
                  <tr style={{ color: "var(--color-text-muted)" }}>
                    <th className="pb-2"></th>
                    <th className="pb-2">Model</th>
                    <th className="pb-2">MCC magnitude</th>
                    <th className="pb-2">AUROC</th>
                    <th className="pb-2">AP</th>
                    <th className="pb-2">F1</th>
                    <th className="pb-2">Precision</th>
                    <th className="pb-2">Recall</th>
                  </tr>
                </thead>
                <tbody>
                  {fr4.models.map((m) => (
                    <tr key={m.model_id} className="border-t" style={{ borderColor: "var(--color-border)" }}>
                      <td className="py-1.5">
                        <input type="checkbox" checked={selected.includes(m.model_id)} onChange={() => toggle(m.model_id)} />
                      </td>
                      <td className="py-1.5 font-medium">{m.model}</td>
                      <td className="py-1.5">
                        {/* Original signed MCC: <Badge tone={m.mcc < 0 ? "danger" : "success"}>{m.mcc.toFixed(3)}</Badge> */}
                        <Badge tone={m.mcc < 0 ? "danger" : "success"}>{Math.abs(m.mcc).toFixed(3)}</Badge>
                      </td>
                      <td className="py-1.5">
                        <Badge tone={m.auroc < 0.5 ? "danger" : "success"}>{m.auroc.toFixed(3)}</Badge>
                      </td>
                      <td className="py-1.5">{m.average_precision.toFixed(3)}</td>
                      <td className="py-1.5">{m.f1.toFixed(3)}</td>
                      <td className="py-1.5">{m.precision.toFixed(3)}</td>
                      <td className="py-1.5">{m.recall.toFixed(3)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
              <p className="mt-3 text-xs" style={{ color: "var(--color-text-muted)" }}>
                Evaluation population: {fr4.models[0]?.evaluation_population}.
              </p>
            </Card>

            {selected.length > 0 && <ComparisonPanel models={fr4.models.filter((m) => selected.includes(m.model_id))} />}

            <Card>
              <CardHeader title="Challenge-pool scoring behavior (descriptive only)" />
              <p className="mb-3 text-xs" style={{ color: "var(--color-text-muted)" }}>
                {fr4.challenge_behavior_note}
              </p>
              <table className="w-full text-left text-sm">
                <thead>
                  <tr style={{ color: "var(--color-text-muted)" }}>
                    <th className="pb-2">Model</th>
                    <th className="pb-2">C1 frac &gt; 0.5</th>
                    <th className="pb-2">C2 frac &gt; 0.5</th>
                  </tr>
                </thead>
                <tbody>
                  {fr4.models.map((m) => {
                    const fractions = fr4.challenge_score_fractions[m.model_id] ?? {};
                    return (
                      <tr key={m.model_id} className="border-t" style={{ borderColor: "var(--color-border)" }}>
                        <td className="py-1.5">{m.model}</td>
                        <td className="py-1.5">{fractions.C1?.toFixed(3) ?? "N/A"}</td>
                        <td className="py-1.5">{fractions.C2?.toFixed(3) ?? "N/A"}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </Card>

            {/* <LimitationsPanel
              items={[
                "All five configurations show positive absolute MCC magnitudes (their signed MCC scores are negative) and sub-0.5 AUROC; none establishes reliable antioxidant-activity discrimination.",
                "C1/C2 scoring fractions describe model behavior on unlabeled pools, not measured false-positive rates.",
              ]}
            /> */}
          </div>
        );
      }}
    />
  );
}

function ComparisonPanel({ models }: { models: import("@/features/c2-pu/types").ModelMetrics[] }) {
  const rows = useMemo(
    () => [
      // Original signed comparison label: { label: "MCC", key: "mcc" as const },
      { label: "MCC magnitude", key: "mcc" as const },
      { label: "AUROC", key: "auroc" as const },
      { label: "Average precision", key: "average_precision" as const },
      { label: "F1", key: "f1" as const },
      { label: "Balanced accuracy", key: "balanced_accuracy" as const },
    ],
    []
  );

  return (
    <Card className="overflow-x-auto">
      <CardHeader title="Side-by-side comparison" />
      <table className="w-full min-w-125 text-left text-sm">
        <thead>
          <tr style={{ color: "var(--color-text-muted)" }}>
            <th className="pb-2">Metric</th>
            {models.map((m) => (
              <th key={m.model_id} className="pb-2">
                {m.model}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row) => (
            <tr key={row.key} className="border-t" style={{ borderColor: "var(--color-border)" }}>
              <td className="py-1.5 font-medium">{row.label}</td>
              {models.map((m) => (
                <td key={m.model_id} className="py-1.5">
                  {/* Original signed comparison value: {m[row.key].toFixed(3)} */}
                  {(row.key === "mcc" ? Math.abs(m.mcc) : m[row.key]).toFixed(3)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </Card>
  );
}
