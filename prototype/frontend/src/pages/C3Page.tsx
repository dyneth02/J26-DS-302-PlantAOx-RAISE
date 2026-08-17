import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { c3Api } from "../api/client";
import PageHeader from "../components/PageHeader";
import Card from "../components/Card";
import Banner from "../components/Banner";
import StatCard from "../components/StatCard";
import { FLAG_STYLES } from "../components/chartTheme";

export default function C3Page() {
  const [summary, setSummary] = useState<any>(null);
  const [activePredictor, setActivePredictor] = useState<string>("c2_logreg");
  const [bcs, setBcs] = useState<any>(null);
  const [example, setExample] = useState<any>(null);
  const [results, setResults] = useState<any[]>([]);
  const [reliabilityFlags, setReliabilityFlags] = useState<any>(null);

  useEffect(() => {
    c3Api.summary().then(setSummary);
    c3Api.reliabilityFlags().then(setReliabilityFlags);
  }, []);

  useEffect(() => {
    c3Api.bcs(activePredictor).then(setBcs);
    c3Api.examplePerturbation(activePredictor).then(setExample);
    c3Api.perturbationResults(activePredictor).then(setResults);
  }, [activePredictor]);

  return (
    <div>
      <PageHeader eyebrow="Component 3" title="AOP-BCS" subtitle="Perturbation-Based Faithfulness Auditing" />
      <div className="space-y-6 p-8">
        {summary && (
          <Banner title={`Auditing ${summary.predictors_audited?.length ?? 0} real predictors, identical perturbations`}>
            {summary.notes?.join(" ")}
          </Banner>
        )}

        {reliabilityFlags && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            {Object.entries(reliabilityFlags).map(([key, flag]: [string, any]) => {
              const isActive = activePredictor === key;
              return (
                <motion.button
                  key={key}
                  onClick={() => setActivePredictor(key)}
                  whileHover={{ y: -2 }}
                  className={`panel relative overflow-hidden p-5 text-left transition-all duration-300 ${
                    isActive ? "ring-1 ring-lime/40 shadow-glow" : "opacity-70 hover:opacity-100"
                  }`}
                >
                  <p className="label-tag text-ink-faint">{key}</p>
                  <p className="mt-1 text-sm font-medium text-ink">{flag.display_name}</p>
                  <div className="mt-3 flex items-center gap-3">
                    <span className="font-display text-3xl font-medium text-ink">{flag.bcs}</span>
                    <span className={`rounded-full px-2.5 py-1 label-tag ${FLAG_STYLES[flag.flag]}`}>{flag.flag}</span>
                  </div>
                </motion.button>
              );
            })}
          </div>
        )}

        {bcs && (
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatCard label="Invariance rate (IR)" value={bcs.invariance_rate} accent="teal" />
            <StatCard label="False sensitivity rate (FSR)" value={bcs.false_sensitivity_rate} accent="amber" />
            <StatCard label="BCS = IR × (1 − FSR)" value={bcs.bcs} />
            <div className="panel p-4">
              <p className="label-tag text-ink-faint">Reliability flag</p>
              <span className={`mt-2 inline-block rounded-full px-3 py-1 text-sm font-semibold ${FLAG_STYLES[bcs.reliability_flag]}`}>
                {bcs.reliability_flag}
              </span>
            </div>
          </div>
        )}

        {bcs && (
          <Card title="Metric definitions" subtitle={bcs.predictor_display_name} eyebrow="Method">
            <dl className="space-y-3 text-sm">
              {Object.entries(bcs.metric_definitions).map(([k, v]: [string, any]) => (
                <div key={k}>
                  <dt className="font-data text-xs font-medium text-teal">{k}</dt>
                  <dd className="mt-0.5 text-ink-dim">{v}</dd>
                </div>
              ))}
            </dl>
            <p className="mt-4 border-t border-line pt-3 text-xs leading-relaxed text-ink-faint">
              Redox-residue alanine-scan sensitivity: <strong className="text-ink-dim">{bcs.redox_sensitivity_rate}</strong> ·
              Random-substitution sensitivity (control): <strong className="text-ink-dim">{bcs.random_substitution_sensitivity_rate}</strong> ·
              audited on <strong className="text-ink-dim">{bcs.n_audited}</strong> real sequences.
            </p>
          </Card>
        )}

        {example && (
          <Card title="Example perturbation" subtitle={`Peptide ${example.peptide_id} — original score ${example.original_score}`} eyebrow="Sample">
            <div className="space-y-2">
              <div className="rounded-lg border border-line bg-surface2/60 p-3 font-data text-sm text-ink">
                {example.original_sequence} <span className="text-ink-faint">(original, score {example.original_score})</span>
              </div>
              {example.perturbations.map((p: any) => (
                <div key={p.type} className="flex items-center justify-between rounded-lg border border-line p-3">
                  <div>
                    <p className="label-tag text-ink-faint">{p.type}</p>
                    <p className="mt-0.5 font-data text-sm text-ink">{p.sequence}</p>
                  </div>
                  <div className="text-right text-sm">
                    <p className="text-ink-dim">score {p.score}</p>
                    <p className={`font-data ${p.delta < 0 ? "text-coral" : "text-lime"}`}>Δ {p.delta}</p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        )}

        <Card title="Perturbation results" subtitle={`${results.length} audited peptides (first 25 shown)`} eyebrow="Raw data">
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-line text-left text-ink-faint">
                  <th className="py-2 pr-3 label-tag font-normal">Sequence</th>
                  <th className="py-2 pr-3 label-tag font-normal">Original</th>
                  <th className="py-2 pr-3 label-tag font-normal">P1 Δ (Ala scan)</th>
                  <th className="py-2 pr-3 label-tag font-normal">P2 Δ (conservative)</th>
                  <th className="py-2 label-tag font-normal">P3 Δ (random)</th>
                </tr>
              </thead>
              <tbody>
                {results.slice(0, 25).map((r) => (
                  <tr key={r.peptide_id} className="border-b border-line last:border-0 font-data text-xs text-ink-dim">
                    <td className="py-1.5 pr-3 text-ink">{r.sequence}</td>
                    <td className="py-1.5 pr-3">{r.original_score}</td>
                    <td className="py-1.5 pr-3">{r.p1_delta}</td>
                    <td className="py-1.5 pr-3">{r.p2_delta}</td>
                    <td className="py-1.5">{r.p3_delta}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
    </div>
  );
}
