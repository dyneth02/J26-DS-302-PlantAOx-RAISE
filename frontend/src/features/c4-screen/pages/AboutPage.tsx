import { Card, CardHeader } from "@/components/ui/Card";
import { useApi } from "@/lib/api/useApi";
import { DataState } from "@/components/research/DataState";
import { c4Api } from "@/features/c4-screen/services/api";

const limitations = [
  "The current reference cloud is a synthetic mock placeholder; d_AD, thresholds, tiers, and their diagnostics depend on that cloud.",
  "SIM_C1, PROB_C2, and BCS are mock signals. They are not biological evidence or measured predictor outputs.",
  "No PARRS, Recall@K, MRR, EF@1%, ARR, or PDSS result is shown or computed on these mock inputs.",
  "ESM-2 layer-33 mean pooling over residues excluding BOS/EOS/PAD is a C4 working assumption, not confirmed by C1.",
  "The current reference cloud and plant candidate length distributions differ; length can influence distance comparisons.",
  "Mean-centering is presented as a sensitivity analysis only. Production thresholds and tier assignments are not changed by it.",
  "BCS flag boundaries are C4-provisional. GREEN/AMBER/RED labels are display categories, not validated biological classifications.",
];

export function AboutPage() {
  const lengths = useApi(c4Api.lengths, []);
  return (
    <div className="space-y-5">
      <Card><CardHeader title="About Component 4" subtitle="PlantAOP-Screen screens in-silico plant digestome peptides and presents an applicability-domain demonstration." />
        <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>The backend serves read-only frozen outputs. Candidate generation uses reviewed plant proteomes, sequential pepsin pH 1.3 then trypsin digestion, 3–20 AA filtering, composition filtering, and exact-sequence deduplication. Supplied ESM-2 embeddings are used for distance calculations; this application never loads or runs ESM-2.</p>
      </Card>
      <Card><CardHeader title="What this does NOT show" />
        <ul className="list-disc space-y-2 pl-5 text-sm">{limitations.map((item) => <li key={item}>{item}</li>)}</ul>
        <DataState state={lengths} render={(data) => {
          const cloudN = data.distributions.reduce((sum, row) => sum + row.cloud_count, 0) || 1;
          const candidateN = data.distributions.reduce((sum, row) => sum + row.candidate_count, 0) || 1;
          const cloudMean = data.distributions.reduce((sum, row) => sum + row.length * row.cloud_count, 0) / cloudN;
          const candidateMean = data.distributions.reduce((sum, row) => sum + row.length * row.candidate_count, 0) / candidateN;
          return <p className="mt-3 text-sm">Current MOCK cloud mean length: {cloudMean.toFixed(2)} aa (n={cloudN.toLocaleString()}); candidate mean length: {candidateMean.toFixed(2)} aa (n={candidateN.toLocaleString()}). This mismatch is descriptive and may affect distance comparisons.</p>;
        }} />
      </Card>
      <Card><CardHeader title="Provenance" />
        <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>The reference cloud and all signal sources are labelled in each view and evidence card. Injected demo cases are explicitly marked. Mock inputs are never used to calculate retrieval metrics.</p>
      </Card>
      <Card><CardHeader title="Offline fallback" subtitle="The original static C4 dashboard remains available in the repository." />
        <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>Open <code>data/interim/c4_screen/c4_dashboard.html</code> directly from the project directory if the API or interactive frontend is unavailable.</p>
        <a href="/data/interim/c4_screen/c4_dashboard.html" target="_blank" rel="noreferrer" className="mt-3 inline-block text-sm font-semibold underline" style={{ color: "var(--color-primary)" }}>Try opening the offline C4 dashboard</a>
      </Card>
    </div>
  );
}
