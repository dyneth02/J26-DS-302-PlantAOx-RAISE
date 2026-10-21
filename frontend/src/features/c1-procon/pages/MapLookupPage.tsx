import { useApi } from "@/lib/api/useApi";
import { c1Api } from "@/features/c1-procon/services/api";
import { DataState } from "@/components/research/DataState";
import { EmbeddingBody } from "@/features/c1-procon/pages/EmbeddingPage";
import { LookupSearch } from "@/features/c1-procon/pages/LookupPage";

/** 3-D map of the benchmark peptides, followed by the peptide search box. */
export function MapLookupPage() {
  const state = useApi(c1Api.embedding, []);

  return (
    <div className="space-y-6">
      <DataState state={state} render={(data) => <EmbeddingBody data={data} mode="map" />} />
      <LookupSearch />
    </div>
  );
}
