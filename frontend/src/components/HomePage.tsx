"use client";

import { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";
import { useApiQuery } from "@/hooks/useApiQuery";
import type { TopicsResponse, StartConversationResponse } from "@/lib/api-types";

const DEFAULT_LANGUAGE = "ja";

const LANGUAGE_LABELS: Record<string, string> = {
  ja: "Japanese (日本語)",
};

export function HomePage() {
  const [mode, setMode] = useState<"learn" | "quiz">("learn");
  const [topic, setTopic] = useState<string>("");
  const [starting, setStarting] = useState(false);
  const [startError, setStartError] = useState<string | null>(null);
  const router = useRouter();
  const { user, loading: authLoading, signOut } = useAuth();

  const {
    data: topicsData,
    loading: topicsLoading,
    error: topicsError,
  } = useApiQuery(
    () => apiClient.get<TopicsResponse>(`/topics?language=${DEFAULT_LANGUAGE}`),
    [],
    { enabled: !authLoading && !!user },
  );

  const language = topicsData?.language ?? null;
  const topics = useMemo(() => topicsData?.topics ?? [], [topicsData]);

  // Select first topic when data arrives
  useEffect(() => {
    if (topics.length > 0 && !topic) {
      setTopic(topics[0]);
    }
  }, [topics, topic]);

  const handleStart = async () => {
    if (starting || !topic || !language) return;
    setStarting(true);
    setStartError(null);
    try {
      const data = await apiClient.post<StartConversationResponse>(
        "/conversation/start",
        { language, mode, topic },
      );
      router.push(`/conversation/${data.session_id}`);
    } catch (err) {
      setStartError(
        err instanceof Error ? err.message : "Failed to start session",
      );
      setStarting(false);
    }
  };

  const canStart =
    !topicsLoading && !topicsError && topics.length > 0 && !!topic && !!language;

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-8 p-8">
      <h1 className="text-4xl font-bold">Langua</h1>

      <div className="flex gap-3">
        <button
          onClick={() => setMode("learn")}
          className={`rounded-lg px-6 py-3 text-sm font-medium transition ${
            mode === "learn"
              ? "bg-blue-600 text-white"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
        >
          Learn
        </button>
        <button
          onClick={() => setMode("quiz")}
          className={`rounded-lg px-6 py-3 text-sm font-medium transition ${
            mode === "quiz"
              ? "bg-blue-600 text-white"
              : "bg-gray-100 text-gray-700 hover:bg-gray-200"
          }`}
        >
          Quiz
        </button>
      </div>

      <div className="flex flex-col gap-2">
        <label className="text-sm font-medium text-gray-600">Topic</label>
        {topicsLoading ? (
          <p className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-2 text-sm text-gray-400">
            Loading topics...
          </p>
        ) : topicsError ? (
          <p className="rounded-lg border border-red-200 bg-red-50 px-4 py-2 text-sm text-red-600">
            {topicsError}
          </p>
        ) : topics.length === 0 ? (
          <p className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-2 text-sm text-gray-400">
            No topics available
          </p>
        ) : (
          <select
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm"
          >
            {topics.map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <label className="text-sm font-medium text-gray-600">Language</label>
        <span className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-2 text-sm text-gray-500">
          {language
            ? (LANGUAGE_LABELS[language] ?? language)
            : DEFAULT_LANGUAGE}
        </span>
      </div>

      {startError && (
        <p className="rounded-md bg-red-50 px-4 py-2 text-sm text-red-700">
          {startError}
        </p>
      )}

      <button
        onClick={handleStart}
        disabled={!canStart || starting}
        className="rounded-lg bg-green-600 px-8 py-3 text-sm font-medium text-white shadow-md hover:bg-green-700 disabled:opacity-50"
      >
        {starting ? "Starting..." : "Start Session"}
      </button>

      <button
        onClick={signOut}
        className="mt-4 text-sm text-gray-400 hover:text-gray-600"
      >
        Sign out
      </button>
    </main>
  );
}
