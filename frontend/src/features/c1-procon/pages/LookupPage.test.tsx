import { afterEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { LookupPage } from "@/features/c1-procon/pages/LookupPage";
import type { LookupResponse } from "@/features/c1-procon/types";

const INVALID: LookupResponse = {
  query: "AXZ",
  valid: false,
  problems: ["non-canonical residues: XZ (only the 20 standard amino acids are accepted)"],
  in_benchmark: false,
  record: null,
  composition: {},
  nearest: [],
  notes: [],
};

describe("LookupPage", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("shows why an invalid peptide is refused instead of scoring it", async () => {
    global.fetch = vi.fn().mockResolvedValue({ ok: true, json: async () => INVALID }) as unknown as typeof fetch;
    render(<LookupPage />);

    expect(screen.getByText("Start typing")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("peptide sequence"), { target: { value: "axz" } });

    await waitFor(() => expect(screen.getByText("This input cannot be used")).toBeInTheDocument());
    expect(screen.getByText(/non-canonical residues: XZ/)).toBeInTheDocument();
    expect((global.fetch as unknown as ReturnType<typeof vi.fn>).mock.calls[0][0]).toContain("sequence=axz");
  });
});
