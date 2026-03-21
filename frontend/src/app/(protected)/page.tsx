"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { apiClient } from "@/lib/api";
import { useAuth } from "@/hooks/useAuth";

const TOPICS = ["Greetings", "Ordering Food", "Directions", "Shopping", "Travel"];

export default function HomePage() {
  const [mode, setMode] = useState<"learn" | "quiz">("learn");
  const [topic, setTopic] = useState(TOPICS[0]);
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { signOut } = useAuth();

  const handleStart = async () => {
    setLoading(true);
    try {
      const response = await apiClient.post("/conversation/start", {
        language: "ja",
        mode,
        topic,
      });
      const data = await response.json();
      router.push(`/conversation/${data.session_id}`);
    } catch (error) {
      console.error("Failed to start conversation:", error);
    } finally {
      setLoading(false);
    }
  };

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
        <select
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          className="rounded-lg border border-gray-300 bg-white px-4 py-2 text-sm"
        >
          {TOPICS.map((t) => (
            <option key={t} value={t}>
              {t}
            </option>
          ))}
        </select>
      </div>

      <div className="flex flex-col gap-2">
        <label className="text-sm font-medium text-gray-600">Language</label>
        <span className="rounded-lg border border-gray-200 bg-gray-50 px-4 py-2 text-sm text-gray-500">
          Japanese (日本語)
        </span>
      </div>

      <button
        onClick={handleStart}
        disabled={loading}
        className="rounded-lg bg-green-600 px-8 py-3 text-sm font-medium text-white shadow-md hover:bg-green-700 disabled:opacity-50"
      >
        {loading ? "Starting..." : "Start Session"}
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
