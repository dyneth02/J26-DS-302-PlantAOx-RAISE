import { useEffect, useState } from "react";
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  ZAxis,
  Tooltip,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  Cell,
  ReferenceLine,
} from "recharts";
import { c1Api } from "../api/client";
import PageHeader from "../components/PageHeader";
import Card from "../components/Card";
import Banner from "../components/Banner";
import StatCard from "../components/StatCard";
import {
  CHART_GRID,
  CHART_LEGEND_STYLE,
  CHART_TICK,
  TIER_COLORS,
  tooltipContentStyle,
  tooltipItemStyle,
  tooltipLabelStyle,
} from "../components/chartTheme";

const MODEL_COLORS: Record<string, string> = {
  "Baseline (original Phase 4)": "rgb(var(--c-lime))",
  "Primary-v2": "rgb(var(--c-teal))",
  "HP1-Random": "rgb(var(--c-amber))",
  "HP2-Fusion": "rgb(var(--c-violet))",
  "Primary-v2-Balanced": "rgb(var(--c-coral))",
};

const MODEL_SHORT_NAMES: Record<string, string> = {
  "Baseline (original Phase 4)": "Baseline",
  "Primary-v2": "Primary-v2",
  "HP1-Random": "HP1-Random",
  "HP2-Fusion": "HP2-Fusion",
  "Primary-v2-Balanced": "Balanced",
};

// Synthetic, illustrative-only points for the "expected outcome" hypothesis chart.
// NOT derived from or mixed with any real embedding data — purely a target-state sketch.
// Computed once at module load (not per-render) so the illustration stays stable.
function gaussianJitter(spread: number) {
  const u1 = Math.random() || 1e-6;
  const u2 = Math.random();
  return Math.sqrt(-2 * Math.log(u1)) * Math.cos(2 * Math.PI * u2) * spread;
}
function generateIllustrativeClusters() {
  const clusters = [
    { tier: "Tier1_FRS", cx: -0.14, cy: 0.1, spread: 0.032, n: 130 },
    { tier: "Tier2_MC", cx: 0.14, cy: -0.11, spread: 0.028, n: 55 },
    { tier: "Tier3_GEN", cx: 0.0, cy: -0.2, spread: 0.038, n: 150 },
  ];
  const points: { x: number; y: number; mechanism_tier: string; sequence: string }[] = [];
  clusters.forEach(({ tier, cx, cy, spread, n }) => {
    for (let i = 0; i < n; i++) {
      points.push({
        x: cx + gaussianJitter(spread),
        y: cy + gaussianJitter(spread),
        mechanism_tier: tier,
        sequence: "illustrative",
      });
    }
  });
  return points;
}
const ILLUSTRATIVE_EMBEDDING = generateIllustrativeClusters();

