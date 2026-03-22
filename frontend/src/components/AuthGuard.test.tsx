import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

const mockReplace = vi.fn();

vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: mockReplace }),
  usePathname: () => "/conversation/123",
}));

// Mock window.location.search for returnTo capture
Object.defineProperty(window, "location", {
  value: { ...window.location, search: "?foo=bar" },
  writable: true,
});

let mockUser: { id: string } | null = null;
let mockLoading = false;

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({
    user: mockUser,
    loading: mockLoading,
  }),
}));

import { AuthGuard } from "./AuthGuard";

describe("AuthGuard", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockUser = null;
    mockLoading = false;
  });

  it("renders children when user is authenticated", () => {
    mockUser = { id: "user-1" };
    render(
      <AuthGuard>
        <p>Protected content</p>
      </AuthGuard>,
    );
    expect(screen.getByText("Protected content")).toBeDefined();
  });

  it("shows loading state while auth is resolving", () => {
    mockLoading = true;
    render(
      <AuthGuard>
        <p>Protected content</p>
      </AuthGuard>,
    );
    expect(screen.getByText("Loading...")).toBeDefined();
    expect(screen.queryByText("Protected content")).toBeNull();
  });

  it("redirects to sign-in with returnTo when unauthenticated", async () => {
    mockUser = null;
    render(
      <AuthGuard>
        <p>Protected content</p>
      </AuthGuard>,
    );

    await waitFor(() => {
      expect(mockReplace).toHaveBeenCalledWith(
        "/sign-in?returnTo=%2Fconversation%2F123%3Ffoo%3Dbar",
      );
    });
  });

  it("does not render children when unauthenticated", () => {
    mockUser = null;
    render(
      <AuthGuard>
        <p>Protected content</p>
      </AuthGuard>,
    );
    expect(screen.queryByText("Protected content")).toBeNull();
  });
});
