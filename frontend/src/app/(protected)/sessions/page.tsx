"use client";

import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";
import { useApiQuery } from "@/hooks/useApiQuery";
import type { SessionSummary, SessionListResponse } from "@/lib/api-types";

export default function SessionsPage() {
  const router = useRouter();

  const { data, loading, error } = useApiQuery(
    () => apiClient.get<SessionListResponse>("/sessions"),
    [],
  );

  const sessions: SessionSummary[] = data?.sessions ?? [];

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">Loading sessions...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
        <p className="text-red-600">{error}</p>
        <button
          onClick={() => router.push("/")}
          className="text-sm text-blue-600 hover:text-blue-700"
        >
          Back to Home
        </button>
      </div>
    );
  }

  function sessionHref(session: SessionSummary): string {
    if (session.status === "active") {
      return `/conversation/${session.id}`;
    }
    return `/sessions/${session.id}`;
  }

  return (
    <div className="mx-auto max-w-2xl p-8">
      <div className="mb-6 flex items-center justify-between">
        <h1 className="text-2xl font-bold">Session History</h1>
        <button
          onClick={() => router.push("/")}
          className="text-sm text-blue-600 hover:text-blue-700"
        >
          New Session
        </button>
      </div>

      {sessions.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-12">
          <p className="text-gray-500">No sessions yet.</p>
          <button
            onClick={() => router.push("/")}
            className="rounded-lg bg-green-600 px-6 py-2 text-sm font-medium text-white shadow-md hover:bg-green-700"
          >
            Start your first conversation
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-3">
          {sessions.map((session) => (
            <button
              key={session.id}
              onClick={() => router.push(sessionHref(session))}
              className="flex items-center justify-between rounded-lg border border-gray-200 bg-white p-4 text-left shadow-sm hover:border-blue-300 hover:shadow-md transition"
            >
              <div>
                <p className="font-medium text-gray-900">{session.topic}</p>
                <p className="text-sm text-gray-500">
                  {session.mode === "quiz" ? "Quiz" : "Learn"} &middot;{" "}
                  {new Date(session.started_at).toLocaleDateString()}
                </p>
              </div>
              <div className="flex items-center gap-2">
                <span
                  className={`rounded-full px-2 py-1 text-xs font-medium ${
                    session.status === "active"
                      ? "bg-green-100 text-green-700"
                      : "bg-gray-100 text-gray-600"
                  }`}
                >
                  {session.status === "active" ? "Active" : "Ended"}
                </span>
                {session.feedback_status === "ready" && (
                  <span className="rounded-full bg-blue-100 px-2 py-1 text-xs font-medium text-blue-700">
                    Feedback ready
                  </span>
                )}
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
