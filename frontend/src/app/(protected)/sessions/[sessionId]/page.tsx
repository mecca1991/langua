"use client";

import { useParams, useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";
import { useApiQuery } from "@/hooks/useApiQuery";
import { TranscriptPanel } from "@/components/TranscriptPanel";
import { FeedbackCard } from "@/components/FeedbackCard";
import type { SessionDetail } from "@/lib/api-types";

export default function SessionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;

  const { data: session, loading, error } = useApiQuery(
    () => apiClient.get<SessionDetail>(`/sessions/${sessionId}`),
    [sessionId],
  );

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">Loading session...</p>
      </div>
    );
  }

  if (error || !session) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
        <p className="text-red-600">{error ?? "Session not found."}</p>
        <button
          onClick={() => router.push("/sessions")}
          className="text-sm text-blue-600 hover:text-blue-700"
        >
          Back to sessions
        </button>
      </div>
    );
  }

  const isActive = session.status === "active";
  const isQuiz = session.mode === "quiz";
  const hasFeedback = session.feedback && session.feedback.length > 0;

  return (
    <div className="mx-auto max-w-2xl p-8">
      <button
        onClick={() => router.push("/sessions")}
        className="mb-4 text-sm text-blue-600 hover:text-blue-700"
      >
        &larr; Back to sessions
      </button>

      <div className="mb-6">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold">{session.topic}</h1>
          <span
            className={`rounded-full px-2 py-1 text-xs font-medium ${
              isActive
                ? "bg-green-100 text-green-700"
                : "bg-gray-100 text-gray-600"
            }`}
          >
            {isActive ? "Active" : "Ended"}
          </span>
        </div>
        <p className="text-sm text-gray-500">
          {isQuiz ? "Quiz" : "Learn"} &middot;{" "}
          {new Date(session.started_at).toLocaleDateString()}
        </p>
      </div>

      {isActive && (
        <div className="mb-6">
          <button
            onClick={() => router.push(`/conversation/${sessionId}`)}
            className="rounded-lg bg-green-600 px-6 py-2 text-sm font-medium text-white shadow-md hover:bg-green-700"
          >
            Continue conversation
          </button>
        </div>
      )}

      <div className="mb-8">
        <h2 className="mb-3 text-lg font-semibold">Transcript</h2>
        <TranscriptPanel entries={session.transcript} />
      </div>

      {hasFeedback && (
        <div className="mb-6">
          <h2 className="mb-3 text-lg font-semibold">Feedback</h2>
          <FeedbackCard feedback={session.feedback[0]} />
        </div>
      )}

      {!isActive &&
        isQuiz &&
        !hasFeedback &&
        (session.feedback_status === "pending" ||
          session.feedback_status === "failed") && (
          <div className="mb-6">
            <button
              onClick={() => router.push(`/results/${sessionId}`)}
              className="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white shadow-md hover:bg-blue-700"
            >
              {session.feedback_status === "pending"
                ? "View pending results"
                : "Retry feedback"}
            </button>
          </div>
        )}
    </div>
  );
}
