"use client";

import { useEffect, useState, useRef } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";
import { FeedbackCard, FeedbackData } from "@/components/FeedbackCard";

type FeedbackStatus = "pending" | "ready" | "failed" | null;

export default function ResultsPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;

  const [feedbackStatus, setFeedbackStatus] = useState<FeedbackStatus>("pending");
  const [feedback, setFeedback] = useState<FeedbackData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [retrying, setRetrying] = useState(false);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const response = await apiClient.get(
          `/sessions/${sessionId}/feedback-status`,
        );
        const data = await response.json();
        setFeedbackStatus(data.feedback_status);

        if (data.feedback_status === "ready") {
          if (intervalRef.current) clearInterval(intervalRef.current);
          const sessionResponse = await apiClient.get(`/sessions/${sessionId}`);
          const sessionData = await sessionResponse.json();
          if (sessionData.feedback) {
            setFeedback(sessionData.feedback);
          }
        } else if (data.feedback_status === "failed") {
          if (intervalRef.current) clearInterval(intervalRef.current);
        }
      } catch {
        setError("Failed to check feedback status");
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 3000);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [sessionId]);

  const handleRetry = async () => {
    setRetrying(true);
    setError(null);
    try {
      await apiClient.post(`/sessions/${sessionId}/retry-feedback`);
      setFeedbackStatus("pending");
      intervalRef.current = setInterval(async () => {
        const response = await apiClient.get(
          `/sessions/${sessionId}/feedback-status`,
        );
        const data = await response.json();
        setFeedbackStatus(data.feedback_status);
        if (data.feedback_status === "ready" || data.feedback_status === "failed") {
          if (intervalRef.current) clearInterval(intervalRef.current);
          if (data.feedback_status === "ready") {
            const sessionResponse = await apiClient.get(`/sessions/${sessionId}`);
            const sessionData = await sessionResponse.json();
            if (sessionData.feedback) {
              setFeedback(sessionData.feedback);
            }
          }
        }
      }, 3000);
    } catch {
      setError("Failed to retry");
    } finally {
      setRetrying(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 p-8">
      <h1 className="text-2xl font-bold">Quiz Results</h1>

      {feedbackStatus === "pending" && (
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-blue-600 border-t-transparent" />
          <p className="text-gray-500">Processing your results...</p>
        </div>
      )}

      {feedbackStatus === "ready" && feedback && (
        <FeedbackCard feedback={feedback} />
      )}

      {feedbackStatus === "failed" && (
        <div className="flex flex-col items-center gap-3">
          <p className="text-red-500">
            Failed to generate feedback. Please try again.
          </p>
          {error && <p className="text-sm text-red-400">{error}</p>}
          <button
            onClick={handleRetry}
            disabled={retrying}
            className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
          >
            {retrying ? "Retrying..." : "Retry"}
          </button>
        </div>
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
