import { useState } from "react";
import { motion } from "framer-motion";
import { BarChart, Bar, XAxis, YAxis, Cell, ResponsiveContainer, CartesianGrid } from "recharts";
import { CHART_GRID, CHART_TICK } from "./chartTheme";

export interface PerturbationTab {
  type: string;
  shortLabel: string;
  sequence: string;
  score: number;
  delta: number;
}

const TAB_COLORS = ["rgb(var(--c-lime))", "rgb(var(--c-teal))", "rgb(var(--c-coral))"];

function DiffSequence({ original, mutated }: { original: string; mutated: string }) {
  const chars = mutated.split("").map((ch, i) => ({ ch, changed: original[i] !== ch }));
  return (
    <p className="font-data text-sm leading-relaxed">
      {chars.map((c, i) => (
        <span
          key={i}
          className={c.changed ? "rounded bg-amber/20 px-0.5 text-amber font-medium" : "text-ink"}
          title={c.changed ? `position ${i + 1}: ${original[i]} → ${c.ch}` : undefined}
        >
          {c.ch}
        </span>
      ))}
    </p>
  );
}

// Doc's "sensitivity meter": how far this perturbation pushed the score, as a
// fraction of the widest delta seen across the three types.
function SensitivityMeter({ delta, maxAbsDelta }: { delta: number; maxAbsDelta: number }) {
  const pct = maxAbsDelta > 0 ? Math.min(Math.abs(delta) / maxAbsDelta, 1) : 0;
  const color = delta < 0 ? "rgb(var(--c-coral))" : "rgb(var(--c-lime))";
  return (
    <div>
      <div className="flex items-center justify-between">
        <p className="label-tag text-ink-faint">Sensitivity</p>
        <p className="font-data text-xs text-ink-dim">Δ {delta.toFixed(4)}</p>
      </div>
      <div className="mt-1.5 h-2 w-full overflow-hidden rounded-full bg-surface2">
        <motion.div
          className="h-full rounded-full"
          style={{ backgroundColor: color }}
          initial={{ width: 0 }}
          animate={{ width: `${pct * 100}%` }}
          transition={{ duration: 0.4, ease: "easeOut" }}
        />
      </div>
    </div>
  );
}

export default function PerturbationTypeExplorer({
  original,
  originalScore,
  tabs,
}: {
  original: string;
  originalScore: number;
  tabs: PerturbationTab[];
}) {
  const [active, setActive] = useState(0);
  const activeTab = tabs[active];
  const maxAbsDelta = Math.max(...tabs.map((t) => Math.abs(t.delta)), 1e-6);

  const chartData = tabs.map((t) => ({ name: t.shortLabel, delta: t.delta }));

  return (
    <div>
      <div className="flex flex-wrap gap-1.5">
        {tabs.map((t, i) => (
          <button
            key={t.type}
            onClick={() => setActive(i)}
            className="label-tag rounded-full border px-2.5 py-1 transition-colors"
            style={{
              borderColor: active === i ? `${TAB_COLORS[i % 3]}66` : "var(--c-line-strong)",
              color: active === i ? TAB_COLORS[i % 3] : "rgb(var(--c-ink-faint))",
            }}
          >
            {t.shortLabel}
          </button>
        ))}
      </div>

      <div className="mt-4 grid grid-cols-1 gap-5 lg:grid-cols-[minmax(0,1.3fr)_minmax(0,1fr)]">
        <motion.div key={active} initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.22 }}>
          <p className="label-tag text-ink-faint">Original</p>
          <p className="font-data text-sm text-ink-dim">
            {original} <span className="text-ink-faint">(score {originalScore.toFixed(4)})</span>
          </p>
          <p className="mt-3 label-tag" style={{ color: TAB_COLORS[active % 3] }}>
            {activeTab.type}
          </p>
          <DiffSequence original={original} mutated={activeTab.sequence} />
          <p className="mt-2 text-xs text-ink-faint">
            score {activeTab.score.toFixed(4)} · amber highlight marks the mutated residue(s)
          </p>
          <div className="mt-4">
            <SensitivityMeter delta={activeTab.delta} maxAbsDelta={maxAbsDelta} />
          </div>
        </motion.div>

        <div className="panel p-3">
          <p className="label-tag mb-1 text-ink-faint">Δ score by perturbation type</p>
          <ResponsiveContainer width="100%" height={140}>
            <BarChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid stroke={CHART_GRID} vertical={false} />
              <XAxis dataKey="name" tick={{ ...CHART_TICK, fontSize: 10 }} axisLine={{ stroke: CHART_GRID }} tickLine={false} />
              <YAxis tick={{ ...CHART_TICK, fontSize: 10 }} axisLine={{ stroke: CHART_GRID }} tickLine={false} width={36} />
              <Bar dataKey="delta" radius={[4, 4, 4, 4]} isAnimationActive={false}>
                {chartData.map((_, i) => (
                  <Cell key={i} fill={TAB_COLORS[i % 3]} fillOpacity={i === active ? 1 : 0.3} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
}
