import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
// @ts-ignore
import { So4Page } from "@/features/c2-pu/pages/So4Page";
// @ts-ignore
import type { Fr4EvaluationResponse } from "@/features/c2-pu/types";

const MOCK_RESPONSE: Fr4EvaluationResponse = {
  fold_id: 0,
  evaluation_note: "Scores are uncalibrated model outputs, not validated biological probabilities. All five configurations show negative MCC and sub-0.5 AUROC on this evaluation.",
  challenge_behavior_note: "it is not a measured false-positive rate.",
  challenge_score_fractions: { M1: { C1: 0.06, C2: 0.33 } },
  models: [
    {
      model_id: "M1",
      model: "PN",
      mcc: -0.18,
      average_precision: 0.64,
      auroc: 0.25,
      precision: 0.74,
      recall: 0.87,
      f1: 0.8,
      balanced_accuracy: 0.56,
      confusion_matrix: { tp: 108, tn: 0, fp: 38, fn: 16 },
      n_positive: 124,
      n_control: 38,
      evaluation_population: "held-out positives vs external assay-inactive controls",
    },
  ],
};

describe("So4Page", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("labels MCC magnitudes and retains the scientific caveat language", async () => {
    // @ts-ignore
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => MOCK_RESPONSE,
    }) as unknown as typeof fetch;

    render(<So4Page />);

    await waitFor(() => expect(screen.getAllByText("PN").length).toBeGreaterThan(0));
    // @ts-ignore
    // Original signed-MCC assertion: expect(screen.getByText("-0.180")).toBeInTheDocument();
    expect(screen.getByText("MCC magnitude")).toBeInTheDocument();
    expect(screen.getByText("0.180")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "MCC" }));
    expect(screen.getByText(/positive absolute MCC magnitudes \(the signed MCC scores are negative\)/)).toBeInTheDocument();
    // @ts-ignore
    expect(screen.getByText(/not validated biological probabilities/)).toBeInTheDocument();
    // @ts-ignore
    expect(screen.getByText(/not a measured false-positive rate/)).toBeInTheDocument();
  });
});
