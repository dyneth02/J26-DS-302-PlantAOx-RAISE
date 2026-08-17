import { ReactNode } from "react";
import { motion } from "framer-motion";

export default function Card({
  title,
  subtitle,
  children,
  eyebrow,
  actions,
}: {
  title: string;
  subtitle?: string;
  children: ReactNode;
  eyebrow?: string;
  actions?: ReactNode;
}) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 14 }}
      whileInView={{ opacity: 1, y: 0 }}
      viewport={{ once: true, margin: "-40px" }}
      transition={{ duration: 0.45, ease: [0.16, 1, 0.3, 1] }}
      className="panel p-6"
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          {eyebrow && <p className="label-tag mb-2 text-teal">{eyebrow}</p>}
          <h2 className="font-display text-xl font-medium tracking-tight text-ink">{title}</h2>
          {subtitle && <p className="mt-1 text-sm text-ink-dim">{subtitle}</p>}
        </div>
        {actions && <div className="flex shrink-0 items-center gap-2">{actions}</div>}
      </div>
      <div className="mt-5">{children}</div>
    </motion.div>
  );
}
