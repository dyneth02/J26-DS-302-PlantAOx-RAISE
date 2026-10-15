import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { Play, Pause } from "lucide-react";

export interface WalkthroughStep {
  label: string;
  color: string; // CSS color for the step pill + diagram accent
  title: string;
  body: React.ReactNode;
}

const STEP_DURATION_MS = 3200;

// Sequence -> vector morph: a few letters resolve into a row of dots.
function SequenceToVectorDiagram({ color }: { color: string }) {
  const letters = ["A", "H", "K", "L", "W"];
  return (
    <svg viewBox="0 0 260 90" className="h-full w-full">
      {letters.map((ch, i) => (
        <g key={ch}>
          <motion.text
            x={20 + i * 24}
            y={30}
            fontSize="14"
            fontFamily="IBM Plex Mono"
            fill="rgb(var(--c-ink-dim))"
            textAnchor="middle"
            initial={{ opacity: 1 }}
            animate={{ opacity: [1, 1, 0] }}
            transition={{ duration: 2, times: [0, 0.4, 1], repeat: Infinity, repeatDelay: 1.2 }}
          >
            {ch}
          </motion.text>
          <motion.circle
            cx={20 + i * 24}
            cy={65}
            r={5}
            fill={color}
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: [0, 0, 1], y: [-10, -10, 0] }}
            transition={{ duration: 2, times: [0, 0.4, 1], repeat: Infinity, repeatDelay: 1.2 }}
          />
        </g>
      ))}
      <motion.path
        d="M 15 45 L 145 45"
        stroke="rgb(var(--c-ink-faint))"
        strokeWidth="1"
        strokeDasharray="3 3"
        initial={{ opacity: 0 }}
        animate={{ opacity: [0, 0.6, 0.6, 0] }}
        transition={{ duration: 2, times: [0, 0.3, 0.7, 1], repeat: Infinity, repeatDelay: 1.2 }}
      />
      <text x="200" y="34" fontSize="10" fill="rgb(var(--c-ink-faint))" className="label-tag">
        sequence
      </text>
      <text x="200" y="69" fontSize="10" fill="rgb(var(--c-ink-faint))" className="label-tag">
        fingerprint
      </text>
    </svg>
  );
}

// Contrastive pulling: two same-mechanism dots drift together, a third (different
// mechanism) drifts away.
function ContrastivePullDiagram({ color }: { color: string }) {
  return (
    <svg viewBox="0 0 260 90" className="h-full w-full">
      <motion.circle
        r={7}
        fill={color}
        initial={{ cx: 60, cy: 25 }}
        animate={{ cx: [60, 100], cy: [25, 45] }}
        transition={{ duration: 1.8, repeat: Infinity, repeatType: "reverse", ease: "easeInOut" }}
      />
      <motion.circle
        r={7}
        fill={color}
        initial={{ cx: 150, cy: 65 }}
        animate={{ cx: [150, 110], cy: [65, 45] }}
        transition={{ duration: 1.8, repeat: Infinity, repeatType: "reverse", ease: "easeInOut" }}
      />
      <motion.circle
        r={7}
        fill="rgb(var(--c-coral))"
        initial={{ cx: 210, cy: 45 }}
        animate={{ cx: [210, 235] }}
        transition={{ duration: 1.8, repeat: Infinity, repeatType: "reverse", ease: "easeInOut" }}
      />
      <text x="55" y="14" fontSize="9" fill="rgb(var(--c-ink-faint))" className="label-tag">
        same mechanism
      </text>
      <text x="200" y="80" fontSize="9" fill="rgb(var(--c-ink-faint))" className="label-tag">
        different
      </text>
    </svg>
  );
}

