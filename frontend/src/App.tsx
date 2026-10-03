import { useCallback, useEffect, useState } from "react";
import {
  Activity,
  ArrowLeft,
  ArrowRight,
  AudioLines,
  Beaker,
  Box,
  Check,
  ChevronDown,
  Circle,
  Download,
  FlaskConical,
  Layers,
  Pause,
  Play,
  Radio,
  RotateCcw,
  SlidersHorizontal,
  Wifi,
  Zap,
} from "lucide-react";
import { api, Frame, Message, type FrameData, type Session } from "./protocol";
import { SignalCanvas } from "./SignalCanvas";
import { ControlScene } from "./ControlScene";

const format = (n: number | undefined | null, digits = 1) =>
  n == null ? "—" : n.toFixed(digits);
const bands = ["delta", "theta", "alpha", "beta", "gamma"];
export function SourceBadge({ label }: { label: string }) {
  return (
    <span
      className={`source-badge ${label === "SYNTHETIC" ? "synthetic" : "replay"}`}
    >
      <Radio size={12} />
      {label}
    </span>
  );
}
export function Probability({
  label,
  value,
}: {
  label: string;
  value: number;
}) {
  return (
    <div className="prob-row">
      <div>
        <span>{label}</span>
        <b>{(value * 100).toFixed(1)}%</b>
      </div>
      <div className="prob-track">
        <div style={{ width: `${value * 100}%` }} />
      </div>
    </div>
  );
}
export default function App() {
  const [frame, setFrame] = useState<FrameData | null>(null),
    [session, setSession] = useState<Session | null>(null),
    [connection, setConnection] = useState("connecting"),
    [error, setError] = useState<string | null>(null),
    [visualPaused, setVisualPaused] = useState(false),
    [scale, setScale] = useState(100),
    [seconds, setSeconds] = useState(5),
    [noise, setNoise] = useState(0),
    [amplitude, setAmplitude] = useState(1),
    [drift, setDrift] = useState(0),
    [line, setLine] = useState(0),
    [dropout, setDropout] = useState(false),
    [loss, setLoss] = useState(0),
    [jitter, setJitter] = useState(0),
    [selected, setSelected] = useState([0, 1, 2, 3]),
    [tab, setTab] = useState("Workspace"),
    [speed, setSpeed] = useState(1),
    [decoderNames, setDecoderNames] = useState<Record<string, string>>({}),
    [busy, setBusy] = useState(false);
  const refresh = useCallback(async () => {
    try {
      setSession(await api("session"));
      setDecoderNames(await api("decoders"));
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);
  useEffect(() => {
    void refresh();
    let socket: WebSocket | null = null,
      timer: ReturnType<typeof setTimeout>;
    let disposed = false;
    const connect = () => {
      if (disposed) return;
      setConnection("connecting");
      socket = new WebSocket(
        `${location.protocol === "https:" ? "wss" : "ws"}://${location.host}/ws`,
      );
      socket.onopen = () => {
        setConnection("connected");
        setError(null);
        void refresh();
      };
      socket.onmessage = (e) => {
        try {
          const m = Message.parse(JSON.parse(e.data));
          if (m.type === "frame") setFrame(Frame.parse(m.payload));
          else if (m.type === "warning")
            setError((m.payload as { message: string }).message);
          else {
            const next = m.payload as Session;
            setSession(next);
            setFrame((prev) => (prev ? { ...prev, state: next.state } : prev));
          }
        } catch {
          setError(
            "Unsupported stream message. Restart the backend and refresh the console.",
          );
        }
      };
      socket.onclose = () => {
        if (!disposed) {
          setConnection("reconnecting");
          timer = setTimeout(connect, 1500);
        }
      };
      socket.onerror = () => {
        setError(
          "Backend unavailable. Start ./scripts/demo.sh and keep its terminal open.",
        );
        socket?.close();
      };
    };
    connect();
    return () => {
      disposed = true;
      clearTimeout(timer);
      socket?.close();
    };
  }, [refresh]);
  const control = async (action: string, value?: number) => {
    setBusy(true);
    try {
      const next: Session = await api("control", { action, value });
      setSession(next);
      setFrame((prev) => (prev ? { ...prev, state: next.state } : prev));
      setError(null);
      if (action === "synthetic" || action === "replay") {
        setFrame(null);
        setSelected(action === "replay" ? [0, 1, 2] : [0, 1, 2, 3]);
      }
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    const timer = setTimeout(() => {
      const configurations = [];
      if (noise)
        configurations.push({
          name: "gaussian_noise",
          intensity: noise,
          seed: 42,
        });
      if (amplitude !== 1)
        configurations.push({ name: "amplitude", intensity: amplitude });
      if (drift)
        configurations.push({
          name: "baseline_drift",
          intensity: drift,
          frequency: 0.2,
        });
      if (line)
        configurations.push({
          name: "line_noise",
          intensity: line,
          frequency: 50,
        });
      if (dropout)
        configurations.push({
          name: "channel_dropout",
          channels: [0],
          intensity: 1,
        });
      if (loss)
        configurations.push({ name: "sample_loss", intensity: loss, seed: 42 });
      if (jitter)
        configurations.push({
          name: "timing_jitter",
          intensity: jitter,
          seed: 42,
        });
      void api("perturbations", { configurations }).catch((e) =>
        setError(e.message),
      );
    }, 200);
    return () => clearTimeout(timer);
  }, [noise, amplitude, drift, line, dropout, loss, jitter]);
  const source = frame?.source ?? session?.source,
    prediction = frame?.prediction,
    synthetic = source?.source_type === "SYNTHETIC",
    p = prediction?.smoothed ?? [0.5, 0.5],
    decision = prediction?.decision;
  const controlValue = synthetic
    ? (frame?.simulated_control ?? 0)
    : decision === 0
      ? -1
      : decision === 1
        ? 1
        : 0;
  const running = (frame?.state ?? session?.state) === "streaming";
  const state =
    connection === "connected"
      ? (frame?.state ?? session?.state ?? "waiting")
      : connection;
  const reset = () => {
    setNoise(0);
    setAmplitude(1);
    setDrift(0);
    setLine(0);
    setDropout(false);
    setLoss(0);
    setJitter(0);
  };
  return (
    <div className="app-shell">
      <aside>
        <div className="brand-mark">
          <AudioLines size={24} />
        </div>
        <button
          className={tab === "Workspace" ? "active" : ""}
          title="Workspace"
          aria-label="Workspace"
          onClick={() => setTab("Workspace")}
        >
          <Layers />
        </button>
        <button
          className={tab === "Perturbation lab" ? "active" : ""}
          title="Perturbation laboratory"
          aria-label="Perturbation laboratory"
          onClick={() => {
            setTab("Perturbation lab");
            document
              .getElementById("lab")
              ?.scrollIntoView({ behavior: "smooth" });
          }}
        >
          <FlaskConical />
        </button>
        <button
          className={tab === "Session log" ? "active" : ""}
          title="Session log"
          aria-label="Session log"
          onClick={() => {
            setTab("Session log");
            document
              .getElementById("timeline")
              ?.scrollIntoView({ behavior: "smooth" });
          }}
        >
          <Activity />
        </button>
        <div className="aside-bottom">
          <span className="local-dot" />
          LOCAL
        </div>
      </aside>
      <div className="workspace">
        <header>
          <div className="wordmark">
            NeuroStream<span>Lab</span>
            <small>RESEARCH CONSOLE</small>
          </div>
          <div className="header-right">
            <span className="connection">
              <span
                className={`dot ${connection === "connected" ? "online" : ""}`}
              />
              {connection === "connected" ? "Backend connected" : connection}
            </span>
            <span className="local-chip">LOCAL ENVIRONMENT</span>
          </div>
        </header>
        <main>
          <div className="page-heading">
            <div>
              <div className="eyebrow">
                SIGNAL WORKSPACE / {tab.toUpperCase()}
              </div>
              <h1>
                From signal to decision<span>.</span>
              </h1>
              <p>
                Explore neural streams. Test the pipeline. Measure what changes.
              </p>
            </div>
            <div className="session-actions">
              <button
                className="button ghost"
                onClick={() =>
                  void control(session?.recording ? "stop_recording" : "record")
                }
                disabled={busy || connection !== "connected"}
              >
                <Circle
                  size={14}
                  className={session?.recording ? "record-dot" : ""}
                />
                {session?.recording ? "Stop recording" : "Record session"}
              </button>
              <button
                className="button primary"
                onClick={() => void control(running ? "pause" : "resume")}
                disabled={busy || connection !== "connected"}
              >
                {running ? <Pause size={14} /> : <Play size={14} />}{" "}
                {running ? "Pause stream" : "Resume stream"}
              </button>
            </div>
          </div>
          {error && (
            <div className="error" role="alert">
              <Zap size={16} />
              {error}
              <button aria-label="Dismiss error" onClick={() => setError(null)}>
                ×
              </button>
            </div>
          )}
          <section className="source-strip">
            <div>
              <div className="source-icon">
                <Radio size={22} />
              </div>
              <div>
                <span className="eyebrow">SIGNAL SOURCE</span>
                <div className="source-title">
                  <select
                    aria-label="Signal source"
                    value={synthetic ? "synthetic" : "replay"}
                    onChange={(e) => void control(e.target.value)}
                    disabled={busy}
                  >
                    <option value="synthetic">BrainFlow synthetic board</option>
                    <option value="replay">PhysioNet held-out replay</option>
                  </select>
                  <ChevronDown size={14} />
                </div>
              </div>
            </div>
            <SourceBadge label={source?.source_type ?? "SYNTHETIC"} />
            <div className="source-meta">
              <span>
                Sample rate<b>{source?.sampling_frequency ?? "—"} Hz</b>
              </span>
              <span>
                Channels<b>{source?.channel_names.length ?? "—"} EEG</b>
              </span>
              <span>
                Subject / session
                <b>
                  {source?.subject
                    ? `${source.subject} / ${source.session}`
                    : "System test"}
                </b>
              </span>
              <span>
                Status
                <b>
                  <span className={`dot ${running ? "online" : ""}`} />
                  {state}
                </b>
              </span>
            </div>
          </section>
          <div className="main-grid">
            <div className="left-column">
              <section className="panel signal-panel">
                <div className="panel-title">
                  <div>
                    <AudioLines size={16} />
                    <h2>Neural signal</h2>
                    <span className="pill">µV</span>
                  </div>
                  <div className="chart-controls">
                    <select
                      aria-label="Amplitude scale"
                      value={scale}
                      onChange={(e) => setScale(Number(e.target.value))}
                    >
                      {[25, 50, 100, 200].map((v) => (
                        <option key={v} value={v}>
                          ±{v} µV
                        </option>
                      ))}
                    </select>
                    <select
                      aria-label="Time scale"
                      value={seconds}
                      onChange={(e) => setSeconds(Number(e.target.value))}
                    >
                      {[2, 5, 10].map((v) => (
                        <option key={v} value={v}>
                          {v} seconds
                        </option>
                      ))}
                    </select>
                    <button
                      className="icon-button"
                      aria-label={
                        visualPaused
                          ? "Resume visualization"
                          : "Pause visualization"
                      }
                      onClick={() => setVisualPaused(!visualPaused)}
                    >
                      {visualPaused ? <Play size={14} /> : <Pause size={14} />}
                    </button>
                  </div>
                </div>
                <div className="chart-caption">
                  Raw source voltage · stacked channels ·{" "}
                  {visualPaused ? "display paused" : "live Canvas rendering"}
                </div>
                <SignalCanvas
                  frame={frame}
                  paused={visualPaused}
                  scale={scale}
                  seconds={seconds}
                  selected={selected}
                />
                <div className="channel-select">
                  {source?.channel_names.slice(0, 8).map((channel, i) => (
                    <button
                      key={channel}
                      className={selected.includes(i) ? "selected" : ""}
                      onClick={() =>
                        setSelected(
                          selected.includes(i)
                            ? selected.filter((c) => c !== i)
                            : [...selected, i].sort(),
                        )
                      }
                    >
                      {selected.includes(i) && <Check size={10} />} {channel}
                    </button>
                  ))}
                  <span>
                    <span className="dot online" />
                    30 FPS target
                  </span>
                </div>
              </section>
              <div className="lower-grid">
                <section className="panel spectral-panel">
                  <div className="panel-title">
                    <div>
                      <Activity size={16} />
                      <h2>Spectral power</h2>
                    </div>
                    <span className="muted">Welch PSD</span>
                  </div>
                  <div className="band-chart">
                    {bands.map((band, i) => {
                      const values = frame?.spectrum.bands ?? {};
                      const total = Object.values(values).reduce(
                        (a, b) => a + b,
                        0,
                      );
                      const proportion = total
                        ? (values[band] ?? 0) / total
                        : 0;
                      return (
                        <div key={band}>
                          <span className="band-value">
                            {(proportion * 100).toFixed(0)}%
                          </span>
                          <div className="band-bar">
                            <div
                              style={{
                                height: `${proportion * 100}%`,
                                background: [
                                  "#60758c",
                                  "#759eab",
                                  "#67d7b6",
                                  "#8fa8e8",
                                  "#bca2d9",
                                ][i],
                              }}
                            />
                          </div>
                          <b>{band}</b>
                          <small>
                            {["1–4", "4–8", "8–13", "13–30", "30–45"][i]} Hz
                          </small>
                        </div>
                      );
                    })}
                  </div>
                  <details>
                    <summary>
                      Detailed PSD · frequency (Hz) / power (µV²/Hz)
                    </summary>
                    <svg
                      viewBox="0 0 400 95"
                      role="img"
                      aria-label="Power spectral density curve"
                    >
                      <polyline
                        fill="none"
                        stroke="#68dcb9"
                        strokeWidth="1.5"
                        points={(frame?.spectrum.psd ?? [])
                          .map(
                            (v, i, a) =>
                              `${(i / Math.max(1, a.length - 1)) * 390 + 5},${85 - Math.max(0, (Math.log10(v + 1e-9) + 9) / 12) * 75}`,
                          )
                          .join(" ")}
                      />
                    </svg>
                  </details>
                  <details className="topography">
                    <summary>Scalp electrode amplitude map</summary>
                    {frame?.topography?.available ? (
                      <>
                        <svg
                          viewBox="0 0 220 170"
                          role="img"
                          aria-label="Electrode RMS map using standard label coordinates"
                        >
                          <circle
                            cx="110"
                            cy="85"
                            r="67"
                            fill="#10202b"
                            stroke="#40586c"
                          />
                          <path
                            d="M100 20 L110 9 L120 20"
                            fill="none"
                            stroke="#40586c"
                          />
                          {frame.topography.electrodes.map((e) => (
                            <g key={e.channel}>
                              <circle
                                cx={110 + e.x * 650}
                                cy={85 - e.y * 650}
                                r="8"
                                fill="#78d9b5"
                                opacity={
                                  0.25 +
                                  Math.min(
                                    1,
                                    (frame.topography?.rms_uv[e.index] ?? 0) /
                                      50,
                                  ) *
                                    0.75
                                }
                              />
                              <text
                                x={110 + e.x * 650}
                                y={102 - e.y * 650}
                                fill="#a9c4d7"
                                textAnchor="middle"
                                fontSize="8"
                              >
                                {e.channel}
                              </text>
                            </g>
                          ))}
                        </svg>
                        <p className="footnote">
                          Standard label coordinates, not individualized sensor
                          positions. Opacity shows chunk RMS. Sparse electrodes
                          are not interpolated.
                        </p>
                      </>
                    ) : (
                      <p className="footnote">
                        Scalp mapping unavailable: channel labels lack
                        sufficient standard montage matches.
                      </p>
                    )}
                  </details>
                  <p className="footnote">
                    Frequency bands describe the signal, not mental states.
                  </p>
                </section>
                <section className="panel scene-panel">
                  <div className="panel-title">
                    <div>
                      <Box size={16} />
                      <h2>Control space</h2>
                    </div>
                    <span className="pill">3D</span>
                  </div>
                  <ControlScene value={controlValue} />
                  <div className="scene-guide">
                    <span>
                      <ArrowLeft size={13} /> Left
                    </span>
                    <span>
                      {synthetic ? "SIMULATED CONTROL" : "DECODER OUTPUT"}
                    </span>
                    <span>
                      Right <ArrowRight size={13} />
                    </span>
                  </div>
                  <p className="footnote">
                    {synthetic
                      ? "Deterministic system test. Synthetic EEG is not motor imagery."
                      : "Movement follows a smoothed, held-out trial prediction."}
                  </p>
                </section>
              </div>
              <section className="panel timeline" id="timeline">
                <div className="panel-title">
                  <div>
                    <Activity size={16} />
                    <h2>Experiment timeline</h2>
                  </div>
                  <span className="muted">Session-relative time</span>
                </div>
                {(frame?.timeline ?? []).length ? (
                  frame?.timeline
                    .slice(-4)
                    .reverse()
                    .map((event, i) => (
                      <div className="event" key={i}>
                        <span>{format(event.time)} s</span>
                        <i />
                        <b>{event.text}</b>
                      </div>
                    ))
                ) : (
                  <div className="empty-timeline">
                    Stream active. Trial and perturbation markers will appear
                    here.
                  </div>
                )}
                {!synthetic && (
                  <div className="replay-controls">
                    <label>
                      Replay speed{" "}
                      <select
                        aria-label="Replay speed"
                        value={speed}
                        onChange={(e) => {
                          setSpeed(Number(e.target.value));
                          void control("speed", Number(e.target.value));
                        }}
                      >
                        {[0.5, 1, 2, 4].map((v) => (
                          <option key={v} value={v}>
                            {v}×
                          </option>
                        ))}
                      </select>
                    </label>
                    <button
                      className="button ghost"
                      onClick={() => void control("seek", 0)}
                    >
                      <RotateCcw size={12} />
                      Restart replay
                    </button>
                  </div>
                )}
              </section>
            </div>
            <div className="right-column">
              <section className="panel decoder-panel">
                <div className="panel-title">
                  <div>
                    <Zap size={16} />
                    <h2>Decoder</h2>
                  </div>
                  <span className={`pill ${prediction ? "green" : ""}`}>
                    {session?.model ? "LOADED" : "UNTRAINED"}
                  </span>
                </div>
                <h3>
                  {session?.model
                    ? (decoderNames[session.model.decoder] ??
                      session.model.decoder)
                    : "No motor imagery model"}
                </h3>
                <p className="decoder-note">
                  {session?.model
                    ? `${session.model.preprocessing_id} · ${session.model.channels.join(" / ")}`
                    : "Synthetic mode validates acquisition and transport. Switch to recorded EEG for trained decoding."}
                </p>
                <>
                  {prediction ? (
                    <>
                      <Probability label="← Left hand" value={p[0]} />
                      <Probability label="Right hand →" value={p[1]} />
                    </>
                  ) : (
                    <div className="no-prediction">
                      No probability output
                      <br />
                      <small>
                        Load recorded EEG replay to decode held-out trials.
                      </small>
                    </div>
                  )}
                </>
                <div className="decision-box">
                  <div>
                    <span className="eyebrow">SMOOTHED DECISION</span>
                    <b>
                      {prediction
                        ? decision === 0
                          ? "Left hand"
                          : decision === 1
                            ? "Right hand"
                            : "Abstain"
                        : "Awaiting recorded EEG"}
                    </b>
                  </div>
                  <span>
                    {prediction
                      ? `${(prediction.confidence * 100).toFixed(0)}%`
                      : "—"}
                  </span>
                </div>
                <div className="decoder-facts">
                  <span>
                    Raw left / right
                    <b>
                      {prediction
                        ? `${(prediction.raw[0] * 100).toFixed(0)} / ${(prediction.raw[1] * 100).toFixed(0)}%`
                        : "—"}
                    </b>
                  </span>
                  <span>
                    Inference<b>{format(prediction?.inference_ms, 2)} ms</b>
                  </span>
                  <span>
                    Recorded task label
                    <b>
                      {prediction?.truth === 0
                        ? "Left hand"
                        : prediction?.truth === 1
                          ? "Right hand"
                          : "—"}
                    </b>
                  </span>
                  <span>
                    Replay accuracy
                    <b>
                      {frame?.stats.live_accuracy == null
                        ? "—"
                        : `${(frame.stats.live_accuracy * 100).toFixed(1)}%`}
                    </b>
                  </span>
                </div>
              </section>
              <section className="panel lab-panel" id="lab">
                <div className="panel-title">
                  <div>
                    <SlidersHorizontal size={16} />
                    <h2>Perturbation lab</h2>
                  </div>
                  <button
                    className="icon-button"
                    aria-label="Reset perturbations"
                    onClick={reset}
                  >
                    <RotateCcw size={14} />
                  </button>
                </div>
                <p className="lab-description">
                  Controlled shifts, applied in memory.
                </p>
                {[
                  {
                    label: "Gaussian noise",
                    value: noise,
                    set: setNoise,
                    max: 3,
                    step: 0.1,
                    unit: synthetic ? "×20 µV" : "× train RMS",
                  },
                  {
                    label: "Amplitude scaling",
                    value: amplitude,
                    set: setAmplitude,
                    max: 3,
                    step: 0.1,
                    unit: "×",
                  },
                  {
                    label: "Baseline drift",
                    value: drift,
                    set: setDrift,
                    max: 5,
                    step: 0.1,
                    unit: synthetic ? "×20 µV" : "× train RMS",
                  },
                  {
                    label: "50 Hz line noise",
                    value: line,
                    set: setLine,
                    max: 3,
                    step: 0.1,
                    unit: synthetic ? "×20 µV" : "× train RMS",
                  },
                  {
                    label: "Sample loss",
                    value: loss,
                    set: setLoss,
                    max: 0.5,
                    step: 0.01,
                    unit: "fraction",
                  },
                  {
                    label: "Timing jitter",
                    value: jitter,
                    set: setJitter,
                    max: 1,
                    step: 0.1,
                    unit: "samples",
                  },
                ].map((c) => (
                  <label className="slider-row" key={c.label}>
                    <span>
                      {c.label}
                      <b>
                        {c.value.toFixed(c.step === 0.01 ? 2 : 1)}{" "}
                        <small>{c.unit}</small>
                      </b>
                    </span>
                    <input
                      type="range"
                      min={0}
                      max={c.max}
                      step={c.step}
                      value={c.value}
                      onChange={(e) => c.set(Number(e.target.value))}
                    />
                  </label>
                ))}
                <label className="toggle-row">
                  <span>
                    Drop first channel
                    <small>
                      {source?.channel_names[0] ?? "Channel 1"} → zero
                    </small>
                  </span>
                  <input
                    aria-label="Drop first channel"
                    type="checkbox"
                    checked={dropout}
                    onChange={(e) => setDropout(e.target.checked)}
                  />
                </label>
                <div className="preset-buttons">
                  <button
                    onClick={() => {
                      reset();
                      setNoise(1);
                      setAmplitude(2);
                    }}
                  >
                    <Beaker size={12} />
                    Mixed shift
                  </button>
                  <button
                    onClick={() => {
                      reset();
                      setNoise(0.7);
                      setDrift(2);
                    }}
                  >
                    <FlaskConical size={12} />
                    Seed 42 scenario
                  </button>
                </div>
                <div className="lab-status">
                  <span
                    className={`dot ${noise || drift || line || dropout || loss || jitter || amplitude !== 1 ? "perturbed" : "online"}`}
                  />
                  {noise ||
                  drift ||
                  line ||
                  dropout ||
                  loss ||
                  jitter ||
                  amplitude !== 1
                    ? "Perturbations active"
                    : "Clean signal"}
                  <span>seed 42</span>
                </div>
              </section>
            </div>
          </div>
          <section className="performance">
            <div>
              <Wifi size={15} />
              <span>STREAM HEALTH</span>
            </div>
            {[
              {
                label: "Pipeline",
                value: `${format(frame?.stats.pipeline_ms, 2)} ms`,
              },
              {
                label: "Buffer depth",
                value: `${frame?.stats.buffer_samples ?? 0} samples`,
              },
              {
                label: "Missing samples",
                value: String(frame?.stats.missing_samples ?? 0),
              },
              {
                label: "Predictions",
                value: String(frame?.stats.prediction_count ?? 0),
              },
              {
                label: "WS dropped frames",
                value: String(frame?.stats.ws_dropped ?? 0),
              },
            ].map((m) => (
              <div key={m.label}>
                <span>{m.label}</span>
                <b>{m.value}</b>
              </div>
            ))}
          </section>
          <div className="research-note">
            <FlaskConical size={15} />
            <span>
              Research software · Local processing · No physical EEG hardware
              validation · Not a medical device
            </span>
            <a
              href="http://127.0.0.1:8000/docs"
              target="_blank"
              rel="noreferrer"
            >
              <Download size={12} /> API documentation
            </a>
          </div>
        </main>
        <footer>
          <span>
            NeuroStreamLab <b>v{session?.version ?? "0.1.0"}</b>
          </span>
          <span>Syed Abdullah Imam · University of North Texas</span>
          <span>
            <span className="dot online" />
            Hardware-free development
          </span>
        </footer>
      </div>
    </div>
  );
}
