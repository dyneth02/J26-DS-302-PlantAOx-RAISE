import { ReactNode } from "react";
import { motion } from "framer-motion";
import { InfoTooltip } from "./Tooltip";

export default function StatCard({
  label,
  value,
  sub,
  accent = "lime",
  tooltip,
}: {
  label: string;
  value: string | number;
  sub?: string;
  accent?: "lime" | "teal" | "violet" | "amber";
  tooltip?: ReactNode;
}) {
  const glow = {
    lime: "group-hover:shadow-glow",
    teal: "group-hover:shadow-glow-teal",
    violet: "group-hover:shadow-glow-teal",
    amber: "group-hover:shadow-glow",
  }[accent];

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
      <p className="mt-1.5 font-display text-[1.75rem] font-medium leading-none tracking-tight text-ink">
        {value}
      </p>
      {sub && <p className="mt-1.5 text-xs text-ink-faint">{sub}</p>}
    </motion.div>
  );
}