// Retrieval: a query dot lights up its nearest neighbours in a small cluster.
function RetrievalDiagram({ color }: { color: string }) {
  const neighbours = [
    { x: 190, y: 25 },
    { x: 205, y: 55 },
    { x: 175, y: 65 },
  ];
  const far = [
    { x: 60, y: 20 },
    { x: 45, y: 68 },
  ];
  return (
    <svg viewBox="0 0 260 90" className="h-full w-full">
      {far.map((p, i) => (
        <circle key={`far-${i}`} cx={p.x} cy={p.y} r={5} fill="rgb(var(--c-ink-faint))" opacity={0.4} />
      ))}
      {neighbours.map((p, i) => (
        <motion.line
          key={`line-${i}`}
          x1={130}
          y1={45}
          x2={p.x}
          y2={p.y}
          stroke={color}
          strokeWidth="1.5"
          initial={{ pathLength: 0, opacity: 0 }}
          animate={{ pathLength: [0, 1], opacity: [0, 1] }}
          transition={{ duration: 1, delay: 0.3 + i * 0.25, repeat: Infinity, repeatDelay: 1.6 }}
        />
      ))}
      {neighbours.map((p, i) => (
        <motion.circle
          key={`n-${i}`}
          cx={p.x}
          cy={p.y}
          r={6}
          fill={color}
          initial={{ opacity: 0.3 }}
          animate={{ opacity: [0.3, 1] }}
          transition={{ duration: 0.5, delay: 0.3 + i * 0.25, repeat: Infinity, repeatDelay: 1.6 + 1 }}
        />
      ))}
      <motion.circle
        cx={130}
        cy={45}
        r={8}
        fill="none"
        stroke={color}
        strokeWidth="2"
        animate={{ scale: [1, 1.4, 1] }}
        transition={{ duration: 1.6, repeat: Infinity }}
        style={{ transformOrigin: "130px 45px" }}
      />
      <circle cx={130} cy={45} r={5} fill="rgb(var(--c-ink))" />
      <text x="108" y="20" fontSize="9" fill="rgb(var(--c-ink-faint))" className="label-tag">
        query
      </text>
    </svg>
  );
}

const DIAGRAMS = [SequenceToVectorDiagram, ContrastivePullDiagram, RetrievalDiagram];

export default function WalkthroughStepper({ steps }: { steps: WalkthroughStep[] }) {
  const [active, setActive] = useState(0);
  const [playing, setPlaying] = useState(false);

  useEffect(() => {
    if (!playing) return;
    const id = setInterval(() => {
      setActive((i) => (i + 1) % steps.length);
    }, STEP_DURATION_MS);
    return () => clearInterval(id);
  }, [playing, steps.length]);

  const Diagram = DIAGRAMS[active] ?? DIAGRAMS[0];
  const step = steps[active];

  return (
    <div>
      <div className="flex flex-wrap items-center gap-1.5">
        {steps.map((s, i) => (
          <button
            key={s.label}
            onClick={() => {
              setActive(i);
              setPlaying(false);
            }}
            className="label-tag relative rounded-full border px-2.5 py-1 transition-colors"
            style={{
              borderColor: active === i ? `${s.color}66` : "var(--c-line-strong)",
              color: active === i ? s.color : "rgb(var(--c-ink-faint))",
            }}
          >
            {s.label}
          </button>
        ))}
        <button
          onClick={() => setPlaying((v) => !v)}
          className="ml-auto flex items-center gap-1.5 rounded-full border border-line-strong px-2.5 py-1 text-xs font-medium text-ink-dim transition-colors hover:bg-surface2/60"
        >
          {playing ? <Pause size={12} /> : <Play size={12} />}
          {playing ? "Pause" : "Play all"}
        </button>
      </div>

      <div className="mt-4 grid grid-cols-1 gap-5 md:grid-cols-[minmax(0,1fr)_minmax(0,1fr)]">
        <div className="panel flex h-32 items-center justify-center p-3">
          <Diagram color={step.color} />
        </div>
        <motion.div
          key={active}
          initial={{ opacity: 0, y: 6 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.25 }}
          className="panel p-4"
        >
          <p className="label-tag" style={{ color: step.color }}>
            {step.title}
          </p>
          <div className="mt-2 text-sm leading-relaxed text-ink">{step.body}</div>
        </motion.div>
      </div>
    </div>
  );
}
