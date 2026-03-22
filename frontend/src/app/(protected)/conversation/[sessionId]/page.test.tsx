import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";

// jsdom does not implement Element.scrollTo
Element.prototype.scrollTo = vi.fn();

const mockPush = vi.fn();
vi.mock("next/navigation", () => ({
  useParams: () => ({ sessionId: "sess-1" }),
  useRouter: () => ({ push: mockPush }),
}));

vi.mock("@/hooks/useRecorder", () => ({
  useRecorder: () => ({
    isRecording: false,
    startRecording: vi.fn(),
    stopRecording: vi.fn(),
    audioBlob: null,
    error: null,
  }),
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
      post: vi.fn(),
      postFormData: vi.fn(),
    },
    ApiError,
  };
});

import ConversationPage from "./page";

const activeSession = {
  id: "sess-1",
  language: "ja",
  mode: "learn",
  topic: "Greetings",
  status: "active",
  feedback_status: null,
  started_at: "2026-03-22T10:00:00Z",
  ended_at: null,
  transcript: [
    { role: "user", text_en: "Hello", turn_index: 0 },
    {
      role: "assistant",
      text_en: "Here is hello:",
      text_native: "こんにちは",
      turn_index: 1,
    },
  ],
  feedback: [],
};

const endedSession = {
  ...activeSession,
  status: "ended",
  ended_at: "2026-03-22T10:05:00Z",
};

describe("ConversationPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("shows loading state initially", () => {
    mockGet.mockReturnValue(new Promise(() => {}));
    render(<ConversationPage />);
    expect(screen.getByText("Loading session...")).toBeDefined();
  });

  it("renders transcript from loaded session", async () => {
    mockGet.mockResolvedValue(activeSession);
    render(<ConversationPage />);

    await waitFor(() => {
      expect(screen.getByText("Hello")).toBeDefined();
      expect(screen.getByText("こんにちは")).toBeDefined();
    });
  });

  it("shows recording controls for active session", async () => {
    mockGet.mockResolvedValue(activeSession);
    render(<ConversationPage />);

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /start recording/i }),
      ).toBeDefined();
      expect(screen.getByText("Tap to speak")).toBeDefined();
    });
  });

  it("shows error message when session load fails", async () => {
    mockGet.mockRejectedValue(new Error("Network down"));
    render(<ConversationPage />);

    await waitFor(() => {
      expect(screen.getByText("Network down")).toBeDefined();
      expect(screen.getByText("Back to Home")).toBeDefined();
    });
  });

  it("shows read-only view for ended session", async () => {
    mockGet.mockResolvedValue(endedSession);
    render(<ConversationPage />);

    await waitFor(() => {
      expect(screen.getByText(/ended/i)).toBeDefined();
      expect(screen.getByText("Hello")).toBeDefined();
      expect(
        screen.queryByRole("button", { name: /start recording/i }),
      ).toBeNull();
    });
  });

  it("shows end session button for active session", async () => {
    mockGet.mockResolvedValue(activeSession);
    render(<ConversationPage />);

    await waitFor(() => {
      expect(
        screen.getByRole("button", { name: /end session/i }),
      ).toBeDefined();
    });
  });
});
