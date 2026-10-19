import { useApi } from "@/lib/api/useApi";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader } from "@/components/ui/Card";
import { c4Api } from "@/features/c4-screen/services/api";

export function PipelinePage() {
  const state = useApi(c4Api.funnel, []);
  return (
    <div className="space-y-5">
      <Card>
        <CardHeader title="Candidate-generation funnel" subtitle="Counts are served directly from the frozen per-plant funnel summary." />
        <DataState state={state} render={(rows) => (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[760px] text-left text-sm">
              <caption className="sr-only">C4 screening candidate counts by plant</caption>
              <thead><tr className="border-b text-xs uppercase" style={{ borderColor: "var(--color-border)", color: "var(--color-text-muted)" }}>
                <th scope="col" className="p-2">Plant</th><th scope="col" className="p-2">Proteins</th><th scope="col" className="p-2">Raw fragments</th><th scope="col" className="p-2">Length 3–20</th><th scope="col" className="p-2">Composition pass</th><th scope="col" className="p-2">Unique peptides</th><th scope="col" className="p-2">Embedded</th>
              </tr></thead>
              <tbody>{rows.map((row) => <tr key={row.plant} className="border-b" style={{ borderColor: "var(--color-border)" }}>
                <th scope="row" className="p-2 font-semibold capitalize">{row.plant}</th>
                <td className="p-2">{row.proteins.toLocaleString()}</td><td className="p-2">{row.raw_fragments.toLocaleString()}</td>
                <td className="p-2">{row.length_filtered.toLocaleString()}</td><td className="p-2">{row.composition_filtered.toLocaleString()}</td>
                <td className="p-2">{row.deduplicated.toLocaleString()}</td>
                <td className="p-2">{row.embedded.toLocaleString()}</td>
              </tr>)}</tbody>
            </table>
          </div>
        )} />
      </Card>
      <Card>
        <CardHeader title="Pipeline notes" />
        <p className="text-sm" style={{ color: "var(--color-text-muted)" }}>Protein exclusions (short sequences or non-standard residues) are logged separately. Peptides are filtered to 3–20 amino acids and at least two amino-acid types, then deduplicated by exact sequence with provenance retained.</p>
      </Card>
    </div>
  );
}
