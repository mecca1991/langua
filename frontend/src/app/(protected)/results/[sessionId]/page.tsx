"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiClient, ApiError } from "@/lib/api";
import { FeedbackCard } from "@/components/FeedbackCard";
import type {
  FeedbackStatusResponse,
  SessionDetail,
  SessionFeedback,
} from "@/lib/api-types";

type PageStatus =
  | "loading"
  | "error"
  | "no_feedback"
  | "pending"
  | "ready"
  | "failed"
  | "retrying";

const POLL_INTERVAL_MS = 3000;

export default function ResultsPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;

  const [status, setStatus] = useState<PageStatus>("loading");
  const [feedback, setFeedback] = useState<SessionFeedback | null>(null);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const pollerRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPolling = useCallback(() => {
    if (pollerRef.current) {
      clearInterval(pollerRef.current);
      pollerRef.current = null;
    }
  }, []);

  const pollOnce = useCallback(async (): Promise<boolean> => {
    const data = await apiClient.get<FeedbackStatusResponse>(
      `/sessions/${sessionId}/feedback-status`,
    );

    if (data.feedback_status === "ready") {
      const session = await apiClient.get<SessionDetail>(
        `/sessions/${sessionId}`,
      );
      if (session.feedback && session.feedback.length > 0) {
        setFeedback(session.feedback[0]);
        setStatus("ready");
      } else {
        setErrorMsg("Feedback was marked as ready but no data was returned.");
        setStatus("error");
      }
      return true;
    }

    if (data.feedback_status === "failed") {
      setStatus("failed");
      return true;
    }

    return false;
  }, [sessionId]);

  const startPolling = useCallback(() => {
    stopPolling();
    pollerRef.current = setInterval(async () => {
      try {
        const done = await pollOnce();
        if (done) stopPolling();
      } catch {
        stopPolling();
        setErrorMsg("Lost connection while checking feedback status.");
        setStatus("error");
      }
    }, POLL_INTERVAL_MS);
  }, [pollOnce, stopPolling]);

  // --- Load session on mount ---
  useEffect(() => {
    const loadSession = async () => {
      try {
        const session = await apiClient.get<SessionDetail>(
          `/sessions/${sessionId}`,
        );

        if (session.feedback_status === "ready") {
          if (session.feedback && session.feedback.length > 0) {
            setFeedback(session.feedback[0]);
            setStatus("ready");
          } else {
            setErrorMsg(
              "Feedback was marked as ready but no data was returned.",
            );
            setStatus("error");
          }
          return;
        }

        if (session.feedback_status === "pending") {
          setStatus("pending");
          startPolling();
          return;
        }

        if (session.feedback_status === "failed") {
          setStatus("failed");
          return;
        }

        // null or unexpected value — no feedback for this session
        setStatus("no_feedback");
      } catch (err) {
        if (err instanceof ApiError) {
          if (err.status === 404) {
            setErrorMsg("Session not found.");
          } else if (err.status === 403) {
            setErrorMsg("You do not have access to this session.");
          } else {
            setErrorMsg(err.message);
          }
        } else {
          setErrorMsg(
            err instanceof Error ? err.message : "Failed to load session",
          );
        }
        setStatus("error");
      }
    };

    loadSession();
    return stopPolling;
  }, [sessionId, startPolling, stopPolling]);

  // --- Retry ---
  const retryingRef = useRef(false);
  const handleRetry = async () => {
    if (retryingRef.current) return;
    retryingRef.current = true;
    setStatus("retrying");
    setErrorMsg(null);
    try {
      await apiClient.post<{ status: string }>(
        `/sessions/${sessionId}/retry-feedback`,
      );
      retryingRef.current = false;
      setStatus("pending");
      startPolling();
    } catch (err) {
      retryingRef.current = false;
      setErrorMsg(err instanceof Error ? err.message : "Failed to retry");
      setStatus("failed");
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-2xl font-bold">Quiz Results</h1>

      {status === "loading" && (
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
          <p className="text-gray-500">Loading...</p>
        </div>
      )}

      {(status === "pending" || status === "retrying") && (
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
          <p className="text-gray-500">
            {status === "retrying"
              ? "Retrying feedback generation..."
              : "Processing your results..."}
          </p>
        </div>
      )}

      {status === "ready" && feedback && <FeedbackCard feedback={feedback} />}

      {status === "failed" && (
        <div className="flex flex-col items-center gap-3">
          <p className="text-red-500">
            Failed to generate feedback. Please try again.
          </p>
          {errorMsg && <p className="text-sm text-red-400">{errorMsg}</p>}
          <button
            onClick={handleRetry}
            className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            Retry
          </button>
        </div>
      )}

      {status === "error" && (
        <p className="text-red-600">{errorMsg ?? "An error occurred."}</p>
      )}

      {status === "no_feedback" && (
        <p className="text-gray-500">
          No feedback is available for this session.
        </p>
      )}

      <button
        onClick={() => router.push("/")}
        className="mt-4 text-sm text-gray-400 hover:text-gray-600"
      >
        Back to Home
      </button>
    </div>
  );
}
