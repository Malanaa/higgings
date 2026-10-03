"""Measure local synthetic processing and accelerated held-out replay processing.

Not physical hardware latency, not browser render latency.
"""

import json
import time
from pathlib import Path

import numpy as np

from neurostreamlab.evaluation.runner import software_metadata
from neurostreamlab.server.runtime import SessionRuntime

results = {"machine": software_metadata(), "modes": {}}
for mode in ("synthetic", "replay"):
    runtime = SessionRuntime()
    try:
        runtime.configure(mode)
        if mode == "replay":
            runtime.source.accelerated = True
        durations = []
        for _i in range(500 if mode == "replay" else 120):
            if mode == "synthetic":
                time.sleep(1 / 30)
            frame = runtime.tick()
            if frame:
                durations.append(frame["stats"]["pipeline_ms"])
        results["modes"][mode] = {
            "frames": len(durations),
            "raw_pipeline_ms": durations,
            "median_ms": float(np.median(durations)),
            "p95_ms": float(np.percentile(durations, 95)),
            "predictions": runtime.n_predictions,
            "missing_samples": runtime.buffer.stats.missing_samples,
            "scope": "source read through serialized frame construction, excluding WebSocket transport and browser rendering",
        }
    finally:
        runtime.close()
Path("results/raw/streaming_profile.json").write_text(json.dumps(results, indent=2))
print(
    json.dumps(
        {
            mode: {key: value for key, value in result.items() if key != "raw_pipeline_ms"}
            for mode, result in results["modes"].items()
        },
        indent=2,
    )
)
