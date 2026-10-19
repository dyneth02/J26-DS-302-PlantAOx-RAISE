import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { c4ScreenRoutes } from "@/features/c4-screen/routes";
import { c4Api } from "@/features/c4-screen/services/api";

describe("C4 frontend routes", () => {
  afterEach(() => vi.restoreAllMocks());

  it("registers the C4 overview and keeps provenance and presentation controls visible", async () => {
    vi.spyOn(c4Api, "meta").mockResolvedValue({
      ad_params: { t1: 0.03, t2: 0.04 },
      cloud: { source: "mock_cloud", n: 500, status: "mock" },
      signal_sources: { SIM_C1: "mock", PROB_C2: "mock", BCS: "mock" },
      spec_version: "c4-interface-0.1-provisional",
      embedding_manifest_summary: { n: 152259, dim: 1280 },
      output_manifest_hash: "test-hash",
      tag: "c4-pp1-v1",
      warnings: ["The reference cloud is MOCK (mock_cloud).", "C1/C2/C3 signals are MOCK (source=mock).", "No retrieval metrics were computed on mock inputs."],
    });
    const router = createMemoryRouter([{ path: "/", children: c4ScreenRoutes }], { initialEntries: ["/c4"] });
    render(<RouterProvider router={router} />);
    await waitFor(() => expect(screen.getByText("152,259")).toBeInTheDocument());
    expect(screen.getByRole("status")).toHaveTextContent("demonstration, not biological evidence");
    expect(screen.getByRole("link", { name: "Evidence cards" })).toHaveAttribute("href", "/c4/cards");
    fireEvent.click(screen.getByRole("button", { name: "Presentation mode" }));
    expect(screen.getByRole("button", { name: "Exit presentation mode" })).toHaveAttribute("aria-pressed", "true");
  });
});
