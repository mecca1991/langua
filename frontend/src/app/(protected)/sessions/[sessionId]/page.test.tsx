import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useParams: () => ({ sessionId: "sess-1" }),
  useRouter: () => ({ push: vi.fn() }),
}));

const mockGet = vi.fn();

vi.mock("@/lib/api", () => {
  class ApiError extends Error {
    readonly status: number;
    readonly errorType: string;
    readonly errorCode: string;
    readonly requestId: string | null;
    constructor(
      payload: {
        error_type: string;
        error_code: string;
        error_message: string;
        request_id: string | null;
      },
      status: number,
    ) {
      super(payload.error_message);
      this.name = "ApiError";
      this.status = status;
      this.errorType = payload.error_type;
      this.errorCode = payload.error_code;
      this.requestId = payload.request_id;
    }
  }
  return {
    apiClient: {
      get: (...args: unknown[]) => mockGet(...args),
    },
    ApiError,
  };
});

import SessionDetailPage from "./page";

const endedSession = {
  id: "sess-1",
  language: "ja",
  mode: "learn",
  topic: "Ordering Food",
  status: "ended",
  feedback_status: null,
  started_at: "2026-03-22T10:00:00Z",
  ended_at: "2026-03-22T10:05:00Z",
  transcript: [{ role: "user", text_en: "I want ramen", turn_index: 0 }],
  feedback: [],
};

describe("SessionDetailPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    render(<SessionDetailPage />);
    expect(screen.getByText("Loading session...")).toBeDefined();
  });

  it("renders session detail on success", async () => {
    mockGet.mockResolvedValue(endedSession);
    render(<SessionDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Ordering Food")).toBeDefined();
      expect(screen.getByText("Ended")).toBeDefined();
      expect(screen.getByText("I want ramen")).toBeDefined();
    });
  });

  it("shows error message on fetch failure", async () => {
    mockGet.mockRejectedValue(new Error("Server error"));
    render(<SessionDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Server error")).toBeDefined();
      expect(screen.getByText("Back to sessions")).toBeDefined();
    });
  });

  it("shows continue button for active session", async () => {
    mockGet.mockResolvedValue({
      ...endedSession,
      status: "active",
      ended_at: null,
    });
    render(<SessionDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("Active")).toBeDefined();
      expect(
        screen.getByRole("button", { name: /continue conversation/i }),
      ).toBeDefined();
    });
  });

  it("shows feedback when available", async () => {
    mockGet.mockResolvedValue({
      ...endedSession,
      feedback_status: "ready",
      feedback: [
        {
          correct: ["arigatou"],
          revisit: ["sumimasen"],
          drills: ["Practice"],
        },
      ],
    });
    render(<SessionDetailPage />);

    await waitFor(() => {
      expect(screen.getByText("arigatou")).toBeDefined();
      expect(screen.getByText("sumimasen")).toBeDefined();
    });
  });
});
