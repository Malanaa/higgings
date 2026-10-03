import asyncio
import json
import logging
import time
import uuid
from dataclasses import asdict
from pathlib import Path

import numpy as np

from neurostreamlab import __version__
from neurostreamlab.config import FilterConfig, PerturbationConfig, load_config
from neurostreamlab.datasets.adapter import load_subject
from neurostreamlab.decoders.base import validate_metadata
from neurostreamlab.decoders.registry import load_decoder
from neurostreamlab.perturbations.engine import PerturbationEngine
from neurostreamlab.preprocessing.pipeline import (
    CausalFilter,
    artifact_flags,
    preprocess_epochs,
    spectrum,
)
from neurostreamlab.preprocessing.topography import electrode_map
from neurostreamlab.server.schemas import StreamMessage
from neurostreamlab.sources.brainflow import BrainFlowSource
from neurostreamlab.sources.recorded import RecordedSource
from neurostreamlab.streaming.buffer import RollingBuffer
from neurostreamlab.streaming.decision import DecisionLayer

logger = logging.getLogger("neurostreamlab")


def prepare_replay(config_path: str = "configs/benchmarks/paper_v1.yaml") -> Path:
    latest = json.loads(Path("results/manifests/latest.json").read_text())
    directory = Path(latest["run_directory"])
    rows = json.loads((directory / "metrics.json").read_text())
    row = next(
        row for row in rows if row["dataset"] == "PhysionetMI" and row["decoder"] == "csp_lda"
    )
    config = load_config(config_path)
    data = load_subject(row["dataset"], row["subject"], config)
    test = np.flatnonzero(data.metadata.split == "test")
    train = np.flatnonzero(data.metadata.split == "train")
    path = Path("data/replay")
    path.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        path / "heldout.npz", x=data.x[test], y=data.y[test], rms=np.std(data.x[train], axis=(0, 2))
    )
    metadata = {
        "dataset": row["dataset"],
        "subject": str(row["subject"]),
        "session": "0",
        "channels": data.channels,
        "fs": data.fs,
        "model": row["model_manifest"],
        "test_trial_ids": data.metadata.iloc[test].trial_id.tolist(),
        "training_trial_ids": data.metadata.iloc[train].trial_id.tolist(),
    }
    if set(metadata["test_trial_ids"]) & set(metadata["training_trial_ids"]):
        raise ValueError("replay leakage")
    (path / "manifest.json").write_text(json.dumps(metadata, indent=2))
    return path


