"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";
import { TranscriptPanel, TranscriptEntry } from "@/components/TranscriptPanel";
import { FeedbackCard, FeedbackData } from "@/components/FeedbackCard";

interface SessionDetail {
  id: string;
  language: string;
  mode: string;
  topic: string;
  status: string;
  feedback_status: string | null;
  started_at: string;
  ended_at: string | null;
  transcript: TranscriptEntry[];
  feedback: FeedbackData[];
}

export default function SessionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;

  const [session, setSession] = useState<SessionDetail | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchSession = async () => {
      try {
        const response = await apiClient.get(`/sessions/${sessionId}`);
        const data = await response.json();
        setSession(data);
      } catch (error) {
        console.error("Failed to fetch session:", error);
      } finally {
        setLoading(false);
      }
    };
    fetchSession();
  }, [sessionId]);

  if (loading || !session) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <p className="text-gray-500">Loading session...</p>
      </div>
    );
  }

  return (
    <div className="mx-auto max-w-2xl p-8">
      <button
        onClick={() => router.push("/sessions")}
        className="mb-4 text-sm text-blue-600 hover:text-blue-700"
      >
        &larr; Back to sessions
      </button>

      <div className="mb-6">
        <h1 className="text-2xl font-bold">{session.topic}</h1>
        <p className="text-sm text-gray-500">
          {session.mode === "quiz" ? "Quiz" : "Learn"} &middot;{" "}
          {new Date(session.started_at).toLocaleDateString()}
        </p>
      </div>

      <div className="mb-8">
        <h2 className="mb-3 text-lg font-semibold">Transcript</h2>
        <TranscriptPanel entries={session.transcript} />
      </div>

      {session.feedback && session.feedback.length > 0 && (
        <div>
          <h2 className="mb-3 text-lg font-semibold">Feedback</h2>
          <FeedbackCard feedback={session.feedback[0]} />
        </div>
      )}
    </div>
  );
}
