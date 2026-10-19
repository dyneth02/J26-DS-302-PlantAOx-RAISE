import { fireEvent, render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { C4Shell } from "@/features/c4-screen/components/C4Shell";
import { DemoMarker, ProvenanceChips, TierBadge } from "@/features/c4-screen/components/Provenance";

describe("C4 shared feature chrome", () => {
  it("keeps the mock-data warning visible and exposes keyboard-operable views", () => {
    const router = createMemoryRouter([
      { path: "/c4", element: <C4Shell />, children: [{ index: true, element: <h3>Overview content</h3> }] },
    ], { initialEntries: ["/c4"] });
    render(<RouterProvider router={router} />);
    expect(screen.getByRole("status")).toHaveTextContent("MOCK REFERENCE CLOUD + MOCK SIGNALS");
    expect(screen.getByRole("navigation", { name: "Component 04 sections" })).toBeInTheDocument();
    const toggle = screen.getByRole("button", { name: "Presentation mode" });
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute("aria-pressed", "true");
  });

  it("labels tiers in text and identifies injected demo cases", () => {
    render(<><ProvenanceChips /><TierBadge tier={2} /><DemoMarker injected /></>);
    expect(screen.getByText("Tier 2 · AMBER")).toBeInTheDocument();
    expect(screen.getByText("Injected demo case")).toBeInTheDocument();
    expect(screen.getByText("SIM_C1: mock")).toBeInTheDocument();
  });
});
