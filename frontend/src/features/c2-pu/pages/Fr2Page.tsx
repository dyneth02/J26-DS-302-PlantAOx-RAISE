import { useState } from "react";
import { useApi } from "@/lib/api/useApi";
import { c2Api } from "@/features/c2-pu/services/api";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader, StatTile } from "@/components/ui/Card";
import { LimitationsPanel } from "@/components/research/LimitationsPanel";

export function Fr2Page() {
  const poolsState = useApi(c2Api.fr2Pools, []);
  const [foldId, setFoldId] = useState(0);
  const foldState = useApi(() => c2Api.fr2FoldChallenges(foldId), [foldId]);

  return (
    <DataState
      state={poolsState}
      render={(pools) => (
        <div className="space-y-6">
          <Card>
            <CardHeader
              title="FR2 — Challenge-pool explorer"
              subtitle={`Frozen as ${pools.version_id}. C1/C2/C3 are unlabeled, not confirmed non-antioxidant peptides.`}
            />
            <div className="grid gap-4 sm:grid-cols-2">
              {pools.pools.map((pool) => (
                <div key={pool.pool} className="rounded-lg border p-4" style={{ borderColor: "var(--color-border)" }}>
                  <p className="text-sm font-semibold">{pool.pool}</p>
                  <p className="mt-1 text-xs" style={{ color: "var(--color-text-muted)" }}>
                    {pool.description}
                  </p>
                  <div className="mt-3 flex gap-6">
                    <StatTile label="Records" value={pool.record_count.toLocaleString()} />
                    {pool.unique_sequence_count !== null && (
                      <StatTile label="Unique sequences" value={pool.unique_sequence_count.toLocaleString()} />
                    )}
                  </div>
                </div>
              ))}
            </div>
          </Card>

          <Card>
            <CardHeader
              title="C3 fold-specific hard challenges"
              subtitle={`${pools.c3_selected_per_fold.toLocaleString()} selected per fold out of ${pools.c3_ranking_total_rows.toLocaleString()} ranking rows — never the full union.`}
            />
            <div className="mb-4 flex items-center gap-2">
              <label htmlFor="fold-select" className="text-sm font-medium">
                GraphPart fold
              </label>
              <select
                id="fold-select"
                value={foldId}
                onChange={(e) => setFoldId(Number(e.target.value))}
                className="rounded-lg border px-2 py-1 text-sm"
                style={{ borderColor: "var(--color-border)", background: "var(--color-surface)" }}
              >
                {[0, 1, 2, 3, 4].map((id) => (
                  <option key={id} value={id}>
                    Fold {id}
                  </option>
                ))}
              </select>
            </div>

            <DataState
              state={foldState}
              render={(fold) => (
                <div>
                  <p className="mb-2 text-sm" style={{ color: "var(--color-text-muted)" }}>
                    {fold.n_rows.toLocaleString()} fold-{fold.fold_id} challenge rows. Top 10 by cosine similarity to
                    the training-only positive centroid:
                  </p>
                  <table className="w-full text-left text-sm">
                    <thead>
                      <tr style={{ color: "var(--color-text-muted)" }}>
                        <th className="pb-2">Rank</th>
                        <th className="pb-2">Peptide ID</th>
                        <th className="pb-2">Sequence</th>
                        <th className="pb-2">Cosine similarity</th>
                      </tr>
                    </thead>
                    <tbody>
                      {fold.top_examples.map((row) => (
                        <tr key={row.peptide_id} className="border-t" style={{ borderColor: "var(--color-border)" }}>
                          <td className="py-1.5">{row.rank}</td>
                          <td className="py-1.5 font-mono text-xs">{row.peptide_id}</td>
                          <td className="py-1.5 font-mono text-xs">{row.sequence}</td>
                          <td className="py-1.5">{row.cosine_similarity.toFixed(4)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            />
          </Card>

          <LimitationsPanel items={pools.known_limitations} />
        </div>
      )}
    />
  );
}
