interface TranscriptEntry {
  role: "user" | "assistant";
  text_en: string;
  text_native?: string;
  text_reading?: string;
  text_romanized?: string;
  pronunciation_note?: string;
  next_prompt?: string;
  turn_index: number;
}

interface TranscriptPanelProps {
  entries: TranscriptEntry[];
}

export type { TranscriptEntry };

export function TranscriptPanel({ entries }: TranscriptPanelProps) {
  if (entries.length === 0) {
    return (
      <div className="flex flex-1 items-center justify-center text-gray-400">
        <p>Start speaking to begin your lesson</p>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4 overflow-y-auto p-4">
      {entries.map((entry) => (
        <div
          key={entry.turn_index}
          className={`rounded-lg p-4 ${
            entry.role === "user"
              ? "ml-8 bg-blue-50 text-right"
              : "mr-8 bg-gray-50"
          }`}
        >
          {entry.role === "user" ? (
            <p className="text-sm text-gray-700">{entry.text_en}</p>
          ) : (
            <div className="flex flex-col gap-2">
              <p className="text-sm text-gray-600">{entry.text_en}</p>
              {entry.text_native && (
                <p className="text-2xl font-bold text-gray-900">
                  {entry.text_native}
                </p>
              )}
              {entry.text_reading && (
                <p className="text-sm text-gray-500">{entry.text_reading}</p>
              )}
              {entry.text_romanized && (
                <p className="text-sm font-medium text-blue-600">
                  {entry.text_romanized}
                </p>
              )}
              {entry.pronunciation_note && (
                <p className="text-xs italic text-amber-600">
                  {entry.pronunciation_note}
                </p>
              )}
              {entry.next_prompt && (
                <p className="mt-1 text-sm font-medium text-green-700">
                  {entry.next_prompt}
                </p>
              )}
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
