import { useEffect, useRef } from "react";
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
  const buffers = useRef<number[][]>([]);
  const current = useRef({ frame, paused, scale, seconds, selected });
  useEffect(() => {
    if (
      frame &&
      current.current.frame?.source.source_type !== frame.source.source_type
    )
      buffers.current = [];
    current.current = { frame, paused, scale, seconds, selected };
    if (frame) {
      frame.signal.forEach((samples, i) => {
        const a = buffers.current[i] ?? [];
        a.push(...samples);
        const max = (frame.source.sampling_frequency * 10) / 2;
        buffers.current[i] = a.slice(-max);
      });
    }
  }, [frame, paused, scale, seconds, selected]);
  useEffect(() => {
    let handle = 0;
    let last = 0;
    const draw = (now: number) => {
      handle = requestAnimationFrame(draw);
      if (now - last < 33 || current.current.paused) return;
      last = now;
      const el = canvas.current;
      if (!el) return;
      const rect = el.getBoundingClientRect();
      const dpr = devicePixelRatio;
      el.width = rect.width * dpr;
      el.height = rect.height * dpr;
      const ctx = el.getContext("2d");
      if (!ctx) return;
      ctx.scale(dpr, dpr);
      const w = rect.width,
        h = rect.height;
      ctx.clearRect(0, 0, w, h);
      const cfg = current.current;
      const count = cfg.selected.length || 1;
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
      cfg.selected.forEach((channel, index) => {
        const y = 20 + ((h - 55) * (index + 0.5)) / count;
        ctx.fillStyle = colors[channel % colors.length];
        ctx.fillText(
          cfg.frame?.source.channel_names[channel] ?? `CH ${channel + 1}`,
          8,
          y + 4,
        );
        ctx.strokeStyle = "#182332";
        ctx.beginPath();
        ctx.moveTo(60, y);
        ctx.lineTo(w - 20, y);
        ctx.stroke();
        const values = (buffers.current[channel] ?? []).slice(
          -(((cfg.frame?.source.sampling_frequency ?? 250) * cfg.seconds) / 2),
        );
        ctx.strokeStyle = colors[channel % colors.length];
        ctx.beginPath();
        values.forEach((v, j) => {
          const x = 60 + (j / Math.max(1, values.length - 1)) * (w - 80);
          const yy =
            y -
            (((Math.max(-cfg.scale, Math.min(cfg.scale, v)) / cfg.scale) *
              (h - 55)) /
              count) *
              0.42;
          if (j === 0) ctx.moveTo(x, yy);
          else ctx.lineTo(x, yy);
        });
        ctx.stroke();
      });
    };
    handle = requestAnimationFrame(draw);
    return () => cancelAnimationFrame(handle);
  }, []);
  return (
    <canvas
      ref={canvas}
      className="signals"
      aria-label="EEG signal traces, horizontal axis time in seconds, vertical amplitude in microvolts"
      role="img"
    />
  );
}
