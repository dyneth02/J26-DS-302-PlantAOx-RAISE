import { motion } from "framer-motion";

export interface SegmentOption {
  value: string;
  label: string;
}

// Single-select stepper pills -- visually modeled on C1Page's existing tierToggleButtons
// pill styling, but single-select/stepper semantics (a shared layoutId highlight) instead
// of independent multi-toggle. New component, not a refactor of tierToggleButtons.
export default function SegmentedControl({
  options,
  value,
  onChange,
  layoutId,
}: {
  options: SegmentOption[];
  value: string;
  onChange: (value: string) => void;
  layoutId: string;
}) {
  return (
    <div className="flex flex-wrap items-center gap-1.5">
      {options.map((o) => {
        const active = o.value === value;
        return (
          <button
            key={o.value}
            onClick={() => onChange(o.value)}
            className={`label-tag relative rounded-full border px-2.5 py-1 transition-colors ${
              active ? "border-lime/40 text-lime" : "border-line-strong text-ink-faint hover:text-ink-dim"
            }`}
          >
            {active && (
              <motion.span
                layoutId={layoutId}
                className="absolute inset-0 rounded-full bg-lime/[0.08]"
                transition={{ type: "spring", stiffness: 400, damping: 32 }}
              />
            )}
            <span className="relative z-10">{o.label}</span>
          </button>
        );
      })}
    </div>
  );
}
