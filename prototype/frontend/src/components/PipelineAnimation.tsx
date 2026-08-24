import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Play, Pause } from "lucide-react";

export interface PipelineStage {
  label: string;
  detail: string;
}

const STAGE_MS = 1400;

export default function PipelineAnimation({ stages }: { stages: PipelineStage[] }) {
  const [active, setActive] = useState<number | null>(null);
  const [playing, setPlaying] = useState(false);
  const [dotIndex, setDotIndex] = useState(0);

  useEffect(() => {
    if (!playing) return;
    const id = setInterval(() => {
      setDotIndex((i) => {
        const next = i + 1;
        if (next >= stages.length) {
          setPlaying(false);
          return 0;
        }
        return next;
      });
    }, STAGE_MS);
    return () => clearInterval(id);
  }, [playing, stages.length]);

  const selected = active !== null ? stages[active] : null;

  return (
    <div>
      <div className="flex items-center justify-between">
        <p className="text-xs text-ink-faint">Click a stage for detail, or watch a candidate move through the pipeline.</p>
        <button
          onClick={() => {
            setDotIndex(0);
            setPlaying((v) => !v);
          }}
          className="flex items-center gap-1.5 rounded-full border border-line-strong px-2.5 py-1 text-xs font-medium text-ink-dim transition-colors hover:bg-surface2/60"
        >
          {playing ? <Pause size={12} /> : <Play size={12} />}
          {playing ? "Pause" : "Play pipeline"}
        </button>
      </div>

      <div className="relative mt-6 flex items-center justify-between">
        <div className="absolute left-0 right-0 top-4 h-px bg-line-strong" />
        {playing && (
          <motion.div
            className="absolute top-4 h-2.5 w-2.5 -translate-y-1/2 rounded-full bg-lime shadow-glow"
            animate={{ left: `calc(${(dotIndex / (stages.length - 1)) * 100}% - 5px)` }}
            transition={{ duration: STAGE_MS / 1000, ease: "linear" }}
          />
        )}
        {stages.map((s, i) => (
          <button
            key={s.label}
            onClick={() => setActive(active === i ? null : i)}
            className="relative z-10 flex flex-col items-center gap-2"
          >
            <span
              className="flex h-8 w-8 items-center justify-center rounded-full border-2 font-data text-xs transition-colors"
              style={{
                borderColor: active === i ? "rgb(var(--c-lime))" : "var(--c-line-strong)",
                background: active === i ? "rgb(var(--c-lime) / 0.1)" : "rgb(var(--c-void))",
                color: active === i ? "rgb(var(--c-lime))" : "rgb(var(--c-ink-faint))",
              }}
            >
              {i + 1}
            </span>
            <span className="label-tag max-w-[6.5rem] text-center text-ink-faint">{s.label}</span>
          </button>
        ))}
      </div>

      {selected && (
        <motion.div
          key={active}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="mt-4"
        >
          <div className="panel p-4">
            <p className="label-tag text-lime">{selected.label}</p>
            <p className="mt-1.5 text-sm leading-relaxed text-ink-dim">{selected.detail}</p>
          </div>
        </motion.div>
      )}
    </div>
  );
}
