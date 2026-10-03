import { z } from "zod";
const Source = z.object({
  name: z.string(),
  source_type: z.enum(["SYNTHETIC", "RECORDED EEG REPLAY", "LIVE HARDWARE"]),
  sampling_frequency: z.number().positive(),
  channel_names: z.array(z.string()),
  subject: z.string().nullable(),
  dataset: z.string().nullable(),
  session: z.string(),
});
const Prediction = z.object({
  raw: z.array(z.number()).length(2),
  smoothed: z.array(z.number()).length(2),
  decision: z.number().nullable(),
  confidence: z.number(),
  inference_ms: z.number(),
  pipeline_ms: z.number(),
  truth: z.number().nullable(),
  trial: z.number(),
});
export const Frame = z.object({
  source: Source,
  topography: z
    .object({
      available: z.boolean(),
      template: z.string().optional(),
      electrodes: z.array(
        z.object({
          channel: z.string(),
          index: z.number(),
          x: z.number(),
          y: z.number(),
        }),
      ),
      rms_uv: z.array(z.number()),
    })
    .optional(),
  signal: z.array(z.array(z.number())),
  timestamps: z.array(z.number()),
  spectrum: z.object({
    frequencies: z.array(z.number()),
    psd: z.array(z.number()),
    bands: z.record(z.string(), z.number()),
  }),
  prediction: Prediction.nullable(),
  simulated_control: z.number().nullable(),
  control_mode: z.string(),
  stats: z.object({
    received_samples: z.number(),
    missing_samples: z.number(),
    late_chunks: z.number(),
    buffer_samples: z.number(),
    pipeline_ms: z.number(),
    pipeline_p95_ms: z.number(),
    prediction_count: z.number(),
    live_accuracy: z.number().nullable(),
    ws_dropped: z.number(),
    uptime_s: z.number(),
  }),
  timeline: z.array(
    z.object({ type: z.string(), time: z.number(), text: z.string() }),
  ),
  state: z.string(),
});
export const Message = z.object({
  schema_version: z.literal(1),
  type: z.enum(["frame", "warning", "source_status"]),
  session_id: z.string(),
  payload: z.unknown(),
});
export type FrameData = z.infer<typeof Frame>;
export type Session = {
  version: string;
  source: z.infer<typeof Source> | null;
  state: string;
  error: string | null;
  model: {
    decoder: string;
    version?: string;
    channels: string[];
    classes: string[];
    preprocessing_id: string;
    training_seconds: number;
  } | null;
  session_id: string;
  recording: string | null;
  replay_available: boolean;
};
export async function api(path: string, body?: unknown) {
  const r = await fetch(
    `/api/${path}`,
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  const data = await r.json();
  if (!r.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Invalid request. Check the supplied controls.",
    );
  return data;
}
