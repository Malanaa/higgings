import { useEffect, useRef, useState } from "react";
import type { FrameData } from "./protocol";

const colors = [
  "#66e1c2",
  "#78a5f8",
  "#c8a4ef",
  "#e2c68d",
  "#8fc4cd",
  "#b3d4a3",
  "#ecaba9",
  "#b6bdee",
];
type Point = { time: number; value: number };

export function SignalCanvas({
  frame,
  paused,
  scale,
  seconds,
  selected,
}: {
  frame: FrameData | null;
  paused: boolean;
  scale: number;
  seconds: number;
  selected: number[];
}) {
  const canvas = useRef<HTMLCanvasElement>(null);
  const buffers = useRef<Point[][]>([]);
  const sourceType = useRef<string | null>(null);
  const lastTimestamp = useRef(-Infinity);
  const current = useRef({ frame, paused, scale, seconds, selected });
  const [fps, setFps] = useState(0);
  useEffect(() => {
    current.current = { frame, paused, scale, seconds, selected };
  }, [frame, paused, scale, seconds, selected]);
  useEffect(() => {
    if (!frame || !frame.timestamps.length) return;
    const end = frame.timestamps.at(-1)!;
    if (
      sourceType.current !== frame.source.source_type ||
      end < lastTimestamp.current
    ) {
      buffers.current = [];
      lastTimestamp.current = -Infinity;
    }
    sourceType.current = frame.source.source_type;
    // A control/heartbeat state change can retain the same signal frame.
    if (end === lastTimestamp.current) return;
    frame.signal.forEach((samples, channel) => {
      const values = buffers.current[channel] ?? [];
      samples.forEach((value, index) =>
        values.push({ time: frame.timestamps[index], value }),
      );
      buffers.current[channel] = values
        .filter((point) => point.time >= end - 10)
        .slice(-Math.ceil(frame.source.sampling_frequency * 10));
    });
    lastTimestamp.current = end;
  }, [frame]);
  useEffect(() => {
    let handle = 0,
      last = 0,
      intervalStart = 0,
      rendered = 0;
    const draw = (now: number) => {
      handle = requestAnimationFrame(draw);
      if (now - last < 33 || current.current.paused) return;
      last = now;
      if (!intervalStart) intervalStart = now;
      rendered++;
      if (now - intervalStart >= 1000) {
        setFps(Math.round((rendered * 1000) / (now - intervalStart)));
        rendered = 0;
        intervalStart = now;
      }
      const el = canvas.current;
      if (!el) return;
      const rect = el.getBoundingClientRect(),
        dpr = devicePixelRatio;
      if (
        el.width !== Math.round(rect.width * dpr) ||
        el.height !== Math.round(rect.height * dpr)
      ) {
        el.width = Math.round(rect.width * dpr);
        el.height = Math.round(rect.height * dpr);
      }
      const ctx = el.getContext("2d");
      if (!ctx) return;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      const w = rect.width,
        h = rect.height;
      ctx.clearRect(0, 0, w, h);
      const cfg = current.current,
        count = cfg.selected.length || 1;
      ctx.font = "11px ui-monospace, monospace";
      ctx.lineWidth = 1;
      for (let i = 0; i < 6; i++) {
        const x = 60 + ((w - 80) * i) / 5;
        ctx.strokeStyle = "#1d2938";
        ctx.beginPath();
        ctx.moveTo(x, 10);
        ctx.lineTo(x, h - 25);
        ctx.stroke();
        ctx.fillStyle = "#728397";
        ctx.fillText(
          `${(-cfg.seconds + (cfg.seconds * i) / 5).toFixed(0)}s`,
          x - 8,
          h - 7,
        );
      }
      const end = Number.isFinite(lastTimestamp.current)
        ? lastTimestamp.current
        : 0;
      cfg.selected.forEach((channel, index) => {
        const baseline = 20 + ((h - 55) * (index + 0.5)) / count;
        ctx.fillStyle = colors[channel % colors.length];
        ctx.fillText(
          cfg.frame?.source.channel_names[channel] ?? `CH ${channel + 1}`,
          8,
          baseline + 4,
        );
        ctx.strokeStyle = "#182332";
        ctx.beginPath();
        ctx.moveTo(60, baseline);
        ctx.lineTo(w - 20, baseline);
        ctx.stroke();
        const points = (buffers.current[channel] ?? []).filter(
          (point) => point.time >= end - cfg.seconds,
        );
        ctx.strokeStyle = colors[channel % colors.length];
        ctx.beginPath();
        let previousTime = -Infinity;
        points.forEach((point) => {
          const x =
            60 + ((point.time - end + cfg.seconds) / cfg.seconds) * (w - 80);
          const y =
            baseline -
            (((Math.max(-cfg.scale, Math.min(cfg.scale, point.value)) /
              cfg.scale) *
              (h - 55)) /
              count) *
              0.42;
          if (
            point.time - previousTime >
            3 / (cfg.frame?.source.sampling_frequency ?? 250)
          )
            ctx.moveTo(x, y);
          else ctx.lineTo(x, y);
          previousTime = point.time;
        });
        ctx.stroke();
      });
    };
    handle = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(handle);
  }, []);
  return (
    <div className="signal-renderer">
      <canvas
        ref={canvas}
        className="signals"
        aria-label="EEG signal traces, horizontal axis source time in seconds, vertical amplitude in microvolts, gaps are not interpolated"
        role="img"
      />
      <span className="renderer-health">
        {paused ? "Display paused" : `Canvas ${fps} FPS`}
      </span>
    </div>
  );
}
