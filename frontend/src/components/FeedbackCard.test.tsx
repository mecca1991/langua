import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { FeedbackCard } from "./FeedbackCard";

const FEEDBACK = {
  correct: ["konnichiwa", "arigatou"],
  revisit: ["sumimasen"],
  drills: ["Practice basic greetings", "Role-play ordering food"],
};

describe("FeedbackCard", () => {
  it("renders correct phrases", () => {
    render(<FeedbackCard feedback={FEEDBACK} />);
    expect(screen.getByText("konnichiwa")).toBeDefined();
    expect(screen.getByText("arigatou")).toBeDefined();
  });

  it("renders phrases to revisit", () => {
    render(<FeedbackCard feedback={FEEDBACK} />);
    expect(screen.getByText("sumimasen")).toBeDefined();
  });

  it("renders suggested drills", () => {
    render(<FeedbackCard feedback={FEEDBACK} />);
    expect(screen.getByText("Practice basic greetings")).toBeDefined();
    expect(screen.getByText("Role-play ordering food")).toBeDefined();
  });

  it("renders section headings", () => {
    render(<FeedbackCard feedback={FEEDBACK} />);
    expect(screen.getByText(/what you got right/i)).toBeDefined();
    expect(screen.getByText(/to revisit/i)).toBeDefined();
    expect(screen.getByText(/suggested drills/i)).toBeDefined();
  });
});
