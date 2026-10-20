import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { AppShell } from "@/components/layout/AppShell";
import { PlatformOverviewPage } from "@/app/pages/PlatformOverviewPage";
import { c2PuRoutes } from "@/features/c2-pu/routes";
import { c3AopBcsRoutes } from "@/features/c3-aop-bcs/routes";
import { Outlet } from "react-router-dom";

function buildTestRouter(initialPath: string) {
  return createMemoryRouter(
    [
      {
        path: "/",
        element: (
          <AppShell title="PlantAOx-RAISE">
            <Outlet />
          </AppShell>
        ),
        children: [{ index: true, element: <PlatformOverviewPage /> }, ...c2PuRoutes, ...c3AopBcsRoutes],
      },
    ],
    { initialEntries: [initialPath] }
  );
}

describe("application shell + routing", () => {
  const originalFetch = global.fetch;

  afterEach(() => {
    global.fetch = originalFetch;
    vi.restoreAllMocks();
  });

  it("renders the shared shell navigation with all four components", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    }) as unknown as typeof fetch;

    render(<RouterProvider router={buildTestRouter("/")} />);

    expect(screen.getAllByText("PlantAOx-RAISE").length).toBeGreaterThan(0);
    expect(screen.getByText(/C2 — PU-AOP/)).toBeInTheDocument();
    expect(screen.getByText(/C1 — AOP-ProCon/)).toBeInTheDocument();
    expect(screen.getByText(/C3 — AOP-BCS/)).toBeInTheDocument();
    expect(screen.getByText(/C4 — PlantAOP-Screen/)).toBeInTheDocument();
    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
  });

  it("registers C2 routes and renders the C2 section nav", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        component_id: "c2_pu",
        research_title: "PU-AOP",
        objective: "test objective",
        freeze_id: "c2_pp1_freeze_v1",
        release_tag: "c2-pp1-v1",
        freeze_decision: "FROZEN — READY WITH LIMITATIONS",
        freeze_date: "2026-10-16",
        fr_milestones: {},
        data_counts: {},
        model_count: 5,
        caveats: {
          technical_status: "accepted",
          scientific_status: "reliable antioxidant-activity discrimination not established",
          supervisor_approval_status: "pending",
          known_limitations: ["Some limitation"],
        },
      }),
    }) as unknown as typeof fetch;

    render(<RouterProvider router={buildTestRouter("/c2")} />);

    await waitFor(() => expect(screen.getByText("PU-AOP")).toBeInTheDocument());
    expect(screen.getByRole("navigation", { name: "Component 02 sections" })).toBeInTheDocument();
    expect(screen.getByText("FROZEN — READY WITH LIMITATIONS")).toBeInTheDocument();
  });

  it("registers C3 routes in the shared shell", () => {
    global.fetch = vi.fn(() => new Promise(() => undefined)) as unknown as typeof fetch;
    render(<RouterProvider router={buildTestRouter("/c3")} />);

    expect(screen.getByText("AOP-BCS")).toBeInTheDocument();
    expect(screen.getByText("SOFTWARE-TESTING DATA ONLY")).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Component 03 sections" })).toBeInTheDocument();
  });
});
