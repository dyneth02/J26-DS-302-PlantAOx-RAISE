import { ReactNode } from "react";
import { motion } from "framer-motion";

const VARIANTS = {
  info: { border: "border-teal/25", bg: "bg-teal/[0.06]", tag: "text-teal", label: "NOTE" },
  warning: { border: "border-amber/30", bg: "bg-amber/[0.07]", tag: "text-amber", label: "ALERT" },
};

export default function Banner({
  title,
  children,
  variant = "info",
  label,
}: {
  title: string;
  children: ReactNode;
  variant?: "info" | "warning";
  label?: string;
}) {
  const v = VARIANTS[variant];
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className={`relative overflow-hidden rounded-xl border ${v.border} ${v.bg} py-4 pl-5 pr-4`}
    >
      <div className={`absolute left-0 top-0 h-full w-[3px] ${variant === "warning" ? "bg-amber" : "bg-teal"}`} />
      <p className={`label-tag ${v.tag}`}>{label ?? v.label}</p>
      <p className="mt-1.5 font-medium text-ink">{title}</p>
      <div className="mt-1 text-sm leading-relaxed text-ink-dim">{children}</div>
    </motion.div>
  );
}
