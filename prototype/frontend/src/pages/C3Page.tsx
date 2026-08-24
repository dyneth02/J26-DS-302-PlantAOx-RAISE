import { useEffect, useMemo, useState } from "react";
import { motion } from "framer-motion";
import { Loader2 } from "lucide-react";
import { c3Api } from "../api/client";
import PageHeader from "../components/PageHeader";
import Card from "../components/Card";
import Banner from "../components/Banner";
import StatCard from "../components/StatCard";
import Select from "../components/Select";
import Skeleton from "../components/Skeleton";
import Section from "../components/Section";
import PerturbationTypeExplorer from "../components/PerturbationTypeExplorer";
import PredictorArena, { type PredictorArenaEntry } from "../components/PredictorArena";
import ReliabilityFlagModal from "../components/ReliabilityFlagModal";
import { usePresentationStore } from "../store/presentationStore";
import { FLAG_STYLES } from "../components/chartTheme";
import type { PerturbationResultRow, LivePerturbationResult } from "../types/c3";

const VALID_AA = /^[ACDEFGHIKLMNPQRSTVWY]+$/;
const REDOX_AA = /[WYHMC]/;
const NON_REDOX_AA = /[ADEFGIKLNPQRSTV]/;

function validateSequence(seq: string): string | null {
  const s = seq.trim().toUpperCase();
  if (s.length < 3 || s.length > 50) return "Sequence must be 3–50 amino acids.";
  if (!VALID_AA.test(s)) return "Only the 20 standard amino acid letters are allowed.";
  if (!REDOX_AA.test(s)) return "Sequence needs at least one redox-active residue (W, Y, H, M, or C).";
  if (!NON_REDOX_AA.test(s)) return "Sequence needs at least one non-redox residue too, so a perturbation site exists.";
  return null;
}

