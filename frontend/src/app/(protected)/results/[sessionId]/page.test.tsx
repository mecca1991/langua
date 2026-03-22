import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

vi.mock("next/navigation", () => ({
  useParams: () => ({ sessionId: "sess-1" }),
  useRouter: () => ({ push: vi.fn() }),
}));

const mockGet = vi.fn();
const mockPost = vi.fn();

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
      post: (...args: unknown[]) => mockPost(...args),
    },
    ApiError,
  };
});

import { ApiError } from "@/lib/api";
import ResultsPage from "./page";

function apiError(message: string, status: number) {
  return new ApiError(
    { error_type: "", error_code: "", error_message: message, request_id: null },
    status,
  );
}

function makeSession(overrides: Record<string, unknown>) {
  return {
    id: "sess-1",
    language: "ja",
    mode: "quiz",
    topic: "Greetings",
    status: "ended",
    feedback_status: null,
    started_at: "2026-03-22T10:00:00Z",
    ended_at: "2026-03-22T10:05:00Z",
    transcript: [],
    feedback: [],
    ...overrides,
  };
}

describe("ResultsPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    render(<ResultsPage />);
    expect(screen.getByText("Loading...")).toBeDefined();
  });

  it("shows feedback immediately when status is ready", async () => {
    mockGet.mockResolvedValue(
      makeSession({
        feedback_status: "ready",
        feedback: [
          {
            correct: ["konnichiwa"],
            revisit: ["sumimasen"],
            drills: ["Practice"],
          },
        ],
      }),
    );
    render(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText("konnichiwa")).toBeDefined();
      expect(screen.getByText("sumimasen")).toBeDefined();
    });
  });

  it("shows processing state when feedback is pending", async () => {
    mockGet.mockResolvedValue(makeSession({ feedback_status: "pending" }));
    render(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText("Processing your results...")).toBeDefined();
    });
  });

  it("shows retry button when feedback has failed", async () => {
    mockGet.mockResolvedValue(makeSession({ feedback_status: "failed" }));
    render(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText(/failed to generate feedback/i)).toBeDefined();
      expect(screen.getByRole("button", { name: /retry/i })).toBeDefined();
    });
  });

  it("shows no-feedback state for learn mode sessions", async () => {
    mockGet.mockResolvedValue(
      makeSession({ mode: "learn", feedback_status: null }),
    );
    render(<ResultsPage />);

    await waitFor(() => {
      expect(
        screen.getByText(/no feedback is available/i),
      ).toBeDefined();
    });
  });

  it("shows error when session is not found (404)", async () => {
    mockGet.mockRejectedValue(apiError("Session not found.", 404));
    render(<ResultsPage />);

    await waitFor(() => {
      expect(screen.getByText("Session not found.")).toBeDefined();
    });
  });

  it("shows error when ready but feedback array is empty", async () => {
    mockGet.mockResolvedValue(
      makeSession({ feedback_status: "ready", feedback: [] }),
    );
    render(<ResultsPage />);

    await waitFor(() => {
      expect(
        screen.getByText(/feedback was marked as ready but no data/i),
      ).toBeDefined();
    });
  });
});
