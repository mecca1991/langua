import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("./supabase", () => ({
  supabase: {
    auth: {
      getSession: vi.fn(),
    },
  },
}));

import { apiClient } from "./api";
import { supabase } from "./supabase";

describe("apiClient", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    global.fetch = vi.fn();
  });

  it("attaches Bearer token from Supabase session", async () => {
    const mockGetSession = vi.mocked(supabase.auth.getSession);
    mockGetSession.mockResolvedValue({
      data: {
        session: { access_token: "test-token-123" },
      },
      error: null,
    } as any);

    const mockFetch = vi.mocked(global.fetch);
    mockFetch.mockResolvedValue(new Response(JSON.stringify({ ok: true }), { status: 200 }));

    await apiClient.get("/health");

    expect(mockFetch).toHaveBeenCalledWith(
      expect.stringContaining("/health"),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer test-token-123",
        }),
      }),
    );
  });

  it("throws when no session exists", async () => {
    const mockGetSession = vi.mocked(supabase.auth.getSession);
    mockGetSession.mockResolvedValue({
      data: { session: null },
      error: null,
    } as any);

    await expect(apiClient.get("/health")).rejects.toThrow("Not authenticated");
  });
});
