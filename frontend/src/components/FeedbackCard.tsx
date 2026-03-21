interface FeedbackData {
  correct: string[];
  revisit: string[];
  drills: string[];
}

interface FeedbackCardProps {
  feedback: FeedbackData;
}

export type { FeedbackData };

export function FeedbackCard({ feedback }: FeedbackCardProps) {
  return (
    <div className="flex flex-col gap-6 rounded-xl bg-white p-6 shadow-lg">
      <div>
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-green-600">
          What You Got Right
        </h3>
        <ul className="flex flex-col gap-1">
          {feedback.correct.map((item, i) => (
            <li key={i} className="flex items-center gap-2 text-sm text-gray-700">
              <span className="text-green-500">&#10003;</span>
              {item}
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-amber-600">
          To Revisit
        </h3>
        <ul className="flex flex-col gap-1">
          {feedback.revisit.map((item, i) => (
            <li key={i} className="flex items-center gap-2 text-sm text-gray-700">
              <span className="text-amber-500">&#9679;</span>
              {item}
            </li>
          ))}
        </ul>
      </div>

      <div>
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-blue-600">
          Suggested Drills
        </h3>
        <ul className="flex flex-col gap-1">
          {feedback.drills.map((item, i) => (
            <li key={i} className="flex items-center gap-2 text-sm text-gray-700">
              <span className="text-blue-500">&#8250;</span>
              {item}
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}
