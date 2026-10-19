import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { EmbeddingPage } from "@/features/c1-procon/pages/EmbeddingPage";
import type { EmbeddingResponse } from "@/features/c1-procon/types";

const space = (key: string, name: string, all: number, sep: number, purity: number) => ({
  key, name, dim: 128, pc_variance_share: [0.4, 0.1, 0.05], within_mc: all, within_frs: all, between: all - sep, all_pairs: all,
  separation: sep, mc_neighbour_purity: purity, pc1_length_correlation: -0.6,
});

const MOCK: EmbeddingResponse = {
  meta: {
    n_peptides: 3, n_strict: 3, n_mc_active: 1, chance_mc_neighbour_purity: 0.1555, neighbours: 10,
    pooling_rule: "max-pool below 10 aa, mean-pool from 10 aa", peptides_ge_10_aa: 1, peptides_lt_10_aa: 2,
  },
  spaces: [space("esm2", "Untrained ESM-2 650M", 0.92, 0.002, 0.19), space("primary", "Main trained head", 0.997, 0.0002, 0.127), space("maxspread", "Head selected for spread", 0.35, 0.018, 0.164)],
  points: [
    { sequence: "HYY", label: "FRS", length: 3, source_group: "anoxpepred", strict_class: "FRS-only", coords: { esm2: [0, 0, 0], primary: [0, 0, 0], maxspread: [0, 0, 0] } },
    { sequence: "EFQI", label: "MC", length: 4, source_group: "external_literature", strict_class: "MC-active", coords: { esm2: [1, 1, 1], primary: [0.1, 0, 0.1], maxspread: [1, -1, 0.5] } },
    { sequence: "GEN", label: "GEN", length: 12, source_group: "tier3_db", strict_class: "not in strict pool", coords: { esm2: [2, 0, -1], primary: [0, 0.1, 0], maxspread: [-1, 1, -0.5] } },
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

  it("switches the map between 2D and 3D without losing the story", async () => {
    // jsdom has no canvas; the 3-D view must still mount and expose its accessible name and controls
    vi.spyOn(HTMLCanvasElement.prototype, "getContext").mockReturnValue(null);
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => MOCK }) as unknown as typeof fetch;
    render(<EmbeddingPage />);

    await waitFor(() => expect(screen.getByRole("img", { name: /PCA map of the peptides in the Untrained ESM-2 650M space/ })).toBeInTheDocument());
    fireEvent.click(screen.getByRole("button", { name: "3D map" }));
    expect(screen.getByRole("img", { name: /3-D PCA map of the peptides in the Untrained ESM-2 650M space/ })).toBeInTheDocument();
    expect(screen.getByText(/PC3 \(5%\)/)).toBeInTheDocument();
    expect(screen.getByLabelText("auto-rotate")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Main trained head" }));
    expect(screen.getByRole("img", { name: /3-D PCA map of the peptides in the Main trained head space/ })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "2D map" }));
    expect(screen.queryByLabelText("auto-rotate")).not.toBeInTheDocument();
  });

  it("lets the viewer hide a legend group and resets the choice when the colouring changes", async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => MOCK }) as unknown as typeof fetch;
    render(<EmbeddingPage />);

    const mc = await screen.findByRole("button", { name: /MC-active \(metal chelation\)/ });
    expect(mc).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(mc);
    expect(mc).toHaveAttribute("aria-pressed", "false");
    fireEvent.click(mc);
    expect(mc).toHaveAttribute("aria-pressed", "true");

    fireEvent.click(mc);
    fireEvent.click(screen.getByRole("button", { name: "Peptide length" }));
    const tri = screen.getByRole("button", { name: /3 aa \(tripeptides\)/ });
    expect(tri).toHaveAttribute("aria-pressed", "true");
    fireEvent.click(screen.getByRole("button", { name: "Mechanism (MC vs FRS)" }));
    expect(screen.getByRole("button", { name: /MC-active \(metal chelation\)/ })).toHaveAttribute("aria-pressed", "true");
  });
});
