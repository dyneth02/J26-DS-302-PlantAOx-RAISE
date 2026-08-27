import { useEffect, useMemo, useState } from "react";
import { BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, ResponsiveContainer, Cell } from "recharts";
import { Loader2, Bookmark, X } from "lucide-react";
import { c2Api } from "../api/client";
import PageHeader from "../components/PageHeader";
import Card from "../components/Card";
import Banner from "../components/Banner";
import StatCard from "../components/StatCard";
import AnimatedStatCard from "../components/AnimatedStatCard";
import Modal from "../components/Modal";
import Skeleton from "../components/Skeleton";
import Section from "../components/Section";
import { usePresentationStore } from "../store/presentationStore";
import { useScenarioStore } from "../store/scenarioStore";
import CalibrationCurve, { type CalibrationBin } from "../components/CalibrationCurve";
import { CHART_GRID, CHART_TICK, tooltipContentStyle, tooltipItemStyle, tooltipLabelStyle } from "../components/chartTheme";
import type { ChallengePools, LiveRnisResult } from "../types/c2";

interface C2ScenarioState {
  pools: string[];
  mcc_easy: number;
  mcc_hard: number;
  rnis: number;
}

// Backend's live-rnis pool keys, mapped to the corresponding static "Challenge pools" entry
// and a short display label for the pool-builder chips.
const LIVE_POOLS = [
  { key: "easy", staticKey: "pool_c1_random_easy", label: "Easy (random decoys)" },
  { key: "peptipedia", staticKey: "pool_c2_non_aop_bioactive", label: "Peptipedia (moderate)" },
  { key: "hard", staticKey: "pool_c3_hard_descriptor_nearest", label: "Hard (descriptor-nearest)" },
] as const;

