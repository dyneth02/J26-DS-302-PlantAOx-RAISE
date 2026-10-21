import { useState } from "react";
import { useApi } from "@/lib/api/useApi";
import { c2Api } from "@/features/c2-pu/services/api";
import { DataState } from "@/components/research/DataState";
import { Card, CardHeader, StatTile } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";

export function So3Page() {
  const state = useApi(c2Api.fr3Examples, []);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  return (
    <DataState
      state={state}
      render={(fr3) => {
        const selected = fr3.examples.find((e) => e.peptide_id === selectedId) ?? fr3.examples[0];

        return (
          <div className="space-y-6">
            <Card>
              <CardHeader
                title="SO3 - Feature Engineering Workbench"
                subtitle={`Fold ${fr3.fold_id}. ${fr3.embedding_model}, ${fr3.embedding_dim}-dim embeddings fused with 15 physicochemical descriptors -> ${fr3.fused_dim} dims.`}
              />
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                {Object.entries(fr3.pool_coverage).map(([pool, count]) => (
                  <StatTile key={pool} label={pool.replaceAll("_", " ")} value={count.toLocaleString()} />
                ))}
              </div>
              <div className="mt-4">
                <Badge tone={fr3.feature_cache_available ? "success" : "danger"}>
                  {fr3.feature_cache_available ? "Fold-0 feature cache available" : "Fold-0 feature cache missing on this checkout"}
                </Badge>
              </div>
            </Card>

            <div className="grid gap-6 lg:grid-cols-[280px_1fr]">
              <Card>
                <CardHeader title="Accepted demonstration peptides" />
                <ul className="space-y-1">
                  {fr3.examples.map((example) => (
                    <li key={example.peptide_id}>
                      <button
                        type="button"
                        onClick={() => setSelectedId(example.peptide_id)}
                        className="w-full rounded-lg px-3 py-2 text-left text-sm"
                        style={{
                          background:
                            selected?.peptide_id === example.peptide_id ? "var(--color-primary)" : "transparent",
                          color: selected?.peptide_id === example.peptide_id ? "white" : "var(--color-text)",
                        }}
                      >
                        <span className="block font-medium">{example.role.replaceAll("_", " ")}</span>
                        <span className="block font-mono text-xs opacity-80">{example.peptide_id}</span>
                      </button>
                    </li>
                  ))}
                </ul>
              </Card>

              {selected && (
                <Card>
                  <CardHeader title={selected.peptide_id} subtitle={selected.role.replaceAll("_", " ")} />
                  <p className="font-mono text-sm break-all">{selected.sequence}</p>
                  <div className="mt-3 flex flex-wrap gap-4">
                    <StatTile label="Length" value={selected.length} />
                    <Badge tone={selected.valid_alphabet_and_length ? "success" : "danger"}>
                      {selected.valid_alphabet_and_length ? "Valid alphabet/length" : "Invalid"}
                    </Badge>
                    <Badge tone={selected.embedding_available ? "success" : "neutral"}>
                      ESM-2 embedding ({selected.embedding_dim}d) {selected.embedding_available ? "cached" : "unavailable"}
                    </Badge>
                  </div>

                  {selected.descriptors && (
                    <div className="mt-4">
                      <p className="mb-2 text-sm font-semibold">15 physicochemical descriptors (computed live)</p>
                      <div className="grid grid-cols-2 gap-x-6 gap-y-1 text-sm sm:grid-cols-3">
                        {Object.entries(selected.descriptors).map(([name, value]) => (
                          <div key={name} className="flex justify-between gap-2">
                            <span style={{ color: "var(--color-text-muted)" }}>{name.replaceAll("_", " ")}</span>
                            <span className="font-mono">{value.toFixed(3)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}

                  <p className="mt-4 text-xs" style={{ color: "var(--color-text-muted)" }}>
                    Fusion: these 15 descriptors + the {selected.embedding_dim}-dim cached ESM-2 embedding -&gt;{" "}
                    {selected.fused_dim}-dim vector, scaled by that fold's training-positives-only scaler. No new ESM-2
                    inference is triggered by this page.
                  </p>
                </Card>
              )}
            </div>
          </div>
        );
      }}
    />
  );
}