export default function C1Page() {
  const [summary, setSummary] = useState<any>(null);
  const [umap, setUmap] = useState<any[]>([]);
  const [prototypes, setPrototypes] = useState<any>(null);
  const [retrieval, setRetrieval] = useState<any[]>([]);
  const [sufficiency, setSufficiency] = useState<any>(null);
  const [scaling, setScaling] = useState<any>(null);

  const [trainedSummary, setTrainedSummary] = useState<any>(null);
  const [trainedEmbedding, setTrainedEmbedding] = useState<any[]>([]);
  const [trainedPrototypes, setTrainedPrototypes] = useState<any>(null);
  const [trainedRetrieval, setTrainedRetrieval] = useState<any[]>([]);
  const [ablation, setAblation] = useState<any>(null);
  const [trainingHistory, setTrainingHistory] = useState<any[]>([]);
  const [statTests, setStatTests] = useState<any[]>([]);
  const [tier3Summary, setTier3Summary] = useState<any>(null);
  const [experiment, setExperiment] = useState<any>(null);
  const [showDetails, setShowDetails] = useState(false);
  const [presentationMode, setPresentationMode] = useState(true);
  const [visibleTiers, setVisibleTiers] = useState<Record<string, boolean>>({
    Tier1_FRS: true,
    Tier2_MC: true,
    Tier3_GEN: true,
  });
  const [visibleBaselineTiers, setVisibleBaselineTiers] = useState<Record<string, boolean>>({
    Tier1_FRS: true,
    Tier_Dual: true,
    Tier2_MC: true,
    Tier3_GEN: true,
  });

  useEffect(() => {
    c1Api.summary().then(setSummary);
    c1Api.umap().then(setUmap);
    c1Api.prototypes().then(setPrototypes);
    c1Api.retrieval().then(setRetrieval);
    c1Api.dataSufficiency().then(setSufficiency);
    c1Api.scalingAblation().then(setScaling);

    c1Api.trainedSummary().then(setTrainedSummary);
    c1Api.trainedEmbedding().then(setTrainedEmbedding);
    c1Api.trainedPrototypes().then(setTrainedPrototypes);
    c1Api.trainedRetrieval().then(setTrainedRetrieval);
    c1Api.ablationComparison().then((data) => {
      // Recharts' Bar animation keys off the data array reference; mapping inline in JSX
      // creates a new array every render and can leave bars stuck at zero height. Transform
      // once, here, so the array identity is stable across re-renders.
      const results = (data?.results ?? []).map((row: any) => ({ ...row, recall10: row["recall@10"] }));
      setAblation({ ...data, results });
    });
    c1Api.trainingHistory().then(setTrainingHistory);
    c1Api.statisticalTests().then(setStatTests);
    c1Api.tier3Summary().then(setTier3Summary);
    c1Api.improvementExperiment().then((data) => {
      // Same reasoning as the ablation-comparison fix: transform once here, not inline in
      // JSX, so Recharts' Bar data-array reference stays stable across unrelated re-renders.
      const rows = [...(data.reference_results ?? []), ...(data.experiment_results ?? [])].map((row: any) => ({
        ...row,
        recall10: row["recall@10"],
        tier2recall5: row["tier2_recall@5"],
      }));
      setExperiment({ ...data, rows });
    });
  }, []);

  const umapByTier = umap.reduce<Record<string, any[]>>((acc, pt) => {
    (acc[pt.mechanism_tier] ??= []).push(pt);
    return acc;
  }, {});

  const trainedByTier = trainedEmbedding.reduce<Record<string, any[]>>((acc, pt) => {
    (acc[pt.mechanism_tier] ??= []).push(pt);
    return acc;
  }, {});

  const illustrativeByTier = ILLUSTRATIVE_EMBEDDING.reduce<Record<string, any[]>>((acc, pt) => {
    (acc[pt.mechanism_tier] ??= []).push(pt);
    return acc;
  }, {});

  const toggleTier = (tier: string) => setVisibleTiers((prev) => ({ ...prev, [tier]: !prev[tier] }));
  const toggleBaselineTier = (tier: string) => setVisibleBaselineTiers((prev) => ({ ...prev, [tier]: !prev[tier] }));

  const tierToggleButtons = (tiers: string[], visible: Record<string, boolean>, onToggle: (tier: string) => void) =>
    tiers.map((tier) => {
      const on = visible[tier];
      return (
        <button
          key={tier}
          type="button"
          onClick={() => onToggle(tier)}
          className="flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs font-medium transition-opacity"
          style={{
            borderColor: TIER_COLORS[tier],
            color: on ? "rgb(var(--c-ink))" : "rgb(var(--c-ink-faint))",
            opacity: on ? 1 : 0.45,
          }}
        >
          <span className="inline-block h-2 w-2 rounded-full" style={{ backgroundColor: TIER_COLORS[tier] }} />
          {tier}
        </button>
      );
    });

  return (
    <div>
      <PageHeader
        eyebrow="Component 1"
        title="AOP-ProCon"
        subtitle="Mechanism-Aware Positive-Only Prototype Contrastive Representation Learning"
      />
      <div className="space-y-6 p-8">
        <div className="flex justify-end">
          <button
            type="button"
            onClick={() => setPresentationMode((v) => !v)}
            className="flex items-center gap-2 rounded-full border border-line-strong px-3 py-1.5 text-xs font-medium text-ink-dim transition-colors hover:bg-surface2/60"
          >
            <span
              className="inline-block h-1.5 w-1.5 rounded-full"
              style={{ backgroundColor: presentationMode ? "rgb(var(--c-lime))" : "rgb(var(--c-ink-faint))" }}
            />
            {presentationMode ? "Presentation view" : "Full technical view"}
          </button>
        </div>

        {!presentationMode && sufficiency && sufficiency.alert_level === "HIGH" && (
          <Banner variant="warning" title="Data sufficiency alert">
            {sufficiency.issue}. Tier counts: {JSON.stringify(sufficiency.tier_counts)}. Target minimum per
            training-eligible tier: {sufficiency.target_minimum}.
            <div className="mt-1 text-xs text-ink-faint">{sufficiency.history}</div>
          </Banner>
        )}

        {summary && (
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatCard label="Total sequences" value={summary.total_sequences} />
            <StatCard label="Training eligible" value={summary.training_eligible_sequences} />
            <StatCard label="Tier1_FRS" value={summary.tier_counts.Tier1_FRS} accent="teal" />
            <StatCard label="Tier2_MC" value={summary.tier_counts.Tier2_MC} accent="amber" />
            <StatCard label="Tier_Dual" value={summary.tier_counts.Tier_Dual} accent="violet" />
            <StatCard label="Tier3_GEN" value={summary.tier_counts.Tier3_GEN} />
          </div>
        )}

        {/* ================= REAL TRAINED MODEL (headline = current best, promoted from the Phase 5c experiment below) ================= */}
        {trainedSummary && presentationMode && (
          <div className="panel relative overflow-hidden p-8 md:p-10">
            <div
              className="pointer-events-none absolute -right-16 -top-24 h-72 w-72 rounded-full bg-lime/10 blur-3xl animate-drift"
              aria-hidden
            />
            <div
              className="pointer-events-none absolute -left-20 bottom-0 h-56 w-56 rounded-full bg-teal/10 blur-3xl"
              aria-hidden
            />
            <p className="label-tag text-lime">Real trained model</p>
            <h2 className="relative mt-2.5 max-w-2xl font-display text-2xl font-medium leading-snug tracking-tight text-ink md:text-[1.75rem]">
              Retrieves antioxidant peptides by shared mechanism — not just raw sequence similarity.
            </h2>
            <div className="relative mt-9 grid grid-cols-1 gap-8 sm:grid-cols-3">
              <div>
                <p className="text-glow font-display text-6xl font-medium leading-none tracking-tight text-lime">
                  {Math.round((trainedSummary.primary_metrics["recall@10"] ?? 0) * 100)}%
                </p>
                <p className="mt-3 label-tag text-ink-faint">Recall@10 retrieval accuracy</p>
              </div>
              <div>
                <p className="font-display text-6xl font-medium leading-none tracking-tight text-teal">
                  {Math.round((trainedSummary.primary_metrics["tier2_recall@5"] ?? 0) * 100)}%
                </p>
                <p className="mt-3 label-tag text-ink-faint">Tier2 (hardest tier) Recall@5</p>
              </div>
              <div>
                <p className="font-display text-6xl font-medium leading-none tracking-tight text-amber">
                  {(summary?.total_sequences ?? 0).toLocaleString()}
                </p>
                <p className="mt-3 label-tag text-ink-faint">Real curated peptide sequences</p>
              </div>
            </div>
          </div>
        )}

        {trainedSummary && !presentationMode && (
          <Banner title={
            trainedSummary.promoted_from
              ? `Real trained model — current best: ${trainedSummary.promoted_from} (checkpoint epoch ${trainedSummary.checkpoint_epoch})`
              : `Real trained positive-only SupCon model — checkpoint epoch ${trainedSummary.checkpoint_epoch}`
          }>
            {trainedSummary.notes?.join(" ")}
          </Banner>
        )}

        {trainedSummary && !presentationMode && (
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatCard label="Recall@10 (LSO)" value={trainedSummary.primary_metrics.recall_10 ?? trainedSummary.primary_metrics["recall@10"]} accent="teal" />
            <StatCard label="nDCG@10" value={trainedSummary.primary_metrics["ndcg@10"]} accent="teal" />
            <StatCard label="Tier2 Recall@5" value={trainedSummary.primary_metrics.tier2_recall_5 ?? trainedSummary.primary_metrics["tier2_recall@5"]} accent="amber" />
            <StatCard label="ARI (K=3 K-means)" value={trainedSummary.primary_metrics.ari} accent="violet" />
          </div>
        )}

        {presentationMode && (
          <Card
            title="How AOP-ProCon works"
            subtitle="A simplified walkthrough using example peptides — illustrative only, not real experimental data"
            eyebrow="CONCEPT WALKTHROUGH · ILLUSTRATIVE EXAMPLE"
          >
            <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
              <div className="panel p-4">
                <p className="label-tag text-lime">Step 1</p>
                <p className="mt-2 text-sm leading-relaxed text-ink">
                  Every peptide's sequence is turned into a numeric "fingerprint" using a pretrained protein language
                  model (ESM-2) that already understands general patterns from millions of proteins.
                </p>
              </div>
              <div className="panel p-4">
                <p className="label-tag text-teal">Step 2</p>
                <p className="mt-2 text-sm leading-relaxed text-ink">
                  During training, the model only looks at pairs of peptides <em>known</em> to share the same
                  mechanism, and nudges their fingerprints closer together — no need for hard-to-find "confirmed
                  non-antioxidant" examples.
                </p>
              </div>
              <div className="panel p-4">
                <p className="label-tag text-amber">Step 3</p>
                <p className="mt-2 text-sm leading-relaxed text-ink">
                  For a new, unlabelled peptide, we compare its fingerprint to known ones — its closest matches
                  reveal its most likely mechanism. This "nearest neighbour" lookup is what we call retrieval.
                </p>
              </div>
            </div>

            <p className="mt-6 label-tag text-ink-faint">Example (illustrative, not real data)</p>
            <div className="mt-2 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-ink-faint">
                    <th className="py-2 pr-4 label-tag font-normal">Example peptide</th>
                    <th className="py-2 pr-4 label-tag font-normal">Mechanism</th>
                    <th className="py-2 label-tag font-normal">What training does</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-line">
                    <td className="py-2.5 pr-4 font-data text-ink">PEP-A</td>
                    <td className="py-2.5 pr-4 text-ink-dim">
                      <span className="inline-block h-2 w-2 rounded-full mr-1.5 align-middle" style={{ backgroundColor: TIER_COLORS.Tier1_FRS }} />
                      Tier1 · Free-radical scavenging
                    </td>
                    <td className="py-2.5 text-ink-dim">Pulled toward other Tier1 peptides</td>
                  </tr>
                  <tr className="border-b border-line">
                    <td className="py-2.5 pr-4 font-data text-ink">PEP-B</td>
                    <td className="py-2.5 pr-4 text-ink-dim">
                      <span className="inline-block h-2 w-2 rounded-full mr-1.5 align-middle" style={{ backgroundColor: TIER_COLORS.Tier1_FRS }} />
                      Tier1 · Free-radical scavenging
                    </td>
                    <td className="py-2.5 text-ink-dim">Pulled toward PEP-A (same mechanism)</td>
                  </tr>
                  <tr className="border-b border-line last:border-0">
                    <td className="py-2.5 pr-4 font-data text-ink">PEP-C</td>
                    <td className="py-2.5 pr-4 text-ink-dim">
                      <span className="inline-block h-2 w-2 rounded-full mr-1.5 align-middle" style={{ backgroundColor: TIER_COLORS.Tier2_MC }} />
                      Tier2 · Metal chelation
                    </td>
                    <td className="py-2.5 text-ink-dim">Pushed apart from the Tier1 group</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </Card>
        )}

        {presentationMode && (
          <Card
            title="Why this is different"
            subtitle="How AOP-ProCon compares to existing antioxidant peptide predictors"
            eyebrow="NOVELTY"
          >
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-ink-faint">
                    <th className="py-2 pr-4 label-tag font-normal">Approach</th>
                    <th className="py-2 pr-4 label-tag font-normal">How it's trained</th>
                    <th className="py-2 label-tag font-normal">Limitation</th>
                  </tr>
                </thead>
                <tbody>
                  <tr className="border-b border-line">
                    <td className="py-2.5 pr-4 text-ink-dim">AnOxPePred, Multi-AOP, and similar</td>
                    <td className="py-2.5 pr-4 text-ink-dim">Binary classifier — trained against random or synthetic negative examples</td>
                    <td className="py-2.5 text-ink-dim">Treats all antioxidant peptides as one class; no mechanism structure</td>
                  </tr>
                  <tr className="border-b border-line last:border-0 bg-lime/[0.04]">
                    <td className="py-2.5 pr-4 text-ink">
                      <span className="inline-block h-2 w-2 rounded-full mr-1.5 align-middle bg-lime" />
                      AOP-ProCon (this project)
                    </td>
                    <td className="py-2.5 pr-4 text-ink-dim">Positive-only — only pairs of peptides with a <em>confirmed shared mechanism</em>, no negatives needed</td>
                    <td className="py-2.5 text-ink-dim">Output is a structured, mechanism-aware representation space, not just a yes/no label</td>
                  </tr>
                </tbody>
              </table>
            </div>
            <p className="mt-3 text-xs leading-relaxed text-ink-faint">
              This isn't standard self-supervised learning either (e.g. SimCLR) — those use artificial data
              augmentations as the "positive" signal. Here, the positive signal is a real biological fact: two
              peptides confirmed to share the same antioxidant mechanism.
            </p>
          </Card>
        )}

        {presentationMode && (
          <Card
            title="Expected outcome — target embedding space"
            subtitle="Illustrative sketch of the hypothesis (not measured data): fully mechanism-aware training should separate the 3 tiers cleanly"
            eyebrow="HYPOTHESIS · ILLUSTRATIVE, NOT ACHIEVED"
          >
            <ResponsiveContainer width="100%" height={320}>
              <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
                <CartesianGrid stroke={CHART_GRID} />
                <XAxis type="number" dataKey="x" name="dim 1" tick={CHART_TICK} axisLine={{ stroke: CHART_GRID }} tickLine={false} />
                <YAxis type="number" dataKey="y" name="dim 2" tick={CHART_TICK} axisLine={{ stroke: CHART_GRID }} tickLine={false} />
                <ZAxis range={[30, 30]} />
                <Legend wrapperStyle={CHART_LEGEND_STYLE} />
                {Object.entries(illustrativeByTier).map(([tier, points]) => (
                  <Scatter key={tier} name={tier} data={points} fill={TIER_COLORS[tier] ?? "#999"} fillOpacity={0.8} isAnimationActive={false} />
                ))}
              </ScatterChart>
            </ResponsiveContainer>
            <p className="mt-2 text-xs leading-relaxed text-ink-faint">
              This is a target sketch, not a result — it illustrates what the project hypothesises full mechanism-aware
              separation would look like. The real embedding space measured from our trained model is available in
              Full technical view above.
            </p>
          </Card>
        )}

        {!presentationMode && (
        <Card
          title="Trained embedding space"
          subtitle="PCA(2) over the REAL 128-D output of the current best trained model — not raw ESM-2"
          eyebrow={trainedSummary?.promoted_from ? "Real · current best model" : "Real · Phase 4"}
          actions={tierToggleButtons(["Tier1_FRS", "Tier2_MC", "Tier3_GEN"], visibleTiers, toggleTier)}
        >
          <div className={presentationMode ? "relative -m-2 overflow-hidden rounded-xl p-2" : ""}>
            {presentationMode && (
              <div
                className="pointer-events-none absolute inset-0 -z-10"
                style={{
                  background:
                    "radial-gradient(55% 55% at 35% 25%, rgb(var(--c-lime) / 0.07), transparent 70%)," +
                    "radial-gradient(45% 45% at 75% 80%, rgb(var(--c-teal) / 0.06), transparent 70%)",
                }}
                aria-hidden
              />
            )}
            <ResponsiveContainer width="100%" height={presentationMode ? 480 : 420}>
              <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
                <CartesianGrid stroke={CHART_GRID} />
                <XAxis type="number" dataKey="x" name="dim 1" tick={CHART_TICK} axisLine={{ stroke: CHART_GRID }} tickLine={false} />
                <YAxis type="number" dataKey="y" name="dim 2" tick={CHART_TICK} axisLine={{ stroke: CHART_GRID }} tickLine={false} />
                <ZAxis range={presentationMode ? [34, 34] : [24, 24]} />
                <Tooltip
                  cursor={{ strokeDasharray: "3 3", stroke: CHART_GRID }}
                  content={({ active, payload }) =>
                    active && payload?.length ? (
                      <div style={tooltipContentStyle()} className="px-3 py-2">
                        <p className="font-medium text-ink">{payload[0].payload.sequence}</p>
                        <p className="text-ink-faint">{payload[0].payload.mechanism_tier}</p>
                      </div>
                    ) : null
                  }
                />
                <Legend wrapperStyle={CHART_LEGEND_STYLE} />
                {Object.entries(trainedByTier)
                  .filter(([tier]) => visibleTiers[tier])
                  .map(([tier, points]) => (
                    <Scatter
                      key={tier}
                      name={tier}
                      data={points}
                      fill={TIER_COLORS[tier] ?? "#999"}
                      fillOpacity={presentationMode ? 0.88 : 0.75}
                      isAnimationActive={false}
                    />
                  ))}
              </ScatterChart>
            </ResponsiveContainer>
          </div>
          <p className="mt-2 text-xs text-ink-faint">
            {presentationMode
              ? "Tier1 and Tier2 (the two mechanism-labelled tiers) visibly tighten compared to the untrained baseline."
              : 'Tier1/Tier2 visibly tighten relative to raw ESM-2 (see "Additional evidence" below); Tier3 (never trained on) still overlaps Tier1, matching the log\'s own documented finding.'}
          </p>
          {trainedPrototypes && (
            <div className="mt-4 grid grid-cols-1 gap-3 md:grid-cols-3">
              {Object.entries(trainedPrototypes.pairwise_distances).map(([pair, dist]: [string, any]) => (
                <div key={pair} className="panel p-3 text-center">
                  <p className="label-tag text-ink-faint">{pair} distance</p>
                  <p className="mt-1 font-display text-xl font-medium text-ink">{dist}</p>
                </div>
              ))}
            </div>
          )}
        </Card>
        )}

        <Card
          title={presentationMode ? "Model comparison" : "Ablation comparison"}
          subtitle={
            presentationMode
              ? "Several training variants were tried; retrieval accuracy (Recall@10) compared across each"
              : "Recomputed independently from the real checkpoints (this prototype's own re-evaluation, not copied from the log)"
          }
          eyebrow="Real · Phase 4v2/5b"
        >
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={ablation?.results ?? []} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
              <CartesianGrid stroke={CHART_GRID} vertical={false} />
              <XAxis
                dataKey="model"
                tickFormatter={(name: string) => MODEL_SHORT_NAMES[name] ?? name}
                tick={{ ...CHART_TICK, fontSize: 10 }}
                axisLine={{ stroke: CHART_GRID }}
                tickLine={false}
                interval={0}
              />
              <YAxis domain={[0, 1]} tick={CHART_TICK} axisLine={{ stroke: CHART_GRID }} tickLine={false} />
              <Tooltip contentStyle={tooltipContentStyle()} labelStyle={tooltipLabelStyle()} itemStyle={tooltipItemStyle()} />
              <Legend wrapperStyle={CHART_LEGEND_STYLE} />
              <Bar dataKey="recall10" name="Recall@10" radius={[4, 4, 0, 0]} isAnimationActive={false}>
                {(ablation?.results ?? []).map((row: any, i: number) => (
                  <Cell key={i} fill={MODEL_COLORS[row.model] ?? "rgb(var(--c-ink-faint))"} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
          {presentationMode ? (
            <p className="mt-3 text-xs leading-relaxed text-ink-faint">
              All variants score highly (94–98% retrieval accuracy); later experiments (below) build on this to
              close the gap for the harder, data-scarce Tier2 mechanism specifically.
            </p>
          ) : (
            <div className="mt-4 overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-ink-faint">
                    <th className="py-2 pr-4 label-tag font-normal">Model</th>
                    <th className="py-2 pr-4 label-tag font-normal">Recall@10</th>
                    <th className="py-2 pr-4 label-tag font-normal">Tier2 Recall@5</th>
                    <th className="py-2 label-tag font-normal">ARI</th>
                  </tr>
                </thead>
                <tbody>
                  {ablation?.results?.map((row: any) => (
                    <tr key={row.model} className="border-b border-line last:border-0">
                      <td className="py-2 pr-4 text-ink">{row.model}</td>
                      <td className="py-2 pr-4 font-data text-ink-dim">{row["recall@10"]}</td>
                      <td className="py-2 pr-4 font-data text-ink-dim">{row["tier2_recall@5"]}</td>
                      <td className="py-2 font-data text-ink-dim">{row.ari}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {experiment && (
          <Card
            title={presentationMode ? "Improving the weak spot: Tier2 retrieval" : "Phase 5c — k-NN pairing + ARI-based checkpointing"}
            subtitle={
              presentationMode
                ? "4 candidate improvements were trained and evaluated head-to-head against the original model"
                : "4 models trained fresh in this environment, using the exact loss/architecture/batching code from the student's own notebook. Not the same as Step 6 in the build guide (HP5 ESM-2 scaling ablation) — this is a rework of the Phase 5/5b pairing & checkpoint-selection methodology, still not started."
            }
            eyebrow="Real · Phase 5c"
          >
            {!presentationMode && <p className="text-sm leading-relaxed text-ink-dim">{experiment.description}</p>}

            {(() => {
              const chartRows = presentationMode
                ? experiment.rows.filter((r: any) => r.source?.includes("this experiment"))
                : experiment.rows;
              return (
                <ResponsiveContainer width="100%" height={280} className="mt-4">
                  <BarChart data={chartRows} margin={{ top: 10, right: 20, left: 0, bottom: 10 }}>
                    <CartesianGrid stroke={CHART_GRID} vertical={false} />
                    <XAxis
                      dataKey="model"
                      tickFormatter={presentationMode ? (name: string) => name.split(/[:(]/)[0].trim() : undefined}
                      tick={{ ...CHART_TICK, fontSize: presentationMode ? 12 : 9 }}
                      axisLine={{ stroke: CHART_GRID }}
                      tickLine={false}
                      interval={0}
                    />
                    <YAxis domain={[-0.05, 1]} tick={CHART_TICK} axisLine={{ stroke: CHART_GRID }} tickLine={false} />
                    <Tooltip contentStyle={tooltipContentStyle()} labelStyle={tooltipLabelStyle()} itemStyle={tooltipItemStyle()} />
                    <Legend wrapperStyle={CHART_LEGEND_STYLE} />
                    <Bar dataKey="tier2recall5" name="Tier2 Recall@5" isAnimationActive={false} radius={[4, 4, 0, 0]}>
                      {chartRows.map((row: any, i: number) => (
                        <Cell key={i} fill={row.source?.includes("this experiment") ? "rgb(var(--c-lime))" : "rgb(var(--c-ink-faint))"} />
                      ))}
                    </Bar>
                    <Bar dataKey="ari" name="ARI" isAnimationActive={false} radius={[4, 4, 0, 0]}>
                      {chartRows.map((row: any, i: number) => (
                        <Cell key={i} fill={row.source?.includes("this experiment") ? "rgb(var(--c-teal))" : "rgb(var(--c-ink-faint) / 0.5)"} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              );
            })()}

            {!presentationMode && (
              <div className="mt-4 overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-line text-left text-ink-faint">
                      <th className="py-2 pr-4 label-tag font-normal">Model</th>
                      <th className="py-2 pr-4 label-tag font-normal">Recall@10</th>
                      <th className="py-2 pr-4 label-tag font-normal">Tier2 Recall@5</th>
                      <th className="py-2 pr-4 label-tag font-normal">ARI</th>
                      <th className="py-2 label-tag font-normal">Source</th>
                    </tr>
                  </thead>
                  <tbody>
                    {experiment.rows.map((row: any) => (
                      <tr
                        key={row.model}
                        className={`border-b border-line last:border-0 ${row.source?.includes("this experiment") ? "bg-lime/[0.04]" : ""}`}
                      >
                        <td className="py-2 pr-4 text-ink">{row.model}</td>
                        <td className="py-2 pr-4 font-data text-ink-dim">{row["recall@10"]}</td>
                        <td className="py-2 pr-4 font-data text-ink-dim">{row["tier2_recall@5"]}</td>
                        <td className="py-2 pr-4 font-data text-ink-dim">{row.ari}</td>
                        <td className="py-2 text-xs text-ink-faint">{row.source}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <div className="mt-4 rounded-xl border border-lime/25 bg-lime/[0.06] p-4">
              <p className="label-tag text-lime">Result</p>
              {presentationMode ? (
                <p className="mt-1.5 text-sm leading-relaxed text-ink">
                  The best combination improved retrieval for the hardest tier (Tier2) from <strong>58%</strong> to{" "}
                  <strong>83%</strong> — a large, measurable gain, achieved by making training pairs more evenly
                  distributed across sequences and refining how the best checkpoint is chosen.
                </p>
              ) : (
                <>
                  <p className="mt-1.5 text-sm leading-relaxed text-ink">
                    <strong>Option 1 (k-NN pairing)</strong> is the highest-impact single change: Tier2 Recall@5 jumps
                    from ~0.58 to <strong>0.84</strong>, beating even HP1-Random. <strong>Combining Option 1 with
                    Option 2</strong> (ARI-based checkpointing) gives the best result overall — near-identical retrieval
                    plus the highest ARI (0.124) of every model tested, real or experimental.
                  </p>
                  <p className="mt-2 text-xs leading-relaxed text-ink-faint">
                    Caveat: Option 2 used <em>alone</em> selected a checkpoint with min_proto_dist=0.053 — below the
                    project's own 0.1 collapse-warning line — despite scoring well on ARI. Pure-ARI checkpoint
                    selection can pick an unstable state; recommend combining it with a proto_dist floor, not using it
                    as the sole criterion.
                  </p>
                </>
              )}
            </div>
          </Card>
        )}

        {presentationMode && trainedRetrieval.length > 0 && (
          <Card
            title="See it work: retrieval demo"
            subtitle="Real cosine similarity search in the trained model's representation space"
            eyebrow="Real · current best model"
          >
            <div className="space-y-3">
              {trainedRetrieval.slice(0, 2).map((demo, i) => (
                <div key={i} className="rounded-lg border border-line bg-surface2/60 p-4">
                  <p className="text-sm text-ink">
                    Query <span className="font-data font-medium text-lime">{demo.query.sequence}</span>{" "}
                    <span className="text-ink-faint">({demo.query.mechanism_tier})</span>
                  </p>
                  <p className="mt-1 text-xs text-ink-faint">Closest matches found by the model:</p>
                  <div className="mt-2 flex flex-wrap gap-2">
                    {demo.top_matches.slice(0, 5).map((m: any) => (
                      <span
                        key={m.rank}
                        className="rounded-md border px-2 py-1 font-data text-xs text-ink-dim"
                        style={{ borderColor: TIER_COLORS[m.mechanism_tier === "Tier1" ? "Tier1_FRS" : m.mechanism_tier === "Tier2" ? "Tier2_MC" : "Tier3_GEN"] }}
                        title={`${m.mechanism_tier} · sim ${m.similarity}`}
                      >
                        {m.sequence} <span className="text-ink-faint">{m.similarity}</span>
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            <p className="mt-3 text-xs leading-relaxed text-ink-faint">
              Given a query peptide, the model finds its nearest neighbours in representation space — most matches
              share the query's mechanism, which is what makes retrieval-based prediction possible.
            </p>
          </Card>
        )}

        {presentationMode && (
          <div className="panel p-6">
            <p className="label-tag text-lime">What's next</p>
            <p className="mt-2 text-sm leading-relaxed text-ink">
              With the core pipeline validated and outperforming the baseline, remaining work is: (1) the PLM
              scaling ablation (does a larger ESM-2 backbone improve mechanism retrieval further?), and (2)
              packaging AOP-BenchPos and the trained representation space for use by the project's other
              components.
            </p>
          </div>
        )}

        {/* ================= ADDITIONAL EVIDENCE (hidden entirely in presentation mode; collapsed by default otherwise) ================= */}
        {!presentationMode && (
          <button
            type="button"
            onClick={() => setShowDetails((v) => !v)}
            className="panel flex w-full items-center justify-between px-4 py-3 text-left transition-colors hover:bg-surface2/60"
          >
            <span className="label-tag text-ink-dim">
              {showDetails ? "Hide" : "Show"} additional evidence & technical details
            </span>
            <span className="text-xs text-ink-faint">
              training curve · retrieval demo · significance tests · Tier3 assignment · untrained baseline
            </span>
          </button>
        )}

        {!presentationMode && showDetails && (
          <>
            <Card
              title="Training curve (original Phase 4 run)"
              subtitle="Real per-epoch loss + prototype separation for the original Colab checkpoint — historical reference, superseded above by the Phase 5c model"
              eyebrow="Real · Phase 4 · historical"
            >
              <ResponsiveContainer width="100%" height={280}>
                <LineChart data={trainingHistory} margin={{ top: 10, right: 30, left: 0, bottom: 10 }}>
                  <CartesianGrid stroke={CHART_GRID} />
                  <XAxis dataKey="epoch" tick={CHART_TICK} axisLine={{ stroke: CHART_GRID }} tickLine={false} />
                  <YAxis yAxisId="loss" tick={CHART_TICK} axisLine={{ stroke: CHART_GRID }} tickLine={false} />
                  <YAxis yAxisId="dist" orientation="right" domain={[0, 1.5]} tick={CHART_TICK} axisLine={{ stroke: CHART_GRID }} tickLine={false} />
                  <Tooltip contentStyle={tooltipContentStyle()} labelStyle={tooltipLabelStyle()} itemStyle={tooltipItemStyle()} />
                  <Legend wrapperStyle={CHART_LEGEND_STYLE} />
                  <ReferenceLine yAxisId="loss" x={3} stroke="rgb(var(--c-lime))" strokeDasharray="4 4" />
                  <Line yAxisId="loss" type="monotone" dataKey="val_loss" name="val_loss" stroke="rgb(var(--c-teal))" strokeWidth={2} dot={{ r: 3 }} />
                  <Line yAxisId="dist" type="monotone" dataKey="proto_dist" name="min_proto_dist" stroke="rgb(var(--c-amber))" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
              <p className="mt-2 text-xs text-ink-faint">Dashed line marks the restored checkpoint (best robustly-separated epoch, not the lowest raw val_loss).</p>
            </Card>

            <Card title="Trained retrieval demo" subtitle="Real cosine similarity in the current best model's 128-D space" eyebrow="Real · current best model">
              <div className="space-y-3">
                {trainedRetrieval.map((demo, i) => (
                  <div key={i} className="rounded-lg border border-line bg-surface2/60 p-4">
                    <p className="text-sm text-ink">
                      Query <span className="font-data font-medium text-lime">{demo.query.sequence}</span>{" "}
                      <span className="text-ink-faint">({demo.query.mechanism_tier})</span>
                    </p>
                    <div className="mt-2.5 flex flex-wrap gap-2">
                      {demo.top_matches.slice(0, 6).map((m: any) => (
                        <span
                          key={m.rank}
                          className="rounded-md border px-2 py-1 font-data text-xs text-ink-dim"
                          style={{ borderColor: TIER_COLORS[m.mechanism_tier === "Tier1" ? "Tier1_FRS" : m.mechanism_tier === "Tier2" ? "Tier2_MC" : "Tier3_GEN"] }}
                          title={`${m.mechanism_tier} · sim ${m.similarity}`}
                        >
                          {m.sequence} <span className="text-ink-faint">{m.similarity}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            <Card title="Statistical significance — HP1–HP4" subtitle="Real Mann-Whitney U tests, rank-biserial effect sizes, Bonferroni correction (α=0.05/4=0.0125)" eyebrow="Real · Phase 5.3">
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-line text-left text-ink-faint">
                      <th className="py-2 pr-4 label-tag font-normal">Hypothesis</th>
                      <th className="py-2 pr-4 label-tag font-normal">p-value</th>
                      <th className="py-2 pr-4 label-tag font-normal">Effect (r)</th>
                      <th className="py-2 pr-4 label-tag font-normal">Magnitude</th>
                      <th className="py-2 label-tag font-normal">Significant (Bonferroni)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {statTests.map((row: any) => (
                      <tr key={row.Hypothesis} className="border-b border-line last:border-0">
                        <td className="py-2 pr-4 text-ink">{row.Hypothesis}</td>
                        <td className="py-2 pr-4 font-data text-ink-dim">{Number(row.p_value).toExponential(3)}</td>
                        <td className="py-2 pr-4 font-data text-ink-dim">{Number(row.effect_r).toFixed(3)}</td>
                        <td className="py-2 pr-4 text-ink-dim">{row.effect_size}</td>
                        <td className="py-2">
                          <span className={`rounded-full px-2 py-0.5 label-tag ${row["significant_bonferroni_a=0.0125"] ? "bg-lime/10 text-lime ring-1 ring-lime/30" : "bg-ink-faint/10 text-ink-faint ring-1 ring-line-strong"}`}>
                            {row["significant_bonferroni_a=0.0125"] ? "YES" : "no"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-3 text-xs leading-relaxed text-ink-faint">
                Only HP3 (Tier1 vs Tier2 nDCG@10 differ) is significant, with a large effect — the representation
                strongly discriminates the two trained mechanisms. HP1 (mechanism-aware pairing helps), HP2 (ESM+physchem
                fusion helps), and HP4 (LSO exposes homology leakage) are all honestly reported as non-significant.
              </p>
            </Card>

            {tier3Summary && (
              <Card title="Tier 3 soft prototype assignment" subtitle="858 evaluation-only sequences, each scored against the 3 real trained prototypes" eyebrow="Real · Phase 5">
                <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
                  <StatCard label="Sequences" value={tier3Summary.n_sequences} />
                  <StatCard label="Mean sim → FRS" value={tier3Summary.mean_sim_frs} accent="teal" />
                  <StatCard label="Mean sim → MC" value={tier3Summary.mean_sim_mc} accent="amber" />
                  <StatCard label="Mean sim → GEN" value={tier3Summary.mean_sim_gen} />
                </div>
                <p className="mt-3 text-xs leading-relaxed text-ink-faint">
                  Tier3 sits almost equidistant between FRS and its own GEN prototype (both ≈0.998) while MC sits far
                  away (≈-0.85) — Tier1 and Tier3 occupy nearly the same trained-space region, a real, documented
                  finding, not a bug: Tier3 is mechanism-unlabelled by construction, so nothing in training pushes it
                  away from whichever tier it happens to resemble.
                </p>
              </Card>
            )}

            <div className="pt-2">
              <p className="label-tag text-ink-faint">— before training, for comparison —</p>
            </div>

            <Card
              title="Raw ESM-2 baseline"
              subtitle={summary?.projection_method ?? "Loading…"}
              eyebrow="Baseline · untrained"
              actions={tierToggleButtons(
                ["Tier1_FRS", "Tier_Dual", "Tier2_MC", "Tier3_GEN"],
                visibleBaselineTiers,
                toggleBaselineTier
              )}
            >
              <ResponsiveContainer width="100%" height={340}>
                <ScatterChart margin={{ top: 10, right: 20, bottom: 10, left: 0 }}>
                  <CartesianGrid stroke={CHART_GRID} />
                  <XAxis type="number" dataKey="umap_x" name="dim 1" tick={CHART_TICK} axisLine={{ stroke: CHART_GRID }} tickLine={false} />
                  <YAxis type="number" dataKey="umap_y" name="dim 2" tick={CHART_TICK} axisLine={{ stroke: CHART_GRID }} tickLine={false} />
                  <ZAxis range={[24, 24]} />
                  <Tooltip
                    cursor={{ strokeDasharray: "3 3", stroke: CHART_GRID }}
                    content={({ active, payload }) =>
                      active && payload?.length ? (
                        <div style={tooltipContentStyle()} className="px-3 py-2">
                          <p className="font-medium text-ink">{payload[0].payload.sequence}</p>
                          <p className="text-ink-faint">{payload[0].payload.mechanism_tier}</p>
                        </div>
                      ) : null
                    }
                  />
                  <Legend wrapperStyle={CHART_LEGEND_STYLE} />
                  {Object.entries(umapByTier)
                    .filter(([tier]) => visibleBaselineTiers[tier])
                    .map(([tier, points]) => (
                      <Scatter key={tier} name={tier} data={points} fill={TIER_COLORS[tier] ?? "#999"} fillOpacity={0.5} isAnimationActive={false} />
                    ))}
                </ScatterChart>
              </ResponsiveContainer>
            </Card>

            <Card title="Prototype centroids (untrained baseline)" subtitle="Real mean embedding per mechanism tier; purity via KMeans agreement" eyebrow="Baseline · untrained">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-ink-faint">
                    <th className="py-2 pr-4 label-tag font-normal">Tier</th>
                    <th className="py-2 pr-4 label-tag font-normal">Prototype ID</th>
                    <th className="py-2 pr-4 label-tag font-normal">Support</th>
                    <th className="py-2 label-tag font-normal">Purity</th>
                  </tr>
                </thead>
                <tbody>
                  {prototypes &&
                    Object.entries(prototypes).map(([tier, p]: [string, any]) => (
                      <tr key={tier} className="border-b border-line last:border-0">
                        <td className="py-2.5 pr-4 text-ink">
                          <span
                            className="mr-2 inline-block h-2.5 w-2.5 rounded-full align-middle"
                            style={{ backgroundColor: TIER_COLORS[tier], boxShadow: `0 0 8px 1px ${TIER_COLORS[tier]}` }}
                          />
                          {tier}
                        </td>
                        <td className="py-2.5 pr-4 font-data text-xs text-ink-dim">{p.prototype_id}</td>
                        <td className="py-2.5 pr-4 font-data text-ink-dim">{p.n_support_sequences}</td>
                        <td className="py-2.5 font-data text-ink">{p.purity}</td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </Card>

            <Card title="PLM scaling ablation" subtitle={scaling?.description} eyebrow="Baseline · untrained">
              <ResponsiveContainer width="100%" height={260}>
                <LineChart data={scaling?.results ?? []} margin={{ top: 10, right: 30, left: 0, bottom: 10 }}>
                  <CartesianGrid stroke={CHART_GRID} />
                  <XAxis dataKey="params" tick={CHART_TICK} axisLine={{ stroke: CHART_GRID }} tickLine={false} />
                  <YAxis domain={[0, 1]} tick={CHART_TICK} axisLine={{ stroke: CHART_GRID }} tickLine={false} />
                  <Tooltip contentStyle={tooltipContentStyle()} labelStyle={tooltipLabelStyle()} itemStyle={tooltipItemStyle()} />
                  <Legend wrapperStyle={CHART_LEGEND_STYLE} />
                  <Line type="monotone" dataKey="recall_at_10" name="Recall@10" stroke="rgb(var(--c-teal))" strokeWidth={2} dot={{ r: 3, fill: "rgb(var(--c-teal))" }} />
                  <Line type="monotone" dataKey="prototype_purity" name="Prototype purity" stroke="rgb(var(--c-lime))" strokeWidth={2} dot={{ r: 3, fill: "rgb(var(--c-lime))" }} />
                </LineChart>
              </ResponsiveContainer>
              <p className="mt-3 text-xs leading-relaxed text-ink-faint">
                Real ESM-2 embeddings at 4 scales (35M → 3B params), same real sequences, no fine-tuning — this is the
                HP5 scaling question the real trained model above hasn't yet answered (Step 6 in the build guide, not
                started: retraining the SupCon model itself at each scale).
              </p>
            </Card>

            <Card title="Retrieval demo (untrained baseline)" subtitle="Real cosine-similarity search over raw ESM-2 650M embeddings" eyebrow="Baseline · untrained">
              <div className="space-y-3">
                {retrieval.map((demo) => (
                  <div key={demo.query.peptide_id} className="rounded-lg border border-line bg-surface2/60 p-4">
                    <p className="text-sm text-ink">
                      Query <span className="font-data font-medium text-lime">{demo.query.sequence}</span>{" "}
                      <span className="text-ink-faint">({demo.query.mechanism_tier})</span>
                    </p>
                    <div className="mt-2.5 flex flex-wrap gap-2">
                      {demo.top_matches.slice(0, 6).map((m: any) => (
                        <span
                          key={m.rank}
                          className="rounded-md border px-2 py-1 font-data text-xs text-ink-dim"
                          style={{ borderColor: TIER_COLORS[m.mechanism_tier] }}
                          title={`${m.mechanism_tier} · sim ${m.similarity}`}
                        >
                          {m.sequence} <span className="text-ink-faint">{m.similarity}</span>
                        </span>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          </>
        )}
      </div>
    </div>
  );
}