export default function C3Page() {
  const [summary, setSummary] = useState<any>(null);
  const [activePredictor, setActivePredictor] = useState<string>("c2_logreg");
  const [bcs, setBcs] = useState<any>(null);
  const [example, setExample] = useState<any>(null);
  const [results, setResults] = useState<PerturbationResultRow[]>([]);
  const [reliabilityFlags, setReliabilityFlags] = useState<any>(null);
  const [arenaEntries, setArenaEntries] = useState<PredictorArenaEntry[]>([]);
  const [flagModalOpen, setFlagModalOpen] = useState(false);

  const [browseId, setBrowseId] = useState<string | null>(null);
  const [customSeq, setCustomSeq] = useState("");
  const [liveResult, setLiveResult] = useState<LivePerturbationResult | null>(null);
  const [liveLoading, setLiveLoading] = useState(false);
  const [liveError, setLiveError] = useState<string | null>(null);
  const safeMode = usePresentationStore((s) => s.safeMode);
  const resetSignal = usePresentationStore((s) => s.resetSignal);

  useEffect(() => {
    c3Api.summary().then(setSummary);
    c3Api.reliabilityFlags().then(setReliabilityFlags);
    c3Api.predictors().then((preds: { key: string; display_name: string }[]) => {
      Promise.all(preds.map((p) => c3Api.bcs(p.key))).then((rows) => {
        setArenaEntries(
          rows.map((r) => ({
            key: r.predictor,
            display_name: r.predictor_display_name,
            bcs: r.bcs,
            reliability_flag: r.reliability_flag,
            invariance_rate: r.invariance_rate,
            false_sensitivity_rate: r.false_sensitivity_rate,
            redox_sensitivity_rate: r.redox_sensitivity_rate,
            random_substitution_sensitivity_rate: r.random_substitution_sensitivity_rate,
          }))
        );
      });
    });
  }, []);

  useEffect(() => {
    if (resetSignal === 0) return;
    setBrowseId(null);
    setCustomSeq("");
    setLiveResult(null);
    setLiveError(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resetSignal]);

  useEffect(() => {
    c3Api.bcs(activePredictor).then(setBcs);
    c3Api.examplePerturbation(activePredictor).then(setExample);
    c3Api.perturbationResults(activePredictor).then(setResults);
    setBrowseId(null);
    setLiveResult(null);
    setLiveError(null);
  }, [activePredictor]);

  const browseOptions = useMemo(
    () => results.map((r) => ({ value: r.peptide_id, label: r.peptide_id, sublabel: r.sequence })),
    [results]
  );
  const browseRow = results.find((r) => r.peptide_id === browseId) ?? null;

  const seqError = customSeq.trim() ? validateSequence(customSeq) : null;

  async function handleLivePerturbation() {
    const s = customSeq.trim().toUpperCase();
    const err = validateSequence(s);
    if (err) {
      setLiveError(err);
      return;
    }
    setLiveLoading(true);
    setLiveError(null);
    try {
      const data = await c3Api.livePerturbation(s);
      setLiveResult(data);
    } catch (e: any) {
      setLiveError(e?.response?.data?.detail ?? "Live scoring failed.");
      setLiveResult(null);
    } finally {
      setLiveLoading(false);
    }
  }

  return (
    <div>
      <PageHeader eyebrow="Component 3" title="AOP-BCS" subtitle="Perturbation-Based Faithfulness Auditing" />
      <div className="space-y-6 p-8">
        <Section
          id="c3-overview"
          label="Overview"
          notes="Frame BCS as a faithfulness check, not an accuracy check: a predictor can be accurate and still be unfaithful if conservative substitutions flip its verdict. The radar chart is the fastest way to compare both real predictors head-to-head."
        >
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

        {!reliabilityFlags && (
          <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Skeleton className="h-[7.5rem]" />
            <Skeleton className="h-[7.5rem]" />
          </div>
        )}

        {bcs && (
          <div className="grid grid-cols-2 gap-4 md:grid-cols-4">
            <StatCard
              label="Invariance rate (IR)"
              value={bcs.invariance_rate}
              accent="teal"
              tooltip="Fraction of conservative (BLOSUM62) substitutions the predictor's score barely moved on. Higher = more consistent."
            />
            <StatCard
              label="False sensitivity rate (FSR)"
              value={bcs.false_sensitivity_rate}
              accent="amber"
              tooltip="Fraction of those same conservative substitutions that flipped the predicted class label. Lower = more reliable."
            />
            <StatCard label="BCS = IR × (1 − FSR)" value={bcs.bcs} tooltip="Behavioral Consistency Score — the single reliability number this page is built around." />
            <button onClick={() => setFlagModalOpen(true)} className="panel p-4 text-left transition-colors hover:bg-surface2/40">
              <p className="label-tag text-ink-faint">Reliability flag · click to see why</p>
              <span className={`mt-2 inline-block rounded-full px-3 py-1 text-sm font-semibold ${FLAG_STYLES[bcs.reliability_flag]}`}>
                {bcs.reliability_flag}
              </span>
            </button>
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

        {arenaEntries.length > 1 && (
          <Card
            title="Predictor comparison arena"
            subtitle="Both real predictors, audited on the exact same perturbations — a fair head-to-head"
            eyebrow="Compare"
          >
            <PredictorArena predictors={arenaEntries} />
          </Card>
        )}
        </Section>

        <Section
          id="c3-perturbations"
          label="Perturbation audit"
          notes="This is the most hands-on part of the demo — type any real peptide sequence (3-50 AA, needs at least one redox residue) into the live scorer and watch real alanine-scan/BLOSUM62/random perturbations get generated and scored server-side."
        >
        {example && (
          <Card
            title="Example perturbation"
            subtitle={`Peptide ${example.peptide_id} — switch between perturbation types to see what changed`}
            eyebrow="Sample"
          >
            <PerturbationTypeExplorer
              original={example.original_sequence}
              originalScore={example.original_score}
              tabs={example.perturbations.map((p: any) => ({
                type: p.type,
                shortLabel: p.type.replace(/^P\d_/, "").replace(/_/g, " "),
                sequence: p.sequence,
                score: p.score,
                delta: p.delta,
              }))}
            />
          </Card>
        )}

        <Card
          title="Browse pre-computed perturbations"
          subtitle={`Search any of the ${results.length} already-audited peptides`}
          eyebrow="Raw data · both predictors"
        >
          <div className="max-w-sm">
            <Select
              options={browseOptions}
              value={browseId}
              onChange={setBrowseId}
              placeholder={`Search ${results.length} peptides…`}
            />
          </div>
          <>
            {browseRow && (
              <motion.div
                key={browseRow.peptide_id}
                initial={{ opacity: 0, y: 6 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.2 }}
                className="mt-4 space-y-2"
              >
                <div className="rounded-lg border border-line bg-surface2/60 p-3 font-data text-sm text-ink">
                  {browseRow.sequence}{" "}
                  <span className="text-ink-faint">
                    (original, score {browseRow.original_score}, {browseRow.mechanism_tier})
                  </span>
                </div>
                {[
                  { type: "P1_alanine_scan", sequence: browseRow.p1_sequence, score: browseRow.p1_score, delta: browseRow.p1_delta },
                  { type: "P2_blosum62_conservative", sequence: browseRow.p2_sequence, score: browseRow.p2_score, delta: browseRow.p2_delta },
                  { type: "P3_random_control", sequence: browseRow.p3_sequence, score: browseRow.p3_score, delta: browseRow.p3_delta },
                ].map((p) => (
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
              </motion.div>
            )}
          </>
        </Card>

        <Card
          title="Try it yourself: live perturbation scoring"
          subtitle="Enter your own sequence — real alanine-scan, BLOSUM62-conservative, and random perturbations are generated and scored on demand"
          eyebrow="Live · c2_logreg only"
        >
          {safeMode ? (
            <p className="text-sm text-ink-faint">
              Safe mode is on — live scoring against the backend is disabled. Turn off safe mode in the toolbar below to try it.
            </p>
          ) : activePredictor !== "c2_logreg" ? (
            <p className="text-sm text-ink-faint">
              Live custom scoring runs only against the lightweight <code className="font-data text-ink-dim">c2_logreg</code> predictor.
              Switch to it above to try your own sequence — <code className="font-data text-ink-dim">multiaop_pretrained</code> stays
              available in browse mode.
            </p>
          ) : (
            <div>
              <div className="flex flex-wrap items-center gap-2">
                <input
                  value={customSeq}
                  onChange={(e) => {
                    setCustomSeq(e.target.value.toUpperCase());
                    setLiveError(null);
                  }}
                  placeholder="e.g. WYSLAMAASDI"
                  maxLength={50}
                  className="w-64 rounded-lg border border-line-strong bg-surface2 px-3 py-2 font-data text-sm text-ink placeholder:text-ink-faint focus:outline-none focus:border-lime/40"
                />
                <button
                  onClick={handleLivePerturbation}
                  disabled={liveLoading || !customSeq.trim() || !!seqError}
                  className="flex items-center gap-1.5 rounded-lg border border-lime/40 bg-lime/10 px-3 py-2 text-sm font-medium text-lime transition-colors hover:bg-lime/[0.15] disabled:cursor-not-allowed disabled:opacity-40"
                >
                  {liveLoading && <Loader2 size={14} className="animate-spin" />}
                  Score it
                </button>
              </div>
              {(seqError || liveError) && (
                <p className="mt-2 text-xs text-coral">{liveError ?? seqError}</p>
              )}
              <>
                {liveResult && !liveError && (
                  <motion.div
                    key={liveResult.sequence}
                    initial={{ opacity: 0, y: 6 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.2 }}
                    className="mt-4 space-y-2"
                  >
                    <div className="rounded-lg border border-line bg-surface2/60 p-3 font-data text-sm text-ink">
                      {liveResult.sequence} <span className="text-ink-faint">(original, score {liveResult.original_score})</span>
                    </div>
                    {liveResult.perturbations.map((p, i) => (
                      <div key={p.type + i} className="flex items-center justify-between rounded-lg border border-line p-3">
                        <div>
                          <p className="label-tag text-ink-faint">{p.type}</p>
                          <p className="mt-0.5 font-data text-sm text-ink">{p.sequence}</p>
                          <p className="mt-0.5 text-xs text-ink-faint">
                            position {p.position} · {p.original_residue}
                            {p.new_residue ? ` → ${p.new_residue}` : ""}
                          </p>
                        </div>
                        <div className="text-right text-sm">
                          <p className="text-ink-dim">score {p.score.toFixed(4)}</p>
                          <p className={`font-data ${p.delta < 0 ? "text-coral" : "text-lime"}`}>Δ {p.delta.toFixed(4)}</p>
                        </div>
                      </div>
                    ))}
                  </motion.div>
                )}
              </>
            </div>
          )}
        </Card>
        </Section>

        <Section id="c3-raw" label="Raw perturbation results">
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
        </Section>
      </div>

      {bcs && (
        <ReliabilityFlagModal
          open={flagModalOpen}
          onClose={() => setFlagModalOpen(false)}
          predictorName={bcs.predictor_display_name}
          flag={bcs.reliability_flag}
          bcs={bcs.bcs}
          invarianceRate={bcs.invariance_rate}
          falseSensitivityRate={bcs.false_sensitivity_rate}
        />
      )}
    </div>
  );
}
