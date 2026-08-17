import { useEffect, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, Cell } from "recharts";
import { c2Api } from "../api/client";
import PageHeader from "../components/PageHeader";
import Card from "../components/Card";
import Banner from "../components/Banner";
import StatCard from "../components/StatCard";
import { CHART_GRID, CHART_TICK, tooltipContentStyle, tooltipItemStyle, tooltipLabelStyle } from "../components/chartTheme";

export default function C2Page() {
  const [summary, setSummary] = useState<any>(null);
  const [pools, setPools] = useState<any>(null);
  const [rnis, setRnis] = useState<any>(null);
  const [calibration, setCalibration] = useState<any>(null);
  const [stageComparison, setStageComparison] = useState<any>(null);

  useEffect(() => {
    c2Api.summary().then(setSummary);
    c2Api.pools().then(setPools);
    c2Api.rnis().then(setRnis);
    c2Api.calibration().then(setCalibration);
    c2Api.stageComparison().then(setStageComparison);
  }, []);

  const chartData = stageComparison?.series ?? [];

  return (
    <div>
      <PageHeader
        eyebrow="Component 2"
        title="PU-AOP"
        subtitle="Evidence-Tiered PU Learning and Random-Negative Inflation Scoring (RNIS)"
      />
      <div className="space-y-6 p-8">
        {summary && <Banner title="Real positives, real hard negatives, synthetic easy negatives">{summary.notes?.join(" ")}</Banner>}

        {rnis && (
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatCard label="MCC — easy negatives" value={rnis.mcc_c1_easy} accent="teal" />
            <StatCard label="MCC — hard negatives" value={rnis.mcc_c3_hard} accent="amber" />
            <StatCard label="RNIS" value={rnis.rnis} sub="MCC_easy − MCC_hard" />
            <StatCard label="Classifier" value="Logistic Regression" sub="14 descriptor features" />
          </div>
        )}

        <Card title="Performance vs. negative-pool difficulty" subtitle={rnis?.interpretation} eyebrow="Inflation check">
          <ResponsiveContainer width="100%" height={280}>
            <BarChart data={chartData} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
              <CartesianGrid stroke={CHART_GRID} vertical={false} />
              <XAxis dataKey="stage" tick={CHART_TICK} axisLine={{ stroke: CHART_GRID }} tickLine={false} />
              <YAxis domain={[0, 1]} tick={CHART_TICK} axisLine={{ stroke: CHART_GRID }} tickLine={false} />
              <Tooltip
                contentStyle={tooltipContentStyle()}
                labelStyle={tooltipLabelStyle()}
                itemStyle={tooltipItemStyle()}
                cursor={{ fill: "rgb(var(--c-ink) / 0.04)" }}
              />
              <Bar dataKey="mcc" radius={[6, 6, 0, 0]}>
                {chartData.map((_: any, i: number) => (
                  <Cell key={i} fill={i === 0 ? "rgb(var(--c-teal))" : "rgb(var(--c-coral))"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Challenge pools" eyebrow="Negative sampling">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-ink-faint">
                  <th className="py-2 pr-4 label-tag font-normal">Pool</th>
                  <th className="py-2 pr-4 label-tag font-normal">Size</th>
                  <th className="py-2 pr-4 label-tag font-normal">Source</th>
                  <th className="py-2 label-tag font-normal">Purpose</th>
                </tr>
              </thead>
              <tbody>
                {pools &&
                  Object.entries(pools).map(([key, p]: [string, any]) => (
                    <tr key={key} className="border-b border-line last:border-0">
                      <td className="py-2.5 pr-4 font-data text-xs text-teal">{key}</td>
                      <td className="py-2.5 pr-4 font-data text-ink">{p.size}</td>
                      <td className="py-2.5 pr-4 text-ink-dim">{p.source}</td>
                      <td className="py-2.5 text-ink-dim">{p.purpose}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        </Card>

        <Card title="Calibration" subtitle="Expected calibration error (ECE) and Brier score, per pool" eyebrow="Confidence">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-line text-left text-ink-faint">
                <th className="py-2 pr-4 label-tag font-normal">Pool</th>
                <th className="py-2 pr-4 label-tag font-normal">ECE</th>
                <th className="py-2 label-tag font-normal">Brier score</th>
              </tr>
            </thead>
            <tbody>
              {calibration &&
                Object.entries(calibration).map(([key, c]: [string, any]) => (
                  <tr key={key} className="border-b border-line last:border-0">
                    <td className="py-2.5 pr-4 text-ink">{key}</td>
                    <td className="py-2.5 pr-4 font-data text-ink-dim">{c.ece}</td>
                    <td className="py-2.5 font-data text-ink-dim">{c.brier}</td>
                  </tr>
                ))}
            </tbody>
          </table>
        </Card>
      </div>
    </div>
  );
}
