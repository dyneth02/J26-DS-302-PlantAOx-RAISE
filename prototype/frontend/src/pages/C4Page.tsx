import { useEffect, useMemo, useState } from "react";
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer, Legend } from "recharts";
import { AnimatePresence, motion } from "framer-motion";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { c4Api } from "../api/client";
import PageHeader from "../components/PageHeader";
import Card from "../components/Card";
import Banner from "../components/Banner";
import StatCard from "../components/StatCard";
import Badge from "../components/Badge";
import Skeleton from "../components/Skeleton";
import Slider from "../components/Slider";
import Modal from "../components/Modal";
import Section from "../components/Section";
import PipelineAnimation from "../components/PipelineAnimation";
import ResidueSequence from "../components/ResidueSequence";
import { InfoTooltip } from "../components/Tooltip";
import { usePresentationStore } from "../store/presentationStore";
import {
  AD_TIER_COLORS,
  CHART_LEGEND_STYLE,
  tooltipContentStyle,
  tooltipItemStyle,
  tooltipLabelStyle,
} from "../components/chartTheme";
import type { EvidenceCard } from "../types/c4";

const AD_TIERS = Object.keys(AD_TIER_COLORS);

export default function C4Page() {
  const [summary, setSummary] = useState<any>(null);
  const [adSummary, setAdSummary] = useState<any>(null);
  const [parrs, setParrs] = useState<any>(null);
  const [pdss, setPdss] = useState<any>(null);
  const [arr, setArr] = useState<any>(null);
  const [cards, setCards] = useState<EvidenceCard[]>([]);

  const [tierFilter, setTierFilter] = useState<Set<string>>(new Set(AD_TIERS));
  const [speciesFilter, setSpeciesFilter] = useState<string>("");
  const [scoreMin, setScoreMin] = useState(0);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const resetSignal = usePresentationStore((s) => s.resetSignal);

  useEffect(() => {
    if (resetSignal === 0) return;
    setTierFilter(new Set(AD_TIERS));
    setSpeciesFilter("");
    setScoreMin(0);
    setExpandedId(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resetSignal]);

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

  function toggleTier(tier: string) {
    setTierFilter((prev) => {
      const next = new Set(prev);
      if (next.has(tier)) next.delete(tier);
      else next.add(tier);
      return next;
    });
  }

  const speciesOptions = useMemo(
    () => Array.from(new Set(cards.map((c) => c.plant_species))).sort(),
    [cards]
  );

  const sourceProteinsForSpecies = useMemo(() => {
    if (!speciesFilter) return [];
    const proteins = cards.filter((c) => c.plant_species === speciesFilter).map((c) => c.source_protein.split("|")[1] ?? c.source_protein);
    return Array.from(new Set(proteins));
  }, [cards, speciesFilter]);

  const filteredCards = useMemo(
    () =>
      cards.filter(
        (c) =>
          tierFilter.has(c.ad_tier) &&
          (!speciesFilter || c.plant_species === speciesFilter) &&
          c.combined_score >= scoreMin
      ),
    [cards, tierFilter, speciesFilter, scoreMin]
  );

  const expandedCard = cards.find((c) => c.candidate_id === expandedId) ?? null;
  const expandedIndex = filteredCards.findIndex((c) => c.candidate_id === expandedId);
  function gotoRelative(delta: number) {
    if (expandedIndex === -1) return;
    const next = expandedIndex + delta;
    if (next < 0 || next >= filteredCards.length) return;
    setExpandedId(filteredCards[next].candidate_id);
  }

  return (
    <div>
      <PageHeader
        eyebrow="Component 4"
        title="PlantAOP-Screen"
        subtitle="Plant Digestome Screening with Applicability-Domain Abstention"
      />
      <div className="space-y-6 p-8">
        <Section id="c4-overview" label="Overview">
          {summary && <Banner title={`Source: ${summary.source}`}>{summary.notes?.join(" ")}</Banner>}

          {summary && (
            <div className="mt-6 grid grid-cols-2 gap-4 md:grid-cols-4">
              <StatCard label="Source proteins" value={summary.n_source_proteins} />
              <StatCard label="Candidate fragments" value={summary.n_candidate_fragments} />
              <StatCard
                label="PARRS"
                value={parrs?.parrs ?? "…"}
                sub="AD-tier enrichment of top ranks"
                accent="teal"
                tooltip="Plant AOP Rank-Retrieval Score: how enriched the top-ranked candidates are for high-confidence AD tiers, vs. what random ranking would give."
              />
              <StatCard
                label="PDSS"
                value={pdss?.pdss ?? "…"}
                sub="distributional shift vs. AOP-BenchPos"
                accent="violet"
                tooltip="Plant Digestome Shift Score: how far the candidate fragments' physicochemical distribution has drifted from the real AOP-BenchPos training distribution."
              />
            </div>
          )}
          {!summary && (
            <div className="mt-6 grid grid-cols-2 gap-4 md:grid-cols-4">
              {Array.from({ length: 4 }).map((_, i) => (
                <Skeleton key={i} className="h-[4.75rem]" />
              ))}
            </div>
          )}
        </Section>

        <Section
          id="c4-pipeline"
          label="How screening works"
          notes="Walk through the 6 stages in order — this is where C1's retrieval similarity, C2's classifier, and C3's reliability audit all come together into one ranked candidate list. Hit Play Pipeline for a visual recap."
        >
          <Card
            title="How screening works"
            subtitle="From plant proteins to a ranked, abstention-aware candidate list"
            eyebrow="Pipeline"
          >
            <PipelineAnimation
              stages={[
                { label: "Source proteins", detail: "Real plant proteins are the raw input — whole sequences, not yet fragmented." },
                { label: "Fragment generation", detail: "Each protein is digested in silico (simulated enzyme cleavage) into candidate peptide fragments." },
                { label: "C1 scoring", detail: "Every fragment is embedded and compared to the real AOP-ProCon prototype space — sim_c1 measures how close it sits to known antioxidant mechanisms." },
                { label: "C2 scoring", detail: "The same fragment is scored by the real C2 PU-AOP classifier — prob_c2 is its predicted antioxidant probability." },
                { label: "AD assignment", detail: "An applicability-domain check flags whether the fragment falls inside a region the models were actually trained on (Tier1/Tier2) or should be treated with caution/abstained on." },
                { label: "Final ranking", detail: "sim_c1, prob_c2, and the AD tier are combined into combined_score, which ranks the evidence cards shown below." },
              ]}
            />
          </Card>
        </Section>

        <Section id="c4-ad-confidence" label="AD tiers & confidence">
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
        </Section>

        <Section
          id="c4-evidence"
          label="Evidence cards"
          notes="Let the panel filter by AD tier and drag the score slider themselves. Open a card and use Prev/Next to browse a few candidates without losing the current filter — good moment to point out the residue coloring and sim_C1/prob_C2 bars."
        >
        <Card
          title="Evidence cards"
          subtitle="Top-ranked candidates, computed from real C1/C2/C3 outputs"
          eyebrow="Output"
          actions={
            <span className="label-tag text-ink-faint">
              {filteredCards.length} / {cards.length} shown
            </span>
          }
        >
          <div className="mb-5 flex flex-wrap items-end gap-x-8 gap-y-4">
            <div>
              <p className="label-tag mb-2 text-ink-faint">AD tier</p>
              <div className="flex gap-1.5">
                {AD_TIERS.map((tier) => {
                  const active = tierFilter.has(tier);
                  return (
                    <button
                      key={tier}
                      onClick={() => toggleTier(tier)}
                      className="label-tag rounded-full border px-2.5 py-1 transition-all"
                      style={{
                        borderColor: active ? AD_TIER_COLORS[tier] : "var(--c-line-strong)",
                        color: active ? AD_TIER_COLORS[tier] : "rgb(var(--c-ink-faint))",
                        opacity: active ? 1 : 0.45,
                      }}
                    >
                      {tier}
                    </button>
                  );
                })}
              </div>
            </div>

            <div>
              <p className="label-tag mb-2 text-ink-faint">Plant species</p>
              <select
                value={speciesFilter}
                onChange={(e) => setSpeciesFilter(e.target.value)}
                className="rounded-lg border border-line-strong bg-surface2 px-2.5 py-1.5 text-xs text-ink font-data focus:outline-none"
              >
                <option value="">All species</option>
                {speciesOptions.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
              {speciesFilter && (
                <div className="mt-2 flex max-w-xs flex-wrap gap-1">
                  {sourceProteinsForSpecies.map((p) => (
                    <span key={p} className="label-tag rounded-full border border-line-strong px-2 py-0.5 text-ink-faint">
                      {p}
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div className="min-w-[14rem]">
              <p className="label-tag mb-2 text-ink-faint">Min. combined score</p>
              <Slider min={0} max={1} step={0.01} value={scoreMin} onChange={setScoreMin} />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-3">
            <AnimatePresence>
              {filteredCards.map((card, i) => (
                <motion.button
                  key={card.candidate_id}
                  layout
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95 }}
                  transition={{ delay: Math.min(i * 0.04, 0.5), duration: 0.35 }}
                  onClick={() => setExpandedId(card.candidate_id)}
                  className="rounded-xl border border-line bg-surface2/50 p-4 text-left transition-colors hover:border-line-strong hover:bg-surface2"
                >
                  <div className="flex items-center justify-between">
                    <span className="font-data text-sm font-medium text-ink">{card.sequence}</span>
                    <Badge flag={card.abstention_flag}>{card.abstention_flag}</Badge>
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
                </motion.button>
              ))}
            </AnimatePresence>
          </div>

          {filteredCards.length === 0 && (
            <p className="py-8 text-center text-sm text-ink-faint">No candidates match the current filters.</p>
          )}
        </Card>
        </Section>
      </div>

      <Modal open={!!expandedCard} onClose={() => setExpandedId(null)} title={expandedCard?.sequence}>
        {expandedCard && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex flex-wrap items-center gap-2">
                <Badge flag={expandedCard.abstention_flag}>{expandedCard.abstention_flag}</Badge>
                <span className="label-tag text-ink-faint">{expandedCard.ad_tier}</span>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => gotoRelative(-1)}
                  disabled={expandedIndex <= 0}
                  aria-label="Previous candidate"
                  className="rounded-lg border border-line-strong p-1.5 text-ink-faint transition-colors hover:bg-surface2 hover:text-ink disabled:opacity-30"
                >
                  <ChevronLeft size={14} />
                </button>
                <span className="label-tag px-1 text-ink-faint">
                  {expandedIndex + 1}/{filteredCards.length}
                </span>
                <button
                  onClick={() => gotoRelative(1)}
                  disabled={expandedIndex >= filteredCards.length - 1}
                  aria-label="Next candidate"
                  className="rounded-lg border border-line-strong p-1.5 text-ink-faint transition-colors hover:bg-surface2 hover:text-ink disabled:opacity-30"
                >
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>

            <ResidueSequence sequence={expandedCard.sequence} />

            <p className="text-sm text-ink-dim">
              {expandedCard.plant_species} · {expandedCard.source_protein} · digested by {expandedCard.enzyme} ·{" "}
              {expandedCard.length} aa
            </p>

            <div className="space-y-2.5 rounded-lg border border-line bg-surface2/50 p-4">
              <div>
                <div className="flex items-center justify-between text-xs text-ink-dim">
                  <span>sim_C1 (C1 retrieval similarity)</span>
                  <span className="font-data text-ink">{expandedCard.sim_c1}</span>
                </div>
                <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-surface3">
                  <div className="h-full rounded-full bg-teal" style={{ width: `${Math.min(expandedCard.sim_c1 * 100, 100)}%` }} />
                </div>
              </div>
              <div>
                <div className="flex items-center justify-between text-xs text-ink-dim">
                  <span>prob_C2 (C2 antioxidant probability)</span>
                  <span className="font-data text-ink">{expandedCard.prob_c2}</span>
                </div>
                <div className="mt-1 h-1.5 w-full overflow-hidden rounded-full bg-surface3">
                  <div className="h-full rounded-full bg-violet" style={{ width: `${Math.min(expandedCard.prob_c2 * 100, 100)}%` }} />
                </div>
              </div>
            </div>

            <div className="grid grid-cols-2 gap-x-6 gap-y-2 rounded-lg border border-line bg-surface2/50 p-4 font-data text-sm text-ink-dim md:grid-cols-3">
              <span>MW <span className="text-ink">{expandedCard.physicochemical_summary.molecular_weight}</span></span>
              <span>GRAVY <span className="text-ink">{expandedCard.physicochemical_summary.gravy}</span></span>
              <span>Net charge <span className="text-ink">{expandedCard.physicochemical_summary.net_charge}</span></span>
              <span>Aromaticity <span className="text-ink">{expandedCard.physicochemical_summary.aromaticity}</span></span>
              <span>AD distance <span className="text-ink">{expandedCard.ad_distance}</span></span>
              <span>Combined score <span className="text-ink">{expandedCard.combined_score}</span></span>
            </div>
            {expandedCard.interpretation && (
              <p className="border-t border-line pt-3 text-xs italic leading-relaxed text-ink-faint">
                {expandedCard.interpretation}
              </p>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
