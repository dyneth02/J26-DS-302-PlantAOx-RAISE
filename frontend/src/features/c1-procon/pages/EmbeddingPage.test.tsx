import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { EmbeddingPage } from "@/features/c1-procon/pages/EmbeddingPage";
import type { EmbeddingResponse } from "@/features/c1-procon/types";

const space = (key: string, name: string, all: number, sep: number, purity: number) => ({
  key, name, dim: 128, pc_variance_share: [0.4, 0.1], within_mc: all, within_frs: all, between: all - sep, all_pairs: all,
  separation: sep, mc_neighbour_purity: purity, pc1_length_correlation: -0.6,
});

const MOCK: EmbeddingResponse = {
  meta: {
    n_peptides: 3, n_strict: 3, n_mc_active: 1, chance_mc_neighbour_purity: 0.1555, neighbours: 10,
    pooling_rule: "max-pool below 10 aa, mean-pool from 10 aa", peptides_ge_10_aa: 1, peptides_lt_10_aa: 2,
  },
  spaces: [space("esm2", "Untrained ESM-2 650M", 0.92, 0.002, 0.19), space("primary", "Main trained head", 0.997, 0.0002, 0.127), space("maxspread", "Head selected for spread", 0.35, 0.018, 0.164)],
  points: [
    { sequence: "HYY", label: "FRS", length: 3, source_group: "anoxpepred", strict_class: "FRS-only", coords: { esm2: [0, 0], primary: [0, 0], maxspread: [0, 0] } },
    { sequence: "EFQI", label: "MC", length: 4, source_group: "external_literature", strict_class: "MC-active", coords: { esm2: [1, 1], primary: [0.1, 0], maxspread: [1, -1] } },
    { sequence: "GEN", label: "GEN", length: 12, source_group: "tier3_db", strict_class: "not in strict pool", coords: { esm2: [2, 0], primary: [0, 0.1], maxspread: [-1, 1] } },
  ],
  pair_counts: [{ pair_set: "positive_pairs", description: "Main pairs", pairs: 10195 }],
  pair_examples: [{ mechanism: "MC", seq1: "EFQI", seq2: "EFQL", distance: 0.13 }],
  reading_guide: ["Each dot is one peptide."],
};

describe("EmbeddingPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("explains collapse of the trained head instead of hiding it", async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => MOCK }) as unknown as typeof fetch;
    render(<EmbeddingPage />);

    await waitFor(() => expect(screen.getByText(/Untrained ESM-2: structure comes from length/)).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "Main trained head" }));
    expect(screen.getByText(/pulled to almost the same point/)).toBeInTheDocument();
    expect(screen.getByText(/average cosine 0.997/)).toBeInTheDocument();
  });
});
