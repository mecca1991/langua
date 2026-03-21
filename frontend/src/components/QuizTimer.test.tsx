import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { QuizTimer } from "./QuizTimer";

describe("QuizTimer", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders initial time as 2:00", () => {
    render(<QuizTimer durationSeconds={120} onExpire={vi.fn()} />);
    expect(screen.getByText("2:00")).toBeDefined();
  });

  it("counts down every second", () => {
    render(<QuizTimer durationSeconds={120} onExpire={vi.fn()} />);
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(screen.getByText("1:59")).toBeDefined();
  });

  it("calls onExpire when timer reaches zero", () => {
    const onExpire = vi.fn();
    render(<QuizTimer durationSeconds={3} onExpire={onExpire} />);

    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(onExpire).toHaveBeenCalledTimes(1);
  });

  it("shows red text when under 30 seconds", () => {
    const { container } = render(
      <QuizTimer durationSeconds={30} onExpire={vi.fn()} />,
    );
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    const timer = container.querySelector("[data-testid='quiz-timer']");
    expect(timer?.className).toContain("text-red");
  });
});
