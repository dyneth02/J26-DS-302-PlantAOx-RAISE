import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { DataState } from "@/components/research/DataState";
import { ApiError } from "@/lib/api/client";
import type { ApiState } from "@/lib/api/useApi";

describe("DataState", () => {
  it("renders a loading skeleton", () => {
    const state: ApiState<string> = { status: "loading" };
    const { container } = render(<DataState state={state} render={(data) => <div>{data}</div>} />);
    expect(container.querySelector('[aria-busy="true"]')).toBeInTheDocument();
  });

  it("renders a distinct artifact-unavailable message for a 503 ApiError", () => {
    const state: ApiState<string> = {
      status: "error",
      error: new ApiError("fold-0 feature cache missing", 503, null),
    };
    render(<DataState state={state} render={(data) => <div>{data}</div>} />);
    expect(screen.getByText("Artifact unavailable in this checkout")).toBeInTheDocument();
    expect(screen.getByText(/fold-0 feature cache missing/)).toBeInTheDocument();
  });

  it("renders a generic error message for a non-503 failure", () => {
    const state: ApiState<string> = { status: "error", error: new Error("network down") };
    render(<DataState state={state} render={(data) => <div>{data}</div>} />);
    expect(screen.getByText("Could not load this data")).toBeInTheDocument();
  });

  it("renders the success content via render prop", () => {
    const state: ApiState<string> = { status: "success", data: "hello world" };
    render(<DataState state={state} render={(data) => <div>{data}</div>} />);
    expect(screen.getByText("hello world")).toBeInTheDocument();
  });
});
