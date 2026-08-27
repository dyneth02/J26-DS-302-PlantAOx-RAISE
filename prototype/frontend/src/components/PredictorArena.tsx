import { useMemo, useState } from "react";
import { motion } from "framer-motion";
import { ArrowUpDown } from "lucide-react";
import { Radar, RadarChart, PolarGrid, PolarAngleAxis, PolarRadiusAxis, ResponsiveContainer, Legend } from "recharts";
import AnimatedStatCard from "./AnimatedStatCard";
import { FLAG_STYLES, CHART_LEGEND_STYLE } from "./chartTheme";

export interface PredictorArenaEntry {
  key: string;
  display_name: string;
  bcs: number;
  reliability_flag: string;
  invariance_rate: number;
  false_sensitivity_rate: number;
  redox_sensitivity_rate: number;
  random_substitution_sensitivity_rate: number;
}

const SERIES_COLORS = ["rgb(var(--c-lime))", "rgb(var(--c-teal))", "rgb(var(--c-coral))"];

export default function PredictorArena({ predictors }: { predictors: PredictorArenaEntry[] }) {
  const [ranked, setRanked] = useState(false);

  const ordered = useMemo(() => {
    if (!ranked) return predictors;
    return [...predictors].sort((a, b) => b.bcs - a.bcs);
  }, [predictors, ranked]);

  const radarData = [
    { axis: "IR", ...Object.fromEntries(predictors.map((p) => [p.key, p.invariance_rate])) },
    { axis: "1 − FSR", ...Object.fromEntries(predictors.map((p) => [p.key, 1 - p.false_sensitivity_rate])) },
    { axis: "Redox sens.", ...Object.fromEntries(predictors.map((p) => [p.key, p.redox_sensitivity_rate])) },
    { axis: "Random sens.", ...Object.fromEntries(predictors.map((p) => [p.key, p.random_substitution_sensitivity_rate])) },
  ];

  return (
    <div>
      <div className="mb-4 flex items-center justify-between">
        <p className="text-xs text-ink-faint">
          {predictors.length} real predictors, audited on identical perturbations — comparable head-to-head.
        </p>
        <button
          onClick={() => setRanked((v) => !v)}
          className="flex items-center gap-1.5 rounded-lg border border-line-strong bg-surface2 px-2.5 py-1.5 text-xs text-ink-dim transition-colors hover:border-lime/40 hover:text-ink"
        >
          <ArrowUpDown size={12} />
          {ranked ? "Unsorted" : "Rank by BCS"}
        </button>
      </div>

      <motion.div layout className="grid grid-cols-1 gap-4 md:grid-cols-2">
        {ordered.map((p, i) => (
          <motion.div key={p.key} layout transition={{ type: "spring", stiffness: 350, damping: 30 }} className="panel p-4">
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm font-medium text-ink">{p.display_name}</p>
              <span className={`shrink-0 rounded-full px-2.5 py-1 label-tag ${FLAG_STYLES[p.reliability_flag]}`}>
                {p.reliability_flag}
              </span>
            </div>
            <AnimatedStatCard
              label="BCS"
              value={p.bcs}
              decimals={4}
              accent={i === 0 && ranked ? "lime" : "teal"}
              tooltip="Behavioral Consistency Score = IR × (1 − FSR)."
            />
            <div className="mt-2 grid grid-cols-2 gap-2 text-xs text-ink-dim">
              <span>IR {p.invariance_rate.toFixed(3)}</span>
              <span>FSR {p.false_sensitivity_rate.toFixed(3)}</span>
            </div>
          </motion.div>
        ))}
      </motion.div>

      <div className="mt-4 panel p-3">
        <p className="label-tag mb-1 text-ink-faint">IR / FSR / sensitivity — head to head</p>
        <ResponsiveContainer width="100%" height={260}>
          <RadarChart data={radarData} outerRadius="70%">
            <PolarGrid stroke="var(--c-line)" />
            <PolarAngleAxis dataKey="axis" tick={{ fill: "rgb(var(--c-ink-dim))", fontSize: 11 }} />
            <PolarRadiusAxis domain={[0, 1]} tick={{ fill: "rgb(var(--c-ink-faint))", fontSize: 9 }} tickCount={4} />
            {predictors.map((p, i) => (
              <Radar
                key={p.key}
                name={p.display_name}
                dataKey={p.key}
                stroke={SERIES_COLORS[i % SERIES_COLORS.length]}
                fill={SERIES_COLORS[i % SERIES_COLORS.length]}
                fillOpacity={0.15}
                strokeWidth={2}
              />
            ))}
            <Legend wrapperStyle={CHART_LEGEND_STYLE} />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
