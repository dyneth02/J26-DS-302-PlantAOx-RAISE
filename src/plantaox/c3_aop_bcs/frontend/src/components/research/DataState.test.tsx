import { render, screen } from "@testing-library/react";
import { DataState } from "@/components/research/DataState";
import { ApiError } from "@/lib/api/client";

describe("DataState", () => {
  it("distinguishes missing C3 artifacts from generic failures", () => {
    render(<DataState state={{ status: "error", error: new ApiError("manifest missing", 503) }} render={() => null} />);
    expect(screen.getByText("C3 artifact unavailable")).toBeInTheDocument();
    expect(screen.getByText("manifest missing")).toBeInTheDocument();
  });
});
