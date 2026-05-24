/**
 * Unit tests for the browser Agent API client.
 *
 * These tests make sure the static frontend calls only the configured Agent
 * API shape and does not sneak a browser-visible secret into requests.
 */
import { describe, expect, it, vi } from "vitest";
import { AgentApiClient, queryString } from "./apiClient.js";
import { normalizeUrl } from "./config.js";

describe("runtime config helpers", () => {
  it("normalizes Agent API URLs", () => {
    expect(normalizeUrl("http://localhost:8090///")).toBe("http://localhost:8090");
  });
});

describe("queryString", () => {
  it("skips empty params and encodes present values", () => {
    expect(queryString({ section: "Item 1A", empty: "", ticker: null })).toBe(
      "?section=Item+1A",
    );
  });
});

describe("AgentApiClient", () => {
  it("calls health without browser-visible auth headers", async () => {
    const fetchImpl = vi.fn(async () => ({
      ok: true,
      text: async () => JSON.stringify({ status: "ok" }),
    }));
    const client = new AgentApiClient({
      baseUrl: "http://localhost:8090",
      fetchImpl,
    });

    await expect(client.health()).resolves.toEqual({ status: "ok" });
    expect(fetchImpl).toHaveBeenCalledWith("http://localhost:8090/health", {
      method: "GET",
      headers: {},
      body: undefined,
    });
  });
});
