"use client";

import { useState, useEffect, useRef } from "react";

interface QuizTimerProps {
  durationSeconds: number;
  onExpire: () => void;
}

export function QuizTimer({ durationSeconds, onExpire }: QuizTimerProps) {
  const [remaining, setRemaining] = useState(durationSeconds);
  const onExpireRef = useRef(onExpire);
  onExpireRef.current = onExpire;

  useEffect(() => {
    const interval = setInterval(() => {
      setRemaining((prev) => {
        const next = prev - 1;
        if (next <= 0) {
          clearInterval(interval);
          onExpireRef.current();
          return 0;
        }
        return next;
      });
    }, 1000);

    return () => clearInterval(interval);
  }, [durationSeconds]);

  const minutes = Math.floor(remaining / 60);
  const seconds = remaining % 60;
  const display = `${minutes}:${seconds.toString().padStart(2, "0")}`;

  return (
    <div
      data-testid="quiz-timer"
      className={`text-lg font-mono font-bold ${
        remaining <= 30 ? "text-red-500" : "text-gray-700"
      }`}
    >
      {display}
    </div>
  );
}
