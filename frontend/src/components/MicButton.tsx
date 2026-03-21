interface MicButtonProps {
  isRecording: boolean;
  isProcessing: boolean;
  onToggle: () => void;
}

export function MicButton({ isRecording, isProcessing, onToggle }: MicButtonProps) {
  return (
    <button
      onClick={onToggle}
      disabled={isProcessing}
      className={`flex h-16 w-16 items-center justify-center rounded-full text-white shadow-lg transition-all ${
        isRecording
          ? "bg-red-500 hover:bg-red-600 scale-110"
          : isProcessing
            ? "bg-gray-400 cursor-not-allowed"
            : "bg-blue-600 hover:bg-blue-700"
      }`}
      aria-label={isRecording ? "Stop recording" : "Start recording"}
    >
      {isProcessing ? (
        <svg
          className="h-6 w-6 animate-spin"
          fill="none"
          viewBox="0 0 24 24"
        >
          <circle
            className="opacity-25"
            cx="12"
            cy="12"
            r="10"
            stroke="currentColor"
            strokeWidth="4"
          />
          <path
            className="opacity-75"
            fill="currentColor"
            d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
          />
        </svg>
      ) : (
        <svg className="h-6 w-6" fill="currentColor" viewBox="0 0 24 24">
          {isRecording ? (
            <rect x="6" y="6" width="12" height="12" rx="2" />
          ) : (
            <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3zm-1 1.93c-3.94-.49-7-3.85-7-7.93h2c0 3.31 2.69 6 6 6s6-2.69 6-6h2c0 4.08-3.06 7.44-7 7.93V20h4v2H8v-2h4v-4.07z" />
          )}
        </svg>
      )}
    </button>
  );
}
