import { render, screen } from "@testing-library/react";
import { createMemoryRouter, RouterProvider } from "react-router-dom";
import { C3Shell } from "@/features/c3-aop-bcs/components/C3Shell";

describe("C3 shell", () => {
  it("preserves the scientific boundary and all dashboard sections", () => {
    const router = createMemoryRouter([{ path: "/c3", element: <C3Shell />, children: [{ index: true, element: <p>Overview content</p> }] }], { initialEntries: ["/c3"] });
    render(<RouterProvider router={router} />);
    expect(screen.getByText("SOFTWARE-TESTING DATA ONLY")).toBeInTheDocument();
    expect(screen.getByText(/not scientific AOP results/i)).toBeInTheDocument();
    expect(screen.getByRole("navigation", { name: "Component 03 sections" })).toBeInTheDocument();
    for (const label of ["Overview", "Dataset", "Perturbations", "Pilot metrics", "Variant explorer", "Predictors", "Evidence"]) {
      expect(screen.getByRole("link", { name: label })).toBeInTheDocument();
    }
  });
});
