import { ReactNode, useEffect, useRef, useState } from "react";
import { motion } from "framer-motion";
import { InfoTooltip } from "./Tooltip";

// Drop-in variant of StatCard.tsx with the same props, but numeric `value` counts up on
// change/mount. A new file rather than an edit to StatCard.tsx, since 4 pages already
// depend on that one rendering statically.
//
// Uses a small self-contained requestAnimationFrame loop rather than react-countup:
// react-countup (both the declarative <CountUp> component and the imperative
// useCountUp hook) reliably got stuck rendering a stale/zero value in this app under
// React 18 StrictMode's dev-only double-invoke of effects -- easing function below is
// the same one Card.tsx/PageHeader.tsx already use elsewhere ([0.16, 1, 0.3, 1]-style
// ease-out feel), just implemented directly so the displayed number can never be wrong.
function useCountUpValue(target: number, durationMs: number) {
  const [display, setDisplay] = useState(target);
  // Tracks the value actually on screen, kept in sync every render (not just at animation
  // completion) -- so if an animation gets interrupted by a new target mid-flight, the next
  // one starts from where the number visually is now, instead of snapping back to whatever
  // stale value a previous run's completion branch last wrote.
  const displayRef = useRef(target);
  useEffect(() => {
    displayRef.current = display;
  });

  useEffect(() => {
    const from = displayRef.current;
    const to = target;
    if (from === to) return;
    let raf = 0;
    const start = performance.now();
    const tick = (now: number) => {
      const t = Math.min((now - start) / durationMs, 1);
      const eased = 1 - Math.pow(1 - t, 3); // ease-out cubic
      const next = from + (to - from) * eased;
      displayRef.current = next;
      setDisplay(next);
      if (t < 1) raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [target, durationMs]);

  return display;
}

export default function AnimatedStatCard({
  label,
  value,
  decimals = 0,
  suffix = "",
  prefix = "",
  sub,
  accent = "lime",
  durationSeconds = 0.7,
  tooltip,
}: {
  label: string;
  value: number;
  decimals?: number;
  suffix?: string;
  prefix?: string;
  sub?: string;
  accent?: "lime" | "teal" | "violet" | "amber";
  durationSeconds?: number;
  tooltip?: ReactNode;
}) {
  const glow = {
    lime: "group-hover:shadow-glow",
    teal: "group-hover:shadow-glow-teal",
    violet: "group-hover:shadow-glow-teal",
    amber: "group-hover:shadow-glow",
  }[accent];

  const display = useCountUpValue(value, durationSeconds * 1000);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={`group panel p-4 transition-shadow duration-300 ${glow}`}
    >
      <p className="label-tag flex items-center gap-1.5 text-ink-faint">
        {label}
        {tooltip && <InfoTooltip content={tooltip} />}
      </p>
      <p className="mt-1.5 font-display text-[1.75rem] font-medium leading-none tracking-tight text-ink font-data">
        {prefix}{display.toFixed(decimals)}{suffix}
      </p>
      {sub && <p className="mt-1.5 text-xs text-ink-faint">{sub}</p>}
    </motion.div>
  );
}
