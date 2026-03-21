import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { TranscriptPanel } from "./TranscriptPanel";

const ENTRIES = [
  {
    role: "user" as const,
    text_en: "I want to say hello",
    turn_index: 0,
  },
  {
    role: "assistant" as const,
    text_en: "Here is how to say hello:",
    text_native: "こんにちは",
    text_reading: "こんにちは",
    text_romanized: "konnichiwa",
    pronunciation_note: "Natural greeting",
    next_prompt: "Try saying it back to me",
    turn_index: 1,
  },
];

describe("TranscriptPanel", () => {
  it("renders user entries", () => {
    render(<TranscriptPanel entries={ENTRIES} />);
    expect(screen.getByText("I want to say hello")).toBeDefined();
  });

  it("renders assistant entries with all fields", () => {
    render(<TranscriptPanel entries={ENTRIES} />);
    expect(screen.getAllByText("こんにちは").length).toBeGreaterThan(0);
    expect(screen.getByText("konnichiwa")).toBeDefined();
    expect(screen.getByText("Natural greeting")).toBeDefined();
    expect(screen.getByText("Try saying it back to me")).toBeDefined();
  });

  it("renders empty state", () => {
    render(<TranscriptPanel entries={[]} />);
    expect(screen.getByText(/start speaking/i)).toBeDefined();
  });
});
