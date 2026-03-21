import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({
    user: { id: "123", email: "test@test.com" },
    loading: false,
    signOut: vi.fn(),
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
}));

vi.mock("@/lib/api", () => ({
  apiClient: {
    post: vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ session_id: "abc-123" }), { status: 200 }),
    ),
  },
}));

import HomePage from "./page";

describe("HomePage", () => {
  it("renders mode selector with Learn and Quiz", () => {
    render(<HomePage />);
    expect(screen.getByText("Learn")).toBeDefined();
    expect(screen.getByText("Quiz")).toBeDefined();
  });

  it("renders topic dropdown", () => {
    render(<HomePage />);
    expect(screen.getByRole("combobox")).toBeDefined();
  });

  it("renders start button", () => {
    render(<HomePage />);
    expect(screen.getByRole("button", { name: /start/i })).toBeDefined();
  });

  it("renders language selector showing Japanese", () => {
    render(<HomePage />);
    expect(screen.getByText(/japanese/i)).toBeDefined();
  });
});
