"use client";

import { useEffect, useState, useRef, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { useRecorder } from "@/hooks/useRecorder";
import { apiClient } from "@/lib/api";
import { Waveform } from "@/components/Waveform";
import { TranscriptPanel, TranscriptEntry } from "@/components/TranscriptPanel";
import { MicButton } from "@/components/MicButton";

export default function ConversationPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;

  const { isRecording, startRecording, stopRecording, audioBlob, error } =
    useRecorder();
  const [entries, setEntries] = useState<TranscriptEntry[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);
  const [processingError, setProcessingError] = useState<string | null>(null);
  const scrollRef = useRef<HTMLDivElement>(null);

  const handleToggle = useCallback(() => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  }, [isRecording, startRecording, stopRecording]);

  useEffect(() => {
    if (!audioBlob) return;

    const sendTurn = async () => {
      setIsProcessing(true);
      setProcessingError(null);

      const formData = new FormData();
      formData.append("session_id", sessionId);
      formData.append("audio", audioBlob, "audio.webm");

      const idempotencyKey = crypto.randomUUID();

      try {
        const response = await apiClient.postFormData(
          "/conversation/turn",
          formData,
          { "X-Idempotency-Key": idempotencyKey },
        );

        if (!response.ok) {
          const err = await response.json();
          throw new Error(err.detail || "Turn failed");
        }

        const data = await response.json();

        setEntries((prev) => [
          ...prev,
          { ...data.user_entry, role: "user" as const },
          { ...data.assistant_entry, role: "assistant" as const },
        ]);

        // Play audio
        const audioUrl = `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}${data.audio_url}`;
        const audio = new Audio(audioUrl);
        audio.play().catch(() => {});
      } catch (err) {
        setProcessingError(
          err instanceof Error ? err.message : "Something went wrong",
        );
      } finally {
        setIsProcessing(false);
      }
    };

    sendTurn();
  }, [audioBlob, sessionId]);

  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: "smooth",
    });
  }, [entries]);

  const handleEnd = async () => {
    try {
      const response = await apiClient.post("/conversation/end", {
        session_id: sessionId,
      });
      const data = await response.json();

      if (data.feedback_status === "pending") {
        router.push(`/results/${sessionId}`);
      } else {
        router.push("/");
      }
    } catch {
      router.push("/");
    }
  };

  return (
    <div className="flex h-screen flex-col">
      <header className="flex items-center justify-between border-b px-6 py-4">
        <h1 className="text-lg font-semibold">Conversation</h1>
        <button
          onClick={handleEnd}
          className="rounded-lg bg-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-300"
        >
          End Session
        </button>
      </header>

      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        <TranscriptPanel entries={entries} />
      </div>

      {error && (
        <p className="px-4 text-center text-sm text-red-500">{error}</p>
      )}
      {processingError && (
        <p className="px-4 text-center text-sm text-red-500">
          {processingError}
        </p>
      )}

      <div className="flex flex-col items-center gap-2 border-t px-6 py-4">
        <Waveform active={isRecording} />
        <MicButton
          isRecording={isRecording}
          isProcessing={isProcessing}
          onToggle={handleToggle}
        />
        <p className="text-xs text-gray-400">
          {isRecording
            ? "Recording... tap to stop"
            : isProcessing
              ? "Processing..."
              : "Tap to speak"}
        </p>
      </div>
    </div>
  );
}
