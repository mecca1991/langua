"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useRecorder } from "@/hooks/useRecorder";
import { useApiQuery } from "@/hooks/useApiQuery";
import { apiClient } from "@/lib/api";
import { Waveform } from "@/components/Waveform";
import { TranscriptPanel, TranscriptEntry } from "@/components/TranscriptPanel";
import { MicButton } from "@/components/MicButton";
import { config } from "@/lib/config";
import type {
  SessionDetail,
  TurnResponse,
  EndConversationResponse,
} from "@/lib/api-types";

export default function ConversationPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;

  // --- Session loading via shared hook ---
  const {
    data: session,
    loading: pageLoading,
    error: pageError,
  } = useApiQuery(
    () => apiClient.get<SessionDetail>(`/sessions/${sessionId}`),
    [sessionId],
  );

  // --- Transcript ---
  const [entries, setEntries] = useState<TranscriptEntry[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  // Hydrate entries when session data loads or sessionId changes
  useEffect(() => {
    if (session) {
      setEntries(session.transcript);
    }
  }, [session]);

  // --- Recording & submission ---
  const { isRecording, startRecording, stopRecording, audioBlob, error: recorderError } =
    useRecorder();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [audioWarning, setAudioWarning] = useState<string | null>(null);
  const submittingRef = useRef(false);

  // --- End session ---
  const endingRef = useRef(false);

  // --- Submit turn when audioBlob is ready ---
  useEffect(() => {
    if (!audioBlob || submittingRef.current) return;
    submittingRef.current = true;

    const sendTurn = async () => {
      setIsSubmitting(true);
      setSubmitError(null);
      setAudioWarning(null);

      const formData = new FormData();
      formData.append("session_id", sessionId);
      formData.append("audio", audioBlob, "recording");

      const idempotencyKey = crypto.randomUUID();

      try {
        const data = await apiClient.postFormData<TurnResponse>(
          "/conversation/turn",
          formData,
          { "X-Idempotency-Key": idempotencyKey },
        );

        setEntries((prev) => [
          ...prev,
          { ...data.user_entry, role: "user" as const },
          { ...data.assistant_entry, role: "assistant" as const },
        ]);

        const audioUrl = `${config.apiUrl}${data.audio_url}`;
        const audio = new Audio(audioUrl);
        try {
          await audio.play();
        } catch {
          setAudioWarning(
            "Could not play audio response. Check your device volume or browser autoplay settings.",
          );
        }
      } catch (err) {
        setSubmitError(
          err instanceof Error ? err.message : "Something went wrong",
        );
      } finally {
        setIsSubmitting(false);
        submittingRef.current = false;
      }
    };

    sendTurn();
  }, [audioBlob, sessionId]);

  // --- Auto-scroll on new entries ---
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [entries]);

  // --- End session ---
  const handleEnd = useCallback(async () => {
    if (endingRef.current) return;
    endingRef.current = true;
    try {
      const data = await apiClient.post<EndConversationResponse>(
        "/conversation/end",
        { session_id: sessionId },
      );

      if (data.feedback_status === "pending") {
        router.push(`/results/${sessionId}`);
      } else {
        router.push("/");
      }
    } catch {
      router.push("/");
    }
  }, [sessionId, router]);

  // --- Toggle recording ---
  const handleToggle = useCallback(() => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }, [isRecording, startRecording, stopRecording]);

  // --- Derived state ---
  const isActive = session?.status === "active";
  const isQuiz = session?.mode === "quiz";

  // --- Loading state ---
  if (pageLoading) {
    return (
      <div className="flex h-screen items-center justify-center">
        <p className="text-gray-500">Loading session...</p>
      </div>
    );
  }

  // --- Error state ---
  if (pageError || !session) {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 p-8">
        <p className="text-red-600">{pageError ?? "Session not found."}</p>
        <button
          onClick={() => router.push("/")}
          className="text-sm text-blue-600 hover:text-blue-700"
        >
          Back to Home
        </button>
      </div>
    );
  }

  // --- Ended session (read-only transcript) ---
  if (!isActive) {
    return (
      <div className="flex h-screen flex-col">
        <header className="flex items-center justify-between border-b px-6 py-4">
          <h1 className="text-lg font-semibold">
            {session.topic} &middot;{" "}
            {isQuiz ? "Quiz" : "Learn"} &middot; Ended
          </h1>
          <button
            onClick={() => router.push("/")}
            className="rounded-lg bg-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-300"
          >
            Back to Home
          </button>
        </header>
        <div className="flex-1 overflow-y-auto">
          <TranscriptPanel entries={entries} />
        </div>
      </div>
    );
  }

  // --- Active session ---
  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b px-6 py-4">
        <h1 className="text-lg font-semibold">
          {session.topic} &middot; {isQuiz ? "Quiz" : "Learn"}
        </h1>
        <button
          onClick={handleEnd}
          disabled={endingRef.current}
          className="rounded-lg bg-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-300 disabled:opacity-50"
        >
          End Session
        </button>
      </header>

      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <TranscriptPanel entries={entries} />
      </div>

      {recorderError && (
        <p className="px-4 py-2 text-center text-sm text-red-500">
          {recorderError}
        </p>
      )}
      {submitError && (
        <p className="px-4 py-2 text-center text-sm text-red-500">
          {submitError}
        </p>
      )}
      {audioWarning && (
        <p className="px-4 py-2 text-center text-sm text-amber-600">
          {audioWarning}
        </p>
      )}

      <div className="flex flex-col items-center gap-2 border-t px-6 py-4">
        <Waveform active={isRecording} />
        <MicButton
          isRecording={isRecording}
          isProcessing={isSubmitting}
          onToggle={handleToggle}
        />
        <p className="text-xs text-gray-400">
          {isRecording
            ? "Recording... tap to stop"
            : isSubmitting
              ? "Processing..."
              : "Tap to speak"}
        </p>
      </div>
    </div>
  );
}
