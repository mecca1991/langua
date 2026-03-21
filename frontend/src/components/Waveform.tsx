interface WaveformProps {
  active: boolean;
}

const BAR_DELAYS = [0, 0.15, 0.3, 0.1, 0.25, 0.05, 0.2, 0.35, 0.12, 0.28];

export function Waveform({ active }: WaveformProps) {
  if (!active) return null;

  return (
    <div className="flex items-center justify-center gap-1 py-4">
      {BAR_DELAYS.map((delay, i) => (
        <div
          key={i}
          data-testid="waveform-bar"
          className="w-1 animate-waveform rounded-full bg-blue-500"
          style={{
            animationDelay: `${delay}s`,
            height: "24px",
          }}
        />
      ))}
      <style>{`
        @keyframes waveform {
          0%, 100% { transform: scaleY(0.3); }
          50% { transform: scaleY(1); }
        }
        .animate-waveform {
          animation: waveform 0.8s ease-in-out infinite;
        }
      `}</style>
    </div>
  );
}
