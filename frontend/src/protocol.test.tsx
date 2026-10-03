import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SourceBadge, Probability } from "./App";
import { Message, Frame } from "./protocol";
describe("source and prediction presentation", () => {
  it("visibly distinguishes synthetic from recorded", () => {
    render(
      <>
        <SourceBadge label="SYNTHETIC" />
        <SourceBadge label="RECORDED EEG REPLAY" />
      </>,
    );
    expect(screen.getByText("SYNTHETIC")).toBeVisible();
    expect(screen.getByText("RECORDED EEG REPLAY")).toBeVisible();
  });
  it("renders explicit class and probability", () => {
    render(<Probability label="Left hand" value={0.75} />);
    expect(screen.getByText("75.0%")).toBeVisible();
    expect(screen.getByText("Left hand")).toBeVisible();
  });
  it("rejects incompatible transport versions", () => {
    expect(() =>
      Message.parse({
        schema_version: 2,
        type: "frame",
        session_id: "s",
        payload: {},
      }),
    ).toThrow();
  });
  it("rejects corrupted frames", () => {
    expect(() =>
      Frame.parse({ source: { source_type: "LIVE", sampling_frequency: -1 } }),
    ).toThrow();
  });
  it("accepts actionable warning envelopes", () => {
    expect(
      Message.parse({
        schema_version: 1,
        type: "warning",
        session_id: "s",
        payload: { message: "Model mismatch" },
      }).type,
    ).toBe("warning");
  });
});
