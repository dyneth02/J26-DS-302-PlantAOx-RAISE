import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { RetrievalPage } from "@/features/c1-procon/pages/RetrievalPage";
import type { RetrievalResponse } from "@/features/c1-procon/types";

const MOCK_RESPONSE: RetrievalResponse = {
  mode: "strict",
  n_queries: 49,
  chance_ap: 0.17692,
  chance_recall_at_5: 0.590902,
  representations: [
    { representation: "LENGTH", kind: "baseline", ap: 0.223, ap_lo: 0.208, ap_hi: 0.238, lift: 1.26, recall_at_5: 0.71, chance_recall_at_5: 0.59 },
    { representation: "Primary", kind: "model", ap: 0.14, ap_lo: 0.135, ap_hi: 0.147, lift: 0.79, recall_at_5: 0.55, chance_recall_at_5: 0.59 },
  ],
  paired: [
    { comparison: "Primary vs length only", ap_a: 0.14, ap_b: 0.223, delta_ap: -0.083, ci_lo: -0.099, ci_hi: -0.068, p_holm: 2e-11, verdict: "LENGTH better" },
  ],
  seeds: [{ model: "Primary", ap_mean: 0.1397, ap_sd: 0.0006, delta_ap_mean: -0.062, seeds_below_untrained: 5, n_seeds: 5 }],
  scale: [],
  collapse: [{ model: "Primary", mean_cos_heldout: 0.997, eff_rank_heldout: 15.8 }],
  trained_runs_total: 25,
  trained_runs_above_untrained: 0,
  note: "Average precision (AP) for retrieving metal-chelating peptides; the baselines are the fair reference.",
};

describe("RetrievalPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("states that no trained run beats the untrained embedding instead of hiding the negative result", async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => MOCK_RESPONSE }) as unknown as typeof fetch;

    render(<RetrievalPage />);

    await waitFor(() => expect(screen.getByText("0 of 25")).toBeInTheDocument());
    expect(screen.getByText(/the baselines are the fair reference/)).toBeInTheDocument();
    expect(screen.getByText("LENGTH better")).toBeInTheDocument();
  });
});
