import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import App from "./App";
vi.mock("./SignalCanvas", () => ({
  SignalCanvas: () => <div>Signal fixture renderer</div>,
}));
vi.mock("./ControlScene", () => ({
  ControlScene: () => <div>Control fixture renderer</div>,
}));
class FakeSocket {
  static latest: FakeSocket;
  onopen: (() => void) | null = null;
  onclose: (() => void) | null = null;
  onerror: (() => void) | null = null;
  onmessage: ((event: { data: string }) => void) | null = null;
  constructor() {
    FakeSocket.latest = this;
  }
  close() {}
  emit(type: string, payload: unknown) {
    this.onmessage?.({
      data: JSON.stringify({
        schema_version: 1,
        type,
        session_id: "fixture",
        payload,
      }),
    });
  }
}
const source = {
  name: "Recorded fixture",
  source_type: "RECORDED EEG REPLAY",
  sampling_frequency: 160,
  channel_names: ["C3", "Cz", "C4"],
  subject: "fixture",
  dataset: "fixture",
  session: "test",
};
const session = {
  version: "0.1.0",
  source,
  state: "streaming",
  session_id: "fixture",
  recording: null,
  replay_available: true,
  model: {
    decoder: "csp_lda",
    channels: ["C3", "Cz", "C4"],
    classes: ["left_hand", "right_hand"],
    preprocessing_id: "trial_zero_phase_v1",
    training_seconds: 1,
  },
};
const frame = {
  source,
  signal: [[1], [1], [1]],
  timestamps: [1],
  spectrum: { frequencies: [1], psd: [1], bands: { alpha: 1 } },
  prediction: {
    raw: [0.8, 0.2],
    smoothed: [0.75, 0.25],
    decision: 0,
    confidence: 0.75,
    inference_ms: 0.1,
    pipeline_ms: 0.2,
    truth: 1,
    trial: 1,
  },
  simulated_control: null,
  control_mode: "held-out EEG decoder",
  stats: {
    received_samples: 1,
    missing_samples: 0,
    late_chunks: 0,
    buffer_samples: 1,
    pipeline_ms: 0.2,
    pipeline_p95_ms: 0.3,
    prediction_count: 1,
    live_accuracy: 0,
    ws_dropped: 0,
    uptime_s: 1,
  },
  timeline: [],
  state: "streaming",
};
const fetchMock = vi.fn();
beforeEach(() => {
  vi.stubGlobal("WebSocket", FakeSocket);
  vi.stubGlobal("fetch", fetchMock);
  fetchMock.mockImplementation(async (url: string) => ({
    ok: true,
    json: async () =>
      url.includes("/decoders") ? { csp_lda: "CSP + LDA" } : session,
  }));
});
afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.clearAllMocks();
});
describe("console integration states", () => {
  it("renders connection, decoder metadata and real message probabilities", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText("CSP + LDA")).toBeVisible());
    act(() => {
      FakeSocket.latest.onopen?.();
      FakeSocket.latest.emit("frame", frame);
    });
    expect(screen.getByText("Backend connected")).toBeVisible();
    expect(screen.getByText("RECORDED EEG REPLAY")).toBeVisible();
    expect(screen.getByText("75.0%")).toBeVisible();
    expect(screen.getByText("Left hand")).toBeVisible();
    expect(screen.getByText(/trial_zero_phase_v1/)).toBeVisible();
  });
  it("renders actionable backend and model warnings", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText("CSP + LDA")).toBeVisible());
    act(() =>
      FakeSocket.latest.emit("warning", {
        message: "Channel mismatch: load a matching model",
      }),
    );
    expect(screen.getByRole("alert")).toHaveTextContent("Channel mismatch");
  });
  it("sends perturbation controls with their actual values", async () => {
    render(<App />);
    await waitFor(() => expect(screen.getByText("CSP + LDA")).toBeVisible());
    fireEvent.change(screen.getByRole("slider", { name: /Gaussian noise/ }), {
      target: { value: "1.2" },
    });
    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/perturbations",
        expect.objectContaining({ body: expect.stringContaining("1.2") }),
      ),
    );
  });
  it("updates pause state without waiting for a new signal frame", async () => {
    fetchMock.mockImplementation(async (url: string) => ({
      ok: true,
      json: async () =>
        url.includes("/decoders")
          ? { csp_lda: "CSP + LDA" }
          : url.includes("/control")
            ? { ...session, state: "paused" }
            : session,
    }));
    render(<App />);
    await waitFor(() => expect(screen.getByText("CSP + LDA")).toBeVisible());
    act(() => {
      FakeSocket.latest.onopen?.();
      FakeSocket.latest.emit("frame", frame);
    });
    fireEvent.click(screen.getByRole("button", { name: "Pause stream" }));
    await waitFor(() =>
      expect(
        screen.getByRole("button", { name: "Resume stream" }),
      ).toBeVisible(),
    );
  });
});
