import { render, screen, waitFor } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { MetricsPage } from "@/features/c3-aop-bcs/pages/MetricsPage";
import type { DashboardPayload } from "@/features/c3-aop-bcs/types";

const data = {
  metrics: {
    primaryDelta: 0.05,
    invarianceRate: 0.93,
    invariantCount: 140,
    invariantDenominator: 150,
    falseSensitivityRate: 0.52,
    insufficientCount: 28,
    insufficientDenominator: 54,
    preliminaryBcs: 0.45,
    overallPfr: 0.11,
    flipCount: 48,
    flipDenominator: 449,
    pfrByType: { P1: 0.2, P2: 0.09, P3: 0.1 },
  },
  sensitivity: [{ delta: 0.05, primary: true, ir: 0.93, fsr: 0.52, bcs: 0.45 }],
  chartData: {
    absoluteDeltaDistribution: [{ label: "0.00–0.05", binStart: 0, binEnd: 0.05, binMidpoint: 0.025, P1: 0.5, P2: 0.7, P3: 0.6 }],
    scoreExamples: [{ label: "P1: W1A", perturbationType: "P1", original: 0.45, perturbed: 0.3 }],
    metricSummary: [
      { metric: "IR", value: 0.93 },
      { metric: "FSR", value: 0.52 },
      { metric: "BCS", value: 0.45 },
      { metric: "PFR", value: 0.11 },
    ],
    predictionFlips: [{ type: "P1", rate: 0.2, flips: 11, total: 54 }],
    source: { path: "data/processed/c3_aop_bcs/delta.csv", sha256: "abc123", recordCount: 449 },
  },
} as DashboardPayload;

describe("MetricsPage", () => {
  afterEach(() => vi.restoreAllMocks());

  it("renders four native interactive charts instead of embedded report images", async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => data }) as unknown as typeof fetch;
    const { container } = render(<MetricsPage />);
    await waitFor(() => expect(screen.getByText("Interactive pilot charts")).toBeInTheDocument());
    expect(screen.getByRole("img", { name: /absolute DeltaScore percentage distributions/i })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /original and perturbed scores/i })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /IR, FSR, BCS, and PFR/i })).toBeInTheDocument();
    expect(screen.getByRole("img", { name: /prediction flip rates/i })).toBeInTheDocument();
    expect(container.querySelectorAll("img")).toHaveLength(0);
    expect(screen.getByText(/449 validated rows/i)).toBeInTheDocument();
  });
});
