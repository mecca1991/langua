import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Waveform } from "./Waveform";

describe("Waveform", () => {
  it("renders bars when active", () => {
    const { container } = render(<Waveform active={true} />);
    const bars = container.querySelectorAll("[data-testid='waveform-bar']");
    expect(bars.length).toBeGreaterThan(0);
  });

  it("renders nothing when inactive", () => {
    const { container } = render(<Waveform active={false} />);
    const bars = container.querySelectorAll("[data-testid='waveform-bar']");
    expect(bars.length).toBe(0);
  });
});
