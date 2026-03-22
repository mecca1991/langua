import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

const mockReplace = vi.fn();
let mockSearchParams = new URLSearchParams();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace }),
  useSearchParams: () => mockSearchParams,
}));

const mockExchangeCode = vi.fn();
const mockSetSession = vi.fn();

vi.mock("@/lib/supabase", () => ({
  supabase: {
    auth: {
      exchangeCodeForSession: (...args: unknown[]) => mockExchangeCode(...args),
      setSession: (...args: unknown[]) => mockSetSession(...args),
    },
  },
}));

import AuthCallbackPage from "./page";

describe("AuthCallbackPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockSearchParams = new URLSearchParams();
  });

  it("shows completing message while processing", () => {
    mockSearchParams = new URLSearchParams("code=test-code");
    mockExchangeCode.mockReturnValue(new Promise(() => {}));
    render(<AuthCallbackPage />);
    expect(screen.getByText("Completing sign-in...")).toBeDefined();
  });

  it("exchanges code and redirects to returnTo on success", async () => {
    mockSearchParams = new URLSearchParams(
      "code=test-code&returnTo=%2Fsessions",
    );
    mockExchangeCode.mockResolvedValue({ error: null });
    render(<AuthCallbackPage />);

    await waitFor(() => {
      expect(mockExchangeCode).toHaveBeenCalledWith("test-code");
      expect(mockReplace).toHaveBeenCalledWith("/sessions");
    });
  });

  it("redirects to / when no returnTo is provided", async () => {
    mockSearchParams = new URLSearchParams("code=valid-code");
    mockExchangeCode.mockResolvedValue({ error: null });
    render(<AuthCallbackPage />);

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith("/");
    });
  });

  it("redirects to sign-in with error on code exchange failure", async () => {
    mockSearchParams = new URLSearchParams("code=bad-code");
    mockExchangeCode.mockResolvedValue({ error: new Error("Invalid code") });
    render(<AuthCallbackPage />);

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith(
        "/sign-in?error=auth_callback_failed",
      );
    });
  });

  it("preserves returnTo on failure redirect", async () => {
    mockSearchParams = new URLSearchParams(
      "code=bad-code&returnTo=%2Fconversation%2F123",
    );
    mockExchangeCode.mockResolvedValue({ error: new Error("fail") });
    render(<AuthCallbackPage />);

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith(
        "/sign-in?error=auth_callback_failed&returnTo=%2Fconversation%2F123",
      );
    });
  });

  it("redirects to sign-in when no code and no hash tokens", async () => {
    mockSearchParams = new URLSearchParams();
    render(<AuthCallbackPage />);

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith(
        "/sign-in?error=auth_callback_failed",
      );
    });
  });
});