class SessionRuntime:
    def __init__(self):
        self.session_id = str(uuid.uuid4())
        self.source = None
        self.model = None
        self.configs: list[PerturbationConfig] = []
        self.clients: set[asyncio.Queue] = set()
        self.lock = asyncio.Lock()
        self.recording = None
        self.recording_path: str | None = None
        self.running = True
        self.error: str | None = None
        self.prediction: dict | None = None
        self.truth: int | None = None
        self.history: list[dict] = []
        self.decisions = DecisionLayer()
        self.n_predictions = self.correct = 0
        self.ws_dropped = 0
        self.started = time.monotonic()
        self.last_spectrum = 0.0
        self.spectral: dict = {"frequencies": [], "psd": [], "bands": {}}
        self.pace_ms: list[float] = []

    def configure(self, mode: str = "synthetic") -> None:
        if mode == "replay" and not Path("data/replay/manifest.json").exists():
            raise FileNotFoundError("Replay unavailable. Run make replay-demo first.")
        if self.source:
            self.source.close()
        self.model = None
        self.prediction = None
        self.truth = None
        self.decisions = DecisionLayer()
        self.n_predictions = self.correct = 0
        self.history = []
        if mode == "replay":
            from neurostreamlab.sources.base import SourceMetadata

            path = Path("data/replay")
            if not (path / "manifest.json").exists():
                raise FileNotFoundError(
                    "Replay unavailable. Run make replay-demo to download and train the held-out demo."
                )
            metadata = json.loads((path / "manifest.json").read_text())
            with np.load(path / "heldout.npz", allow_pickle=False) as dataset:
                x, y, rms = dataset["x"], dataset["y"], dataset["rms"]
            n = x.shape[-1]
            events = []
            for i, label in enumerate(y):
                events.extend(
                    [
                        {
                            "sample": i * n,
                            "type": "trial_start",
                            "label": int(label),
                            "trial": i,
                            "trial_id": metadata["test_trial_ids"][i],
                        },
                        {
                            "sample": (i + 1) * n - 1,
                            "type": "trial_end",
                            "label": int(label),
                            "trial": i,
                        },
                    ]
                )
            source_metadata = SourceMetadata(
                identifier="heldout-physionet",
                name="PhysioNet held-out hand imagery",
                source_type="RECORDED EEG REPLAY",
                sampling_frequency=metadata["fs"],
                channel_names=metadata["channels"],
                channel_types=["eeg"] * len(metadata["channels"]),
                dataset=metadata["dataset"],
                subject=metadata["subject"],
                session=metadata["session"],
            )
            self.source = RecordedSource(
                np.concatenate(list(x), axis=1), source_metadata, events, chunk_size=16, loop=True
            )
            self.model = load_decoder(Path(metadata["model"]).parent)
            validate_metadata(self.model.metadata, metadata["channels"], metadata["fs"])
            self.filter_config = FilterConfig.model_validate(self.model.metadata["preprocessing"])
            self.reference_rms = rms
        else:
            self.source = BrainFlowSource()
            self.filter_config = FilterConfig()
            self.reference_rms = np.full(self.source.metadata.n_channels, 20.0)
        self.topography = electrode_map(self.source.metadata.channel_names)
        self.source.connect()
        self.source.start()
        self.buffer = RollingBuffer(
            self.source.metadata.n_channels, self.source.metadata.sampling_frequency
        )
        self.causal = CausalFilter(
            self.source.metadata.n_channels,
            self.source.metadata.sampling_frequency,
            self.filter_config,
        )
        self.engine = PerturbationEngine(
            self.configs, self.source.metadata.sampling_frequency, self.reference_rms
        )
        self.trial_data: list[np.ndarray] = []
        self.trial_valid = True
        self.error = None
        self.last_spectrum = 0

    def state(self) -> dict:
        metadata = self.source.metadata.model_dump() if self.source else None
        return {
            "session_id": self.session_id,
            "version": __version__,
            "source": metadata,
            "state": "error"
            if self.error
            else "streaming"
            if self.source and self.source.running
            else "complete"
            if getattr(self.source, "complete", False)
            else "paused",
            "error": self.error,
            "model": self.model.metadata if self.model else None,
            "control_mode": "held-out EEG decoder"
            if self.model
            else "simulated system-test control",
            "perturbations": [c.model_dump() for c in self.configs],
            "recording": self.recording_path,
            "replay_available": Path("data/replay/manifest.json").exists(),
        }

    def set_perturbations(self, configurations: list[PerturbationConfig]) -> None:
        assert self.source is not None
        channels = self.source.metadata.n_channels
        if any(c >= channels for p in configurations for c in p.channels):
            raise ValueError("channel index exceeds current source")
        self.configs = configurations
        self.engine = PerturbationEngine(
            configurations, self.source.metadata.sampling_frequency, self.reference_rms
        )
        self.history.append(
            {
                "type": "perturbation",
                "time": time.monotonic() - self.started,
                "text": ", ".join(p.name for p in configurations) or "clean",
            }
        )

    def control(self, action: str, value: float | None) -> dict:
        assert self.source is not None
        if action in ("synthetic", "replay"):
            self.configure(action)
        elif action == "record":
            if not self.recording:
                Path("sessions").mkdir(exist_ok=True)
                self.recording_path = f"sessions/{self.session_id}-{time.time_ns()}.jsonl"
                self.recording = open(self.recording_path, "w")
                self.recording.write(
                    json.dumps({"schema_version": 1, "type": "metadata", "payload": self.state()})
                    + "\n"
                )
        elif action == "stop_recording":
            if self.recording:
                self.recording.close()
                self.recording = None
            self.recording_path = None
        elif action in ("seek", "speed"):
            if not isinstance(self.source, RecordedSource) or value is None:
                raise ValueError("seek/speed require replay and a value")
            if action == "seek":
                self.source.seek(value)
                self.buffer = RollingBuffer(
                    self.source.metadata.n_channels, self.source.metadata.sampling_frequency
                )
                self.causal = CausalFilter(
                    self.source.metadata.n_channels,
                    self.source.metadata.sampling_frequency,
                    self.filter_config,
                )
                self.trial_data = []
                self.trial_valid = False
                self.prediction = None
                self.decisions = DecisionLayer()
            else:
                self.source.set_speed(value)
        elif action == "pause":
            self.source.pause() if isinstance(self.source, RecordedSource) else self.source.stop()
        elif action == "resume":
            self.source.start()
        elif action == "stop":
            self.source.stop()
            self.buffer = RollingBuffer(
                self.source.metadata.n_channels, self.source.metadata.sampling_frequency
            )
            self.trial_data = []
            self.prediction = None
            self.decisions = DecisionLayer()
        return self.state()

    def tick(self) -> dict | None:
        assert self.source is not None
        start = time.perf_counter_ns()
        chunk = self.source.read()
        if chunk is None:
            return None
        events = chunk.events
        chunk = self.engine.transform_chunk(chunk)
        if chunk is None:
            self.trial_valid = False
            return None
        self.buffer.append(chunk)
        self.causal.transform(chunk.data)
        fs = self.source.metadata.sampling_frequency
        # Decode only complete held-out trials, never train or cue-label-driven control.
        if self.model:
            boundaries = {e["sample"]: e for e in events}
            samples = np.rint(chunk.timestamps * fs).astype(int)
            for i, sample in enumerate(samples):
                event = boundaries.get(sample)
                if event and event["type"] == "trial_start":
                    self.trial_data = []
                    self.trial_valid = True
                    self.truth = event["label"]
                    self.history.append(
                        {
                            "type": "trial",
                            "time": float(chunk.timestamps[i]),
                            "text": f"Trial {event['trial'] + 1}: {'left' if self.truth == 0 else 'right'} task",
                        }
                    )
                self.trial_data.append(chunk.data[:, i : i + 1])
                if event and event["type"] == "trial_end":
                    trial = np.concatenate(self.trial_data, axis=-1)
                    if self.trial_valid and trial.shape[-1] == self.model.metadata["n_times"]:
                        tick_start = time.perf_counter_ns()
                        processed = preprocess_epochs(trial, fs, self.filter_config)
                        infer_start = time.perf_counter_ns()
                        p = self.model.predict_proba(processed)[0]
                        inference_ms = (time.perf_counter_ns() - infer_start) / 1e6
                        self.prediction = {
                            **self.decisions.update(p, float(chunk.timestamps[i])),
                            "inference_ms": inference_ms,
                            "pipeline_ms": (time.perf_counter_ns() - tick_start) / 1e6,
                            "truth": self.truth,
                            "trial": event["trial"],
                        }
                        self.n_predictions += 1
                        self.correct += int(p.argmax() == self.truth)
                    else:
                        self.history.append(
                            {
                                "type": "warning",
                                "time": float(chunk.timestamps[i]),
                                "text": "Incomplete trial skipped after interruption or seek",
                            }
                        )
                    self.trial_data = []
        latest = self.buffer.latest(2)
        now = time.monotonic()
        if latest and now - self.last_spectrum > 1:
            f, p, bands = spectrum(latest[0], fs)
            mask = f <= 50
            self.spectral = {
                "frequencies": f[mask].tolist(),
                "psd": p[mask].tolist(),
                "bands": bands,
            }
            self.last_spectrum = now
        pipeline_ms = (time.perf_counter_ns() - start) / 1e6
        self.pace_ms.append(pipeline_ms)
        self.pace_ms = self.pace_ms[-200:]
        simulated = float(np.sin((now - self.started) * 0.45)) if not self.model else None
        payload = {
            "source": self.source.metadata.model_dump(),
            "topography": {**self.topography, "rms_uv": np.std(chunk.data, axis=-1).tolist()},
            "signal": chunk.data[:8, ::2].tolist(),
            "timestamps": chunk.timestamps[::2].tolist(),
            "events": events,
            "spectrum": self.spectral,
            "prediction": self.prediction,
            "simulated_control": simulated,
            "control_mode": "held-out EEG decoder"
            if self.model
            else "simulated system-test control",
            "stats": {
                **asdict(self.buffer.stats),
                "buffer_samples": len(self.buffer.times),
                "pipeline_ms": pipeline_ms,
                "pipeline_p95_ms": float(np.percentile(self.pace_ms, 95)),
                "prediction_count": self.n_predictions,
                "live_accuracy": self.correct / self.n_predictions if self.n_predictions else None,
                "ws_dropped": self.ws_dropped,
                "uptime_s": now - self.started,
            },
            "artifacts": artifact_flags(chunk.data),
            "timeline": self.history[-8:],
            "perturbations": [c.model_dump() for c in self.configs],
            "state": self.state()["state"],
        }
        return payload

    async def run(self) -> None:
        while self.running:
            try:
                async with self.lock:
                    payload = await asyncio.to_thread(self.tick)
                if payload is not None:
                    message = StreamMessage(
                        type="frame", session_id=self.session_id, payload=payload
                    ).model_dump()
                    if self.recording:
                        # Session exports omit raw signals by default.
                        record = {
                            **message,
                            "payload": {
                                k: v
                                for k, v in payload.items()
                                if k not in ("signal", "timestamps", "spectrum")
                            },
                        }
                        self.recording.write(json.dumps(record) + "\n")
                        self.recording.flush()
                    for queue in list(self.clients):
                        if queue.full():
                            queue.get_nowait()
                            self.ws_dropped += 1
                        queue.put_nowait(message)
            except Exception as exc:
                logger.exception(
                    json.dumps(
                        {
                            "session_id": self.session_id,
                            "type": "runtime_error",
                            "message": str(exc),
                        }
                    )
                )
                self.error = str(exc)
                message = StreamMessage(
                    type="warning", session_id=self.session_id, payload={"message": str(exc)}
                ).model_dump()
                for queue in list(self.clients):
                    if not queue.full():
                        queue.put_nowait(message)
                await asyncio.sleep(1)
            await asyncio.sleep(1 / 30)

    def close(self) -> None:
        self.running = False
        if self.source:
            self.source.close()
        if self.recording:
            self.recording.close()
