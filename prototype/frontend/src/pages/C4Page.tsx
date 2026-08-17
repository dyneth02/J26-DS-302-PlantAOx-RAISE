import { useEffect, useState } from "react";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { motion } from "framer-motion";
import { c4Api } from "../api/client";
import PageHeader from "../components/PageHeader";
import Card from "../components/Card";
import Banner from "../components/Banner";
import StatCard from "../components/StatCard";
import {
  AD_TIER_COLORS,
  CHART_LEGEND_STYLE,
  FLAG_STYLES,
  tooltipContentStyle,
  tooltipItemStyle,
  tooltipLabelStyle,
} from "../components/chartTheme";

export default function C4Page() {
  const [summary, setSummary] = useState<any>(null);
  const [adSummary, setAdSummary] = useState<any>(null);
  const [parrs, setParrs] = useState<any>(null);
  const [pdss, setPdss] = useState<any>(null);
  const [arr, setArr] = useState<any>(null);
  const [cards, setCards] = useState<any[]>([]);

  useEffect(() => {
    c4Api.summary().then(setSummary);
    c4Api.adSummary().then(setAdSummary);
    c4Api.parrs().then(setParrs);
    c4Api.pdss().then(setPdss);
    c4Api.arr().then(setArr);
    c4Api.evidenceCards().then(setCards);
  }, []);

  const pieData = adSummary
    ? Object.entries(adSummary.tier_counts).map(([tier, count]) => ({ tier, count }))
    : [];

  return (
    <div>
      <PageHeader
        eyebrow="Component 4"
        title="PlantAOP-Screen"
        subtitle="Plant Digestome Screening with Applicability-Domain Abstention"
      />
      <div className="space-y-6 p-8">
        {summary && <Banner title={`Source: ${summary.source}`}>{summary.notes?.join(" ")}</Banner>}

        {summary && (
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatCard label="Source proteins" value={summary.n_source_proteins} />
            <StatCard label="Candidate fragments" value={summary.n_candidate_fragments} />
            <StatCard label="PARRS" value={parrs?.parrs ?? "…"} sub="AD-tier enrichment of top ranks" accent="teal" />
            <StatCard label="PDSS" value={pdss?.pdss ?? "…"} sub="distributional shift vs. AOP-BenchPos" accent="violet" />
          </div>
        )}

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          <Card title="Applicability-domain tiers" subtitle={`${adSummary?.n_candidates ?? "…"} candidate fragments`} eyebrow="Distribution">
            <ResponsiveContainer width="100%" height={260}>
              <PieChart>
                <Pie
                  data={pieData}
                  dataKey="count"
                  nameKey="tier"
                  outerRadius={90}
                  label={{ fill: "rgb(var(--c-ink-dim))", fontSize: 11, fontFamily: "IBM Plex Mono" }}
                  stroke="rgb(var(--c-void))"
                  strokeWidth={2}
                >
                  {pieData.map((d) => (
                    <Cell key={d.tier} fill={AD_TIER_COLORS[d.tier] ?? "rgb(var(--c-ink-faint))"} />
                  ))}
                </Pie>
                <Tooltip contentStyle={tooltipContentStyle()} labelStyle={tooltipLabelStyle()} itemStyle={tooltipItemStyle()} />
                <Legend wrapperStyle={CHART_LEGEND_STYLE} />
              </PieChart>
            </ResponsiveContainer>
          </Card>

          <Card title="Abstention-adjusted retrieval rate (ARR)" subtitle={arr?.definition} eyebrow="Confidence">
            <div className="flex h-[260px] flex-col items-center justify-center">
              <motion.p
                initial={{ opacity: 0, scale: 0.9 }}
                animate={{ opacity: 1, scale: 1 }}
                className="font-display text-6xl font-medium text-glow text-lime"
              >
                {arr?.arr ?? "…"}
              </motion.p>
              <p className="mt-3 max-w-xs text-center text-sm text-ink-dim">{arr?.interpretation}</p>
            </div>
          </Card>
        </div>

        <Card title="Evidence cards" subtitle="Top-ranked candidates, computed from real C1/C2/C3 outputs" eyebrow="Output">
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            {cards.map((card, i) => (
              <motion.div
                key={card.candidate_id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.06, duration: 0.4 }}
                className="rounded-xl border border-line bg-surface2/50 p-4 transition-colors hover:border-line-strong"
              >
                <div className="flex items-center justify-between">
                  <span className="font-data text-sm font-medium text-ink">{card.sequence}</span>
                  <span className={`rounded-full px-2 py-0.5 label-tag ${FLAG_STYLES[card.abstention_flag]}`}>
                    {card.abstention_flag}
                  </span>
                </div>
                <p className="mt-1.5 text-xs text-ink-faint">
                  {card.plant_species} · {card.source_protein.split("|")[1] ?? card.source_protein}
                </p>
                <div className="mt-3 grid grid-cols-2 gap-x-3 gap-y-1.5 font-data text-xs text-ink-dim">
                  <span>MW <span className="text-ink">{card.physicochemical_summary.molecular_weight}</span></span>
                  <span>GRAVY <span className="text-ink">{card.physicochemical_summary.gravy}</span></span>
                  <span>sim_C1 <span className="text-ink">{card.sim_c1}</span></span>
                  <span>prob_C2 <span className="text-ink">{card.prob_c2}</span></span>
                  <span>AD tier <span className="text-ink">{card.ad_tier}</span></span>
                  <span>score <span className="text-ink">{card.combined_score}</span></span>
                </div>
                <p className="mt-3 border-t border-line pt-2.5 text-xs italic leading-relaxed text-ink-faint">
                  {card.interpretation}
                </p>
              </motion.div>
            ))}
          </div>
        </Card>
      </div>
    </div>
  );
}
