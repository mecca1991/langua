import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("./supabase", () => ({
  supabase: {
    auth: {
      getSession: vi.fn(),
    },
  },
}));

import { apiClient, ApiError } from "./api";
import { supabase } from "./supabase";

function mockSession(token: string) {
  vi.mocked(supabase.auth.getSession).mockResolvedValue({
    data: { session: { access_token: token } },
    error: null,
  } as ReturnType<typeof supabase.auth.getSession> extends Promise<infer R>
    ? R
    : never);
}

describe("apiClient", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    global.fetch = vi.fn();
  });

  it("attaches Bearer token from Supabase session", async () => {
    mockSession("test-token-123");

    vi.mocked(global.fetch).mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), { status: 200 }),
    );

    await apiClient.get("/health");

    expect(vi.mocked(global.fetch)).toHaveBeenCalledWith(
      expect.stringContaining("/health"),
      expect.objectContaining({
        headers: expect.objectContaining({
          Authorization: "Bearer test-token-123",
        }),
      }),
    );
  });

  it("throws ApiError with NO_SESSION when no session exists", async () => {
    vi.mocked(supabase.auth.getSession).mockResolvedValue({
      data: { session: null },
      error: null,
    } as ReturnType<typeof supabase.auth.getSession> extends Promise<infer R>
      ? R
      : never);

    try {
      await apiClient.get("/health");
      expect.fail("should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.errorCode).toBe("NO_SESSION");
      expect(apiErr.message).toBe("Not authenticated");
    }
  });

  it("throws ApiError with NETWORK_FAILURE when fetch rejects", async () => {
    mockSession("tok");

    vi.mocked(global.fetch).mockRejectedValue(new TypeError("Failed to fetch"));

    try {
      await apiClient.get("/test");
      expect.fail("should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.errorCode).toBe("NETWORK_FAILURE");
      expect(apiErr.status).toBe(0);
    }
  });

  it("returns parsed JSON on success", async () => {
    mockSession("tok");

    vi.mocked(global.fetch).mockResolvedValue(
      new Response(JSON.stringify({ session_id: "abc-123" }), { status: 200 }),
    );

    const data = await apiClient.get<{ session_id: string }>("/test");
    expect(data.session_id).toBe("abc-123");
  });

  it("throws ApiError on non-ok response with backend error payload", async () => {
    mockSession("tok");

    vi.mocked(global.fetch).mockResolvedValue(
      new Response(
        JSON.stringify({
          error_type: "AUTHENTICATION_ERROR",
          error_code: "INVALID_AUTH",
          error_message: "Token expired",
          request_id: "req-1",
        }),
        { status: 401 },
      ),
    );

    try {
      await apiClient.get("/test");
      expect.fail("should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(401);
      expect(apiErr.errorType).toBe("AUTHENTICATION_ERROR");
      expect(apiErr.errorCode).toBe("INVALID_AUTH");
      expect(apiErr.message).toBe("Token expired");
      expect(apiErr.requestId).toBe("req-1");
    }
  });

  it("throws ApiError with fallback fields when error body is unparseable", async () => {
    mockSession("tok");

    vi.mocked(global.fetch).mockResolvedValue(
      new Response("not json", { status: 500 }),
    );

    try {
      await apiClient.get("/test");
      expect.fail("should have thrown");
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError);
      const apiErr = err as ApiError;
      expect(apiErr.status).toBe(500);
      expect(apiErr.errorCode).toBe("UNPARSEABLE_RESPONSE");
    }
  });
});
