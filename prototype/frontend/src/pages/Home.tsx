import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { motion, type Variants } from "framer-motion";
import { getProjectMeta } from "../api/client";
import Card from "../components/Card";
import Banner from "../components/Banner";

const ACCENTS: Record<string, { text: string; ring: string; dot: string }> = {
  C1: { text: "text-teal", ring: "hover:ring-teal/30 hover:shadow-glow-teal", dot: "bg-teal" },
  C2: { text: "text-amber", ring: "hover:ring-amber/30 hover:shadow-glow", dot: "bg-amber" },
  C3: { text: "text-violet", ring: "hover:ring-violet/30 hover:shadow-glow-teal", dot: "bg-violet" },
  C4: { text: "text-lime", ring: "hover:ring-lime/30 hover:shadow-glow", dot: "bg-lime" },
};

const stagger: Variants = {
  hidden: {},
  show: { transition: { staggerChildren: 0.08 } },
};
const rise: Variants = {
  hidden: { opacity: 0, y: 16 },
  show: { opacity: 1, y: 0, transition: { duration: 0.5, ease: [0.16, 1, 0.3, 1] } },
};

export default function Home() {
  const [meta, setMeta] = useState<any>(null);

  useEffect(() => {
    getProjectMeta().then(setMeta).catch(() => setMeta(null));
  }, []);

  if (!meta) {
    return <div className="p-10 font-data text-sm text-ink-faint">loading project overview…</div>;
  }

  return (
    <div>
      {/* Hero */}
      <div className="relative overflow-hidden border-b border-line px-10 pb-16 pt-16">
        <div className="pointer-events-none absolute -left-32 -top-40 h-96 w-96 rounded-full bg-lime/10 blur-3xl animate-drift" aria-hidden />
        <div className="pointer-events-none absolute -right-24 top-10 h-80 w-80 rounded-full bg-teal/10 blur-3xl animate-drift2" aria-hidden />

        <motion.div initial="hidden" animate="show" variants={stagger} className="relative max-w-3xl">
          <motion.p variants={rise} className="label-tag text-lime">
            Undergraduate Research Project · Proposal Prototype
          </motion.p>
          <motion.h1 variants={rise} className="mt-4 font-display text-6xl font-medium leading-[1.02] tracking-tight text-ink">
            PlantAOx<span className="text-lime">·</span>RAISE
          </motion.h1>
          <motion.p variants={rise} className="mt-5 max-w-xl text-lg leading-relaxed text-ink-dim">
            {meta.full_name}
          </motion.p>
        </motion.div>
      </div>

      <div className="space-y-8 p-10">
        <Banner title="Prototype scope">{meta.prototype_disclaimer}</Banner>

        <Card title="Problem statement" eyebrow="Motivation">
          <p className="text-[0.95rem] leading-relaxed text-ink-dim">{meta.problem_statement}</p>
        </Card>

        <div>
          <div className="mb-4 flex items-baseline justify-between">
            <h2 className="font-display text-2xl font-medium tracking-tight text-ink">Four reliability components</h2>
            <p className="label-tag text-ink-faint">one novelty claim each</p>
          </div>
          <motion.div
            initial="hidden"
            whileInView="show"
            viewport={{ once: true, margin: "-60px" }}
            variants={stagger}
            className="grid grid-cols-1 gap-4 md:grid-cols-2"
          >
            {meta.components.map((c: any) => {
              const a = ACCENTS[c.id] ?? ACCENTS.C1;
              return (
                <motion.div key={c.id} variants={rise}>
                  <Link
                    to={c.route}
                    className={`panel group block p-6 ring-1 ring-transparent transition-all duration-300 ${a.ring}`}
                  >
                    <div className="flex items-center gap-2.5">
                      <span className={`h-1.5 w-1.5 rounded-full ${a.dot}`} />
                      <span className={`label-tag ${a.text}`}>{c.id}</span>
                      <span className="font-display text-lg font-medium text-ink">{c.name}</span>
                    </div>
                    <p className="mt-3 text-sm leading-relaxed text-ink-dim">{c.title}</p>
                    <p className="mt-3 text-xs leading-relaxed text-ink-faint">
                      <span className="font-medium text-ink-dim">Novelty — </span>
                      {c.novelty}
                    </p>
                    <p className="mt-4 font-data text-xs text-ink-faint opacity-0 transition-opacity group-hover:opacity-100">
                      view dashboard →
                    </p>
                  </Link>
                </motion.div>
              );
            })}
          </motion.div>
        </div>

        <Card title="Component ownership" eyebrow="Team">
          <div className="divide-y divide-line">
            {meta.team_ownership.map((row: any, i: number) => (
              <div key={row.component} className="flex items-center gap-4 py-3 first:pt-0 last:pb-0">
                <span className="label-tag w-8 shrink-0 text-ink-faint">0{i + 1}</span>
                <span className="w-48 shrink-0 font-medium text-ink">{row.component}</span>
                <span className="text-sm text-ink-dim">{row.responsibility}</span>
              </div>
            ))}
          </div>
        </Card>

        <Card title="Architecture" subtitle="Presentation → reliability metrics → four components → shared curation & feature layer" eyebrow="System">
          <div className="grid grid-cols-1 gap-3 md:grid-cols-4">
            {meta.components.map((c: any, i: number) => {
              const a = ACCENTS[c.id] ?? ACCENTS.C1;
              return (
                <div key={c.id} className="relative">
                  <div className="rounded-lg border border-line-strong bg-surface2 py-4 text-center">
                    <span className={`label-tag ${a.text}`}>{c.id}</span>
                    <p className="mt-1 text-sm font-medium text-ink">{c.name}</p>
                  </div>
                  {i < 3 && (
                    <span className="absolute right-[-14px] top-1/2 hidden -translate-y-1/2 font-data text-ink-faint md:block">
                      →
                    </span>
                  )}
                </div>
              );
            })}
          </div>
          <div className="mt-4 flex items-center justify-center">
            <span className="font-data text-ink-faint">↓</span>
          </div>
          <div className="rounded-lg border border-dashed border-line-strong py-4 text-center">
            <p className="label-tag text-ink-dim">shared curation · descriptors · embeddings</p>
          </div>
          <p className="mt-4 text-center text-xs leading-relaxed text-ink-faint">
            All four components feed a common reliability-metrics layer — RNIS · BCS · AD tiers · PARRS · PDSS · ARR.
          </p>
        </Card>
      </div>
    </div>
  );
}
