import { useApi } from "@/lib/api/useApi";
import { c1Api } from "@/features/c1-procon/services/api";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader, StatTile } from "@/components/ui/Card";
import { LimitationsPanel } from "@/components/research/LimitationsPanel";
import { C1_COLORS, Callout, HBarChart, Legend } from "@/features/c1-procon/components/charts";
import type { BarItem } from "@/features/c1-procon/components/charts";
import { Bar, BarChart, CartesianGrid, Legend as ChartLegend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const TOOLTIP_STYLE = { background: "var(--color-surface)", borderColor: "var(--color-border)" };
const LABEL_COLOR: Record<string, string> = { FRS: C1_COLORS.frs, MC: C1_COLORS.mc, "FRS;MC": C1_COLORS.dual, GEN: C1_COLORS.gen };

export function DatasetPage() {
  const state = useApi(c1Api.dataset, []);

  return (
    <DataState
      state={state}
      render={(data) => {
        const labelItems: BarItem[] = data.label_counts.map((l) => ({
          label: l.label === "GEN" ? "GEN (mechanism not established)" : l.label === "FRS;MC" ? "FRS;MC (both mechanisms)" : l.label,
          value: l.count,
          color: LABEL_COLOR[l.label],
        }));
        const sourceItems: BarItem[] = data.source_by_class.flatMap((s) => [
          { label: `${s.source_group} - FRS-only`, value: s.frs_only, color: C1_COLORS.frs },
          { label: `${s.source_group} - MC-active`, value: s.mc_active, color: C1_COLORS.mc },
        ]);

        return (
          <div className="space-y-6">
            <Card>
              <CardHeader title="Step 1 - Leak-controlled multi-label benchmark" subtitle={`Fingerprint ${data.fingerprint}`} />
              <HBarChart items={labelItems} min={0} max={750} decimals={0} labelWidth={250} ariaLabel="Number of peptides per label" />
              <p className="mt-2 text-xs" style={{ color: "var(--color-text-muted)" }}>
                Split: {data.split_type}. One peptide can carry two labels (FRS;MC), so a dual-mechanism peptide counts for both classes.
              </p>
            </Card>

            <Card>
              <CardHeader title="Strict-evidence pool" subtitle="Peptides with per-peptide evidence; the pool the probe and retrieval use." />
              <div className="grid grid-cols-3 gap-6">
                <StatTile label="peptides" value={data.strict_pool.peptides} />
                <StatTile label="MC-active" value={data.strict_pool.mc_active} hint="MC-only plus FRS;MC" />
                <StatTile label="FRS-only" value={data.strict_pool.frs_only} />
              </div>
            </Card>

            <Card>
              <CardHeader title="Confound 1 - data source" subtitle="Every FRS-only peptide comes from one database, so the source alone separates the classes." />
              <HBarChart items={sourceItems} min={0} max={Math.max(...sourceItems.map((s) => s.value)) * 1.15} decimals={0} labelWidth={260} ariaLabel="Peptides per data source and class" />
              <Legend entries={[[C1_COLORS.frs, "FRS-only"], [C1_COLORS.mc, "MC-active"]]} />
              <div className="mt-4">
                <Callout title="Why it matters" tone="warn">
                  A model can score above chance simply by learning “which database did this peptide come from”. That is why data source is used as a baseline in the Probe and
                  Confounds pages.
                </Callout>
              </div>
            </Card>

            <Card>
              <CardHeader
                title="Confound 2 - length (tripeptide share)"
                subtitle={`Mean lengths are almost equal (${data.mean_length.mc_active.toFixed(2)} vs ${data.mean_length.frs_only.toFixed(2)} aa), but tripeptides are ${(data.tripeptide_share.frs_only * 100).toFixed(1)}% of FRS-only against ${(data.tripeptide_share.mc_active * 100).toFixed(1)}% of MC-active peptides.`}
              />
              <div style={{ width: "100%", height: 260 }}>
                <ResponsiveContainer>
                  <BarChart data={data.length_bins}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis dataKey="length_bin" stroke="var(--color-text-muted)" fontSize={12} label={{ value: "peptide length (amino acids)", position: "insideBottom", offset: -2, fontSize: 11 }} />
                    <YAxis stroke="var(--color-text-muted)" fontSize={12} />
                    <Tooltip contentStyle={TOOLTIP_STYLE} />
                    <ChartLegend />
                    <Bar dataKey="frs_only" name="FRS-only" fill={C1_COLORS.frs} radius={[4, 4, 0, 0]} />
                    <Bar dataKey="mc_active" name="MC-active" fill={C1_COLORS.mc} radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <LimitationsPanel title="How to read this benchmark" items={data.notes} />
          </div>
        );
      }}
    />
  );
}
