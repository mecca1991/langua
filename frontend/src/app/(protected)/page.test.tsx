import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, fireEvent } from "@testing-library/react";

const mockPush = vi.fn();

let mockAuthUser: { id: string } | null = { id: "123" };
let mockAuthLoading = false;

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({
    user: mockAuthUser,
    loading: mockAuthLoading,
    signOut: vi.fn(),
  }),
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
  }),
}));

const mockGet = vi.fn();
const mockPost = vi.fn();

vi.mock("@/lib/api", () => ({
  apiClient: {
    get: (...args: unknown[]) => mockGet(...args),
    post: (...args: unknown[]) => mockPost(...args),
  },
}));

import { HomePage } from "@/components/HomePage";

describe("HomePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuthUser = { id: "123" };
    mockAuthLoading = false;
    mockGet.mockResolvedValue({
      topics: ["Greetings", "Ordering Food", "Directions"],
      language: "ja",
    });
  });

  it("does not fetch topics while auth is loading", async () => {
    mockAuthLoading = true;
    render(<HomePage />);

    // Flush microtasks to let any fetch fire
    await new Promise((r) => setTimeout(r, 50));

    expect(mockGet).not.toHaveBeenCalled();
    expect(screen.getByText("Loading topics...")).toBeDefined();
  });

  it("does not fetch topics when there is no user session", async () => {
    mockAuthUser = null;
    render(<HomePage />);

    await new Promise((r) => setTimeout(r, 50));

    expect(mockGet).not.toHaveBeenCalled();
  });

  it("fetches topics after auth resolves with a user", async () => {
    render(<HomePage />);

    await waitFor(() => {
      expect(mockGet).toHaveBeenCalledWith(
        expect.stringContaining("/topics"),
      );
      expect(screen.getByRole("combobox")).toBeDefined();
    });
  });

  it("renders mode selector with Learn and Quiz", async () => {
    render(<HomePage />);
    await waitFor(() => {
      expect(screen.getByText("Learn")).toBeDefined();
      expect(screen.getByText("Quiz")).toBeDefined();
    });
  });

  it("renders topic dropdown after topics load", async () => {
    render(<HomePage />);
    await waitFor(() => {
      expect(screen.getByRole("combobox")).toBeDefined();
    });
  });

  it("renders language showing Japanese after topics load", async () => {
    render(<HomePage />);
    await waitFor(() => {
      expect(screen.getByText(/japanese/i)).toBeDefined();
    });
  });

  it("shows error when topic fetch fails", async () => {
    mockGet.mockRejectedValue(new Error("Network error"));
    render(<HomePage />);

    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeDefined();
    });
  });

  it("calls API and navigates on successful start", async () => {
    mockPost.mockResolvedValue({ session_id: "new-sess-1" });
    render(<HomePage />);

    await waitFor(() => {
      expect(screen.getByRole("combobox")).toBeDefined();
    });

    const startButton = screen.getByRole("button", { name: /start/i });
    fireEvent.click(startButton);

    await waitFor(() => {
      expect(mockPost).toHaveBeenCalledWith("/conversation/start", {
        language: "ja",
        mode: "learn",
        topic: "Greetings",
      });
      expect(mockPush).toHaveBeenCalledWith("/conversation/new-sess-1");
    });
  });

  it("shows error when start session fails", async () => {
    mockPost.mockRejectedValue(new Error("Server unavailable"));
    render(<HomePage />);

    await waitFor(() => {
      expect(screen.getByRole("combobox")).toBeDefined();
    });

    const startButton = screen.getByRole("button", { name: /start/i });
    fireEvent.click(startButton);

    await waitFor(() => {
      expect(screen.getByText("Server unavailable")).toBeDefined();
    });
  });

  it("disables start button while topics are loading", () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    render(<HomePage />);

    const startButton = screen.getByRole("button", { name: /start/i });
    expect(startButton.hasAttribute("disabled")).toBe(true);
  });
});
