import { afterEach, expect, it, vi } from "vitest";
import { c3Api } from "@/features/c3-aop-bcs/services/api";

afterEach(() => vi.restoreAllMocks());

it("uses the shared versioned API convention", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({ ok: true, json: async () => ({ status: "ok" }) } as Response);
  await c3Api.health();
  expect(fetchMock).toHaveBeenCalledWith("/api/v1/c3/health", expect.objectContaining({ method: "GET" }));
});

it("loads the typed dashboard contract from C3", async () => {
  const fetchMock = vi.spyOn(globalThis, "fetch").mockResolvedValue({ ok: true, json: async () => ({ apiVersion: "c3-dashboard-api-v1" }) } as Response);
  const response = await c3Api.dashboard();
  expect(fetchMock).toHaveBeenCalledWith("/api/v1/c3/dashboard", expect.objectContaining({ method: "GET" }));
  expect(response.apiVersion).toBe("c3-dashboard-api-v1");
});