export default function C2Page() {
  const [summary, setSummary] = useState<any>(null);
  const [pools, setPools] = useState<ChallengePools | null>(null);
  const [rnis, setRnis] = useState<any>(null);
  const [calibration, setCalibration] = useState<any>(null);
  const [stageComparison, setStageComparison] = useState<any>(null);

  const [selectedPools, setSelectedPools] = useState<Set<string>>(new Set(["easy"]));
  const [liveResult, setLiveResult] = useState<LiveRnisResult | null>(null);
  const [liveLoading, setLiveLoading] = useState(false);
  const [liveError, setLiveError] = useState<string | null>(null);
  const [expandedPool, setExpandedPool] = useState<string | null>(null);
  const [liveCalibration, setLiveCalibration] = useState<{
    pools_selected: string[];
    selected_bins: CalibrationBin[];
    hard_bins: CalibrationBin[];
  } | null>(null);
  const safeMode = usePresentationStore((s) => s.safeMode);
  const resetSignal = usePresentationStore((s) => s.resetSignal);
  const allScenarios = useScenarioStore((s) => s.scenarios);
  const saveScenario = useScenarioStore((s) => s.save);
  const removeScenario = useScenarioStore((s) => s.remove);
  const scenarios = useMemo(() => allScenarios.filter((sc) => sc.page === "c2"), [allScenarios]);

  function handleSaveScenario() {
    if (!liveResult) return;
    const state = liveResult.pools_selected as string[];
    saveScenario("c2", state.join(" + ") || "(none)", {
      pools: state,
      mcc_easy: liveResult.mcc_easy,
      mcc_hard: liveResult.mcc_hard,
      rnis: liveResult.rnis,
    } satisfies C2ScenarioState);
  }

  function loadScenario(pools: string[]) {
    setSelectedPools(new Set(pools));
  }

  useEffect(() => {
    c2Api.summary().then(setSummary);
    c2Api.pools().then(setPools);
    c2Api.rnis().then(setRnis);
    c2Api.calibration().then(setCalibration);
    c2Api.stageComparison().then(setStageComparison);
  }, []);

  useEffect(() => {
    if (resetSignal === 0) return;
    setSelectedPools(new Set(["easy"]));
    setExpandedPool(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resetSignal]);

  useEffect(() => {
    if (safeMode || selectedPools.size === 0) {
      setLiveResult(null);
      setLiveError(null);
      return;
    }
    let cancelled = false;
    setLiveLoading(true);
    setLiveError(null);
    c2Api
      .liveRnis(Array.from(selectedPools))
      .then((data) => {
        if (!cancelled) setLiveResult(data);
      })
      .catch((e) => {
        if (!cancelled) {
          setLiveError(e?.response?.data?.detail ?? "Live recompute failed.");
          setLiveResult(null);
        }
      })
      .finally(() => {
        if (!cancelled) setLiveLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [selectedPools, safeMode]);

  useEffect(() => {
    if (safeMode || selectedPools.size === 0) {
      setLiveCalibration(null);
      return;
    }
    let cancelled = false;
    c2Api.liveCalibration(Array.from(selectedPools)).then((data) => {
      if (!cancelled) setLiveCalibration(data);
    });
    return () => {
      cancelled = true;
    };
  }, [selectedPools, safeMode]);

  function togglePool(key: string) {
    setSelectedPools((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  const chartData = stageComparison?.series ?? [];
  const expandedPoolData = expandedPool && pools ? pools[expandedPool] : null;

  return (
    <div>
      <PageHeader
        eyebrow="Component 2"
        title="PU-AOP"
        subtitle="Evidence-Tiered PU Learning and Random-Negative Inflation Scoring (RNIS)"
      />
      <div className="space-y-6 p-8">
        <Section
          id="c2-overview"
          label="Overview"
          notes="The key insight here is RNIS: performance measured against easy synthetic negatives is misleadingly high. Lead with the MCC-easy vs MCC-hard gap before showing RNIS itself."
        >
        {summary && <Banner title="Real positives, real hard negatives, synthetic easy negatives">{summary.notes?.join(" ")}</Banner>}

        {rnis ? (
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatCard
              label="MCC — easy negatives"
              value={rnis.mcc_c1_easy}
              accent="teal"
              tooltip="Matthews Correlation Coefficient when evaluated against synthetic, randomly-composed easy negatives — the way most published AOP predictors are benchmarked."
            />
            <StatCard
              label="MCC — hard negatives"
              value={rnis.mcc_c3_hard}
              accent="amber"
              tooltip="Same classifier, same metric, but evaluated against real non-AOP bioactive peptides selected to be descriptor-nearest to the positives — a much harder, more realistic negative set."
            />
            <StatCard
              label="RNIS"
              value={rnis.rnis}
              sub="MCC_easy − MCC_hard"
              tooltip="Random-Negative Inflation Score: how much of the classifier's apparent performance evaporates once evaluated on hard negatives instead of easy ones. Near zero = little inflation."
            />
            <StatCard label="Classifier" value="Logistic Regression" sub="14 descriptor features" />
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            {Array.from({ length: 4 }).map((_, i) => (
              <Skeleton key={i} className="h-[4.75rem]" />
            ))}
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
        </Section>

        <Section
          id="c2-pools"
          label="Negative pools & live RNIS"
          notes="Ask the panel which pool combination they'd like to try — a fresh LogisticRegression genuinely retrains server-side on whatever they pick. Point out that selecting 'hard' alone makes MCC_easy == MCC_hard by construction — a good moment to explain why."
        >
        <Card title="Challenge pools" subtitle="Click a row for detail" eyebrow="Negative sampling">
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
                  Object.entries(pools).map(([key, p]) => (
                    <tr
                      key={key}
                      onClick={() => setExpandedPool(key)}
                      className="cursor-pointer border-b border-line transition-colors last:border-0 hover:bg-surface2/50"
                    >
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

        <Card
          title="Try it yourself: live RNIS"
          subtitle="Pick any combination of negative pools — a fresh classifier is trained and evaluated on demand"
          eyebrow="Live · real recompute"
        >
          {safeMode && (
            <p className="text-sm text-ink-faint">
              Safe mode is on — live recompute against the backend is disabled. Turn off safe mode in the toolbar below to try it.
            </p>
          )}

          <div className={`flex flex-wrap gap-1.5 ${safeMode ? "mt-4 opacity-40 pointer-events-none" : ""}`}>
            {LIVE_POOLS.map(({ key, label }) => {
              const active = selectedPools.has(key);
              return (
                <button
                  key={key}
                  onClick={() => togglePool(key)}
                  className="label-tag rounded-full border px-2.5 py-1 transition-colors"
                  style={{
                    borderColor: active ? "rgb(var(--c-lime) / 0.4)" : "var(--c-line-strong)",
                    color: active ? "rgb(var(--c-lime))" : "rgb(var(--c-ink-faint))",
                  }}
                >
                  {label}
                </button>
              );
            })}
          </div>

          {!safeMode && selectedPools.size === 0 && (
            <p className="mt-4 text-sm text-ink-faint">Select at least one pool to train and evaluate a live classifier.</p>
          )}

          {!safeMode && liveError && <p className="mt-4 text-sm text-coral">{liveError}</p>}

          {liveLoading && !liveResult && (
            <div className="mt-4 flex items-center gap-2 text-sm text-ink-faint">
              <Loader2 size={14} className="animate-spin" /> Training on positives + {Array.from(selectedPools).join(", ")}…
            </div>
          )}

          {liveResult && !liveError && (
            <div className="relative mt-4">
              <div className={`grid grid-cols-1 gap-3 transition-opacity md:grid-cols-3 ${liveLoading ? "opacity-50" : ""}`}>
                <AnimatedStatCard
                  key={`easy-${liveResult.pools_selected.join(",")}`}
                  label="MCC — easy negatives"
                  value={liveResult.mcc_easy}
                  decimals={4}
                  accent="teal"
                />
                <AnimatedStatCard
                  key={`hard-${liveResult.pools_selected.join(",")}`}
                  label="MCC — hard negatives"
                  value={liveResult.mcc_hard}
                  decimals={4}
                  accent="amber"
                />
                <AnimatedStatCard key={`rnis-${liveResult.pools_selected.join(",")}`} label="RNIS" value={liveResult.rnis} decimals={4} />
              </div>
              <p className="mt-3 text-xs leading-relaxed text-ink-faint">
                Trained on {liveResult.n_train} positives + selected-pool examples ({liveResult.pools_selected.join(", ")}).{" "}
                {liveResult.interpretation}
              </p>
              <button
                onClick={handleSaveScenario}
                className="mt-3 flex items-center gap-1.5 rounded-lg border border-line-strong bg-surface2 px-2.5 py-1.5 text-xs text-ink-dim transition-colors hover:border-lime/40 hover:text-ink"
              >
                <Bookmark size={12} />
                Save this combination
              </button>
            </div>
          )}
        </Card>

        {scenarios.length > 0 && (
          <Card
            title="Saved scenarios"
            subtitle="Pool combinations saved for side-by-side comparison"
            eyebrow="Compare"
          >
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b border-line text-left text-ink-faint">
                    <th className="py-2 pr-4 label-tag font-normal">Pools</th>
                    <th className="py-2 pr-4 label-tag font-normal">MCC easy</th>
                    <th className="py-2 pr-4 label-tag font-normal">MCC hard</th>
                    <th className="py-2 pr-4 label-tag font-normal">RNIS</th>
                    <th className="py-2 label-tag font-normal"></th>
                  </tr>
                </thead>
                <tbody>
                  {scenarios.map((sc) => {
                    const state = sc.state as unknown as C2ScenarioState;
                    return (
                      <tr key={sc.id} className="border-b border-line last:border-0 font-data text-xs text-ink-dim">
                        <td className="py-2 pr-4">
                          <button onClick={() => loadScenario(state.pools)} className="text-teal hover:underline">
                            {sc.label}
                          </button>
                        </td>
                        <td className="py-2 pr-4">{state.mcc_easy.toFixed(4)}</td>
                        <td className="py-2 pr-4">{state.mcc_hard.toFixed(4)}</td>
                        <td className="py-2 pr-4">{state.rnis.toFixed(4)}</td>
                        <td className="py-2">
                          <button onClick={() => removeScenario(sc.id)} aria-label="Remove scenario" className="text-ink-faint hover:text-coral">
                            <X size={13} />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </Card>
        )}
        </Section>

        <Section
          id="c2-calibration"
          label="Calibration"
          notes="Explain the diagonal: points that sit on it mean the model's stated confidence matches its real accuracy. Points below the diagonal are over-confident — flag if the hard pool sits systematically below the easy pool."
        >
        <Card
          title="Calibration"
          subtitle="Reliability diagram — how well predicted probability matches observed accuracy, for the pool combination selected above"
          eyebrow="Confidence"
        >
          {safeMode ? (
            <p className="text-sm text-ink-faint">Safe mode is on — showing the static ECE/Brier table below only.</p>
          ) : liveCalibration ? (
            <CalibrationCurve
              selectedBins={liveCalibration.selected_bins}
              hardBins={liveCalibration.hard_bins}
              selectedLabel={liveCalibration.pools_selected.join(" + ")}
            />
          ) : (
            <Skeleton className="h-[300px]" />
          )}
          <p className="mt-3 text-xs text-ink-faint">
            Dot size = number of test examples in that confidence bin. Points on the dashed diagonal are perfectly calibrated; above it
            the model is under-confident, below it over-confident.
          </p>
          <table className="mt-5 w-full text-sm">
            <thead>
              <tr className="border-b border-line text-left text-ink-faint">
                <th className="py-2 pr-4 label-tag font-normal">Pool (static baseline)</th>
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
        </Section>
      </div>

      <Modal open={!!expandedPool} onClose={() => setExpandedPool(null)} title={expandedPool ?? undefined}>
        {expandedPoolData && (
          <div className="space-y-3 text-sm">
            <div>
              <p className="label-tag text-ink-faint">Size</p>
              <p className="mt-0.5 font-data text-ink">{expandedPoolData.size} sequences</p>
            </div>
            <div>
              <p className="label-tag text-ink-faint">Source</p>
              <p className="mt-0.5 text-ink-dim">{expandedPoolData.source}</p>
            </div>
            <div>
              <p className="label-tag text-ink-faint">Purpose</p>
              <p className="mt-0.5 text-ink-dim">{expandedPoolData.purpose}</p>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
