# Stream and session export protocol

WebSocket /ws messages are JSON with schema_version: 1, type, session_id and payload. Types are source_status, frame and warning. Unknown versions or malformed frames produce an actionable frontend error instead of silently freezing. Reconnection retries with a bounded delay. The current protocol sends a batched frame envelope containing conceptual signal, spectrum, prediction, decision, telemetry, marker and perturbation updates to minimize envelope overhead.

A frame contains:
- source: source_type (SYNTHETIC, RECORDED EEG REPLAY or LIVE HARDWARE), sampling_frequency, channel_names, units and optional dataset/subject/session.
- signal: channel-major arrays, up to eight channels, with matching timestamps. Display downsampling is not model preprocessing.
- spectrum: frequency bins in Hz, PSD in microvolt squared per Hz, and integrated delta/theta/alpha/beta/gamma power. Bands are signal descriptions, not inferred mental states.
- prediction: null when no trained output exists, otherwise raw and smoothed binary probabilities, nullable decision, confidence, inference_ms, trial pipeline_ms, trial index and recorded task label.
- simulated_control: numeric only in synthetic mode, never called decoded intention.
- stats: sample counters, buffer depth, software-processing times, replay prediction count, raw trial replay accuracy and dropped WebSocket display frames.
- events and timeline: recorded task boundaries and perturbation changes.
- perturbations: validated serialized configuration.
- state: streaming, paused, complete or error.

Warning payloads contain a message. Source status includes source metadata, model metadata, recording state and error. Heartbeats continue during pause. Commands POST /api/control support synthetic, replay, pause, resume, stop, seek, speed, record and stop_recording. POST /api/perturbations accepts a configurations array. Configurations reject unknown names, invalid fractions and incompatible channels.

Session files are sessions/<session ID>-<timestamp>.jsonl. The first row is a versioned metadata message. Subsequent rows retain frame payloads without signal/timestamps/spectrum, so predictions, decisions, markers, shifts and timings are exported while raw EEG is omitted. Export is local and no webcam or microphone exists. Recording paths are generated internally, not supplied by untrusted browser clients.
