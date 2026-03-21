"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";

interface SessionSummary {
  id: string;
  language: string;
  mode: string;
  topic: string;
  status: string;
  feedback_status: string | null;
  started_at: string;
  ended_at: string | null;
}

export default function SessionsPage() {
  const [sessions, setSessions] = useState<SessionSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const router = useRouter();

  useEffect(() => {
    const fetchSessions = async () => {
      try {
        const response = await apiClient.get("/sessions");
        const data = await response.json();
        setSessions(data.sessions);
      } catch (error) {
        console.error("Failed to fetch sessions:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchSessions();
  }, []);

  if (loading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">Loading sessions...</p>
      </div>
    );
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
        <p className="text-gray-500">No sessions yet. Start your first conversation!</p>
      ) : (
        <div className="flex flex-col gap-3">
          {sessions.map((session) => (
            <button
              key={session.id}
              onClick={() => router.push(`/sessions/${session.id}`)}
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
                  {session.status}
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
