import { motion } from "framer-motion";

export default function PageHeader({ eyebrow, title, subtitle }: { eyebrow?: string; title: string; subtitle?: string }) {
  return (
    <div className="relative overflow-hidden border-b border-line px-10 pt-12 pb-10">
      <div
        className="pointer-events-none absolute -right-24 -top-24 h-72 w-72 rounded-full bg-teal/10 blur-3xl animate-drift"
        aria-hidden
      />
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1] }}
        className="relative"
      >
        {eyebrow && <p className="label-tag text-lime">{eyebrow}</p>}
        <h1 className="mt-2 font-display text-4xl font-medium tracking-tight text-ink">{title}</h1>
        {subtitle && <p className="mt-2.5 max-w-2xl text-[0.95rem] leading-relaxed text-ink-dim">{subtitle}</p>}
      </motion.div>
    </div>
  );
}
