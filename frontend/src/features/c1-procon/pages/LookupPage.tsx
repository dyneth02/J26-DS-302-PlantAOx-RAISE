import { useEffect, useState } from "react";
import { useApi } from "@/lib/api/useApi";
import { c1Api } from "@/features/c1-procon/services/api";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { C1_COLORS, Callout, HBarChart } from "@/features/c1-procon/components/charts";
import type { BarItem } from "@/features/c1-procon/components/charts";
import { SimpleTable, fmt } from "@/features/c1-procon/components/SimpleTable";
import type { LookupResponse } from "@/features/c1-procon/types";

const REACTIVE = new Set(["Y", "W", "H", "C", "M"]);
const EXAMPLES = ["YWH", "EFQI", "HLHP", "GGGG"];
const NOTHING_TYPED: LookupResponse = { query: "", valid: false, problems: ["empty input"], in_benchmark: false, record: null, composition: {}, nearest: [], notes: [] };

function LookupResult({ result }: { result: LookupResponse }) {
  if (!result.valid) {
    return (
      <Callout title="This input cannot be used" tone="bad">
        {result.problems.join("; ")}
      </Callout>
    );
  }

  const composition: BarItem[] = Object.entries(result.composition).map(([aa, value]) => ({
    label: aa,
    value,
    color: REACTIVE.has(aa) ? C1_COLORS.mc : C1_COLORS.baseline,
  }));
  const rec = result.record;

  return (
    <div className="space-y-4">
      {result.notes.map((note) => (
        <Callout key={note} title={note.startsWith("Length") ? "Length warning" : rec ? "How to read this" : "Not in the benchmark"} tone="warn">
          {note}
        </Callout>
      ))}

      {rec && (
        <Card>
          <CardHeader title="In the benchmark" subtitle={`Peptide ${rec.sequence}`} />
          <SimpleTable
            headers={["Labels", "Length", "Source", "Fold", "Homology group", "Strict evidence", "Out-of-fold MC score (strict)", "Out-of-fold MC score (extended)"]}
            rows={[
              [
                <Badge key="labels" tone={rec.labels === "GEN" ? "neutral" : "accent"}>{rec.labels}</Badge>,
                rec.length,
                rec.source_group ?? "n/a",
                rec.fold ?? "n/a",
                rec.homology_group ?? "n/a",
                rec.strict_evidence === null ? "n/a" : String(rec.strict_evidence),
                fmt(rec.oof_mc_score_strict, 2),
                fmt(rec.oof_mc_score_extended, 2),
              ],
            ]}
          />
        </Card>
      )}

      <Card>
        <CardHeader title={`Amino-acid composition (${result.query.length} aa)`} subtitle="Share of each of the 20 amino acids; this is the AAC-20 feature set used as a baseline." />
        <HBarChart items={composition} min={0} max={1} decimals={2} labelWidth={40} ariaLabel="Amino-acid composition of the peptide" />
        <p className="mt-2 text-xs" style={{ color: "var(--color-text-muted)" }}>
          Purple: Tyr, Trp, His, Cys and Met, residues often linked to radical scavenging and metal binding.
        </p>
      </Card>

      <Card>
        <CardHeader title="Nearest benchmark peptides by composition" subtitle="Cosine similarity of the amino-acid composition (1.0 = identical composition)." />
        <SimpleTable
          headers={["Sequence", "Labels", "Length", "Cosine"]}
          rows={result.nearest.map((n) => [<code key={n.sequence}>{n.sequence}</code>, n.labels, n.length, fmt(n.cosine, 3)])}
        />
      </Card>
    </div>
  );
}

export function LookupPage() {
  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");

  // wait a moment after typing so the API is not called on every keystroke
  useEffect(() => {
    const timer = setTimeout(() => setQuery(input.trim()), 250);
    return () => clearTimeout(timer);
  }, [input]);

  // nothing is requested until something is typed
  const state = useApi(() => (query ? c1Api.lookup(query) : Promise.resolve(NOTHING_TYPED)), [query]);

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader
          title="Peptide lookup"
          subtitle="Type any benchmark peptide, or a new one, to see its label, composition and nearest neighbours. No model is run here."
        />
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          maxLength={60}
          aria-label="peptide sequence"
          placeholder="TYPE A PEPTIDE, E.G. YWH OR ANY BENCHMARK SEQUENCE"
          spellCheck={false}
          autoComplete="off"
          className="w-full max-w-xl rounded-lg border px-3 py-2 font-mono text-sm uppercase"
          style={{ background: "var(--color-bg)", borderColor: "var(--color-border)", color: "var(--color-text)" }}
        />
        <div className="mt-3 flex flex-wrap items-center gap-2 text-xs" style={{ color: "var(--color-text-muted)" }}>
          Try:
          {EXAMPLES.map((example) => (
            <button
              key={example}
              type="button"
              onClick={() => setInput(example)}
              className="rounded-full border px-3 py-1 font-mono"
              style={{ borderColor: "var(--color-border)", color: "var(--color-text)" }}
            >
              {example}
            </button>
          ))}
        </div>
      </Card>

      {query ? (
        <DataState
          state={state}
          render={(result) =>
            // a response for an older input can still be on screen for one render after typing: hide it until it matches
            result.query === query.toUpperCase().slice(0, 200) ? (
              <LookupResult result={result} />
            ) : (
              <div className="h-24 animate-pulse rounded-xl" style={{ background: "var(--color-border)" }} aria-busy="true" />
            )
          }
        />
      ) : (
        <Callout title="Start typing" tone="info">
          Only the 20 standard amino acids are accepted. The benchmark covers peptides of 3 to 49 amino acids; anything outside that range is flagged as an extrapolation.
        </Callout>
      )}
    </div>
  );
}
