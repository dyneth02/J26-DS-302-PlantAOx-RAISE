import { afterEach, describe, expect, it, vi } from "vitest";
import { c4Api } from "@/features/c4-screen/services/api";

describe("C4 API client", () => {
  afterEach(() => vi.restoreAllMocks());

  it("uses the shared versioned API and preserves mock provenance", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ cloud: { source: "mock_cloud", n: 500, status: "mock" }, warnings: ["MOCK"] }),
    } as Response);
    const result = await c4Api.meta();
    expect(fetchMock).toHaveBeenCalledWith("/api/v1/c4/meta", expect.objectContaining({ method: "GET" }));
    expect(result.cloud.source).toBe("mock_cloud");
  });

  it("encodes filters and pagination into the endpoint request", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ items: [], total: 0, page: 2, page_size: 25 }),
    } as Response);
    await c4Api.candidates({ plant: "rice", tier: 1, cs_min: 0.5, q: "YV", page: 2, page_size: 25 });
    const path = String(fetchMock.mock.calls[0][0]);
    expect(path).toContain("/api/v1/c4/candidates?");
    expect(path).toContain("plant=rice");
    expect(path).toContain("cs_min=0.5");
    expect(path).toContain("page_size=25");
  });
});
