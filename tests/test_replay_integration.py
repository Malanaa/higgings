import json

import numpy as np
from fastapi.testclient import TestClient

from neurostreamlab.config import FilterConfig
from neurostreamlab.decoders.registry import create_decoder
from neurostreamlab.preprocessing.pipeline import preprocess_epochs
from neurostreamlab.server.app import create_app
from neurostreamlab.server.runtime import SessionRuntime


def test_deterministic_recorded_to_decoder_decision_recording(
    classification_fixture, tmp_path, monkeypatch
):
    x, y = classification_fixture
    config = FilterConfig()
    model = create_decoder(
        "csp_lda",
        {
            "channels": ["C3", "Cz", "C4"],
            "fs": 160,
            "n_times": 480,
            "seed": 42,
            "classes": ["left_hand", "right_hand"],
            "preprocessing": config.model_dump(),
            "preprocessing_id": "trial_zero_phase_v1",
            "training_seconds": 0,
        },
    )
    model.fit(preprocess_epochs(x[:40], 160, config), y[:40])
    model.save(tmp_path / "model")
    replay = tmp_path / "data/replay"
    replay.mkdir(parents=True)
    np.savez_compressed(replay / "heldout.npz", x=x[40:], y=y[40:], rms=np.std(x[:40], axis=(0, 2)))
    (replay / "manifest.json").write_text(
        json.dumps(
            {
                "dataset": "deterministic engineering fixture",
                "subject": "fixture",
                "session": "test",
                "channels": ["C3", "Cz", "C4"],
                "fs": 160,
                "model": str(tmp_path / "model/manifest.json"),
                "test_trial_ids": [f"test{i}" for i in range(20)],
                "training_trial_ids": [f"train{i}" for i in range(40)],
            }
        )
    )
    monkeypatch.chdir(tmp_path)
    runtime = SessionRuntime()
    try:
        runtime.configure("replay")
        runtime.source.accelerated = True
        frames = [runtime.tick() for _ in range(100)]
        assert runtime.n_predictions >= 3
        prediction = next(f["prediction"] for f in frames if f and f["prediction"])
        assert np.isclose(sum(prediction["raw"]), 1)
        assert prediction["inference_ms"] >= 0
    finally:
        runtime.close()
    app = create_app("replay")
    with TestClient(app) as client:
        runtime = app.state.runtime
        client.post("/api/control", json={"action": "pause"})
        runtime.source.accelerated = True
        client.post("/api/control", json={"action": "resume"})
        client.post("/api/control", json={"action": "record"})
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "source_status"
            frame = ws.receive_json()
            assert frame["payload"]["source"]["source_type"] == "RECORDED EEG REPLAY"
            assert frame["payload"]["simulated_control"] is None
        client.post(
            "/api/perturbations",
            json={"configurations": [{"name": "gaussian_noise", "intensity": 1}]},
        )
        client.post("/api/control", json={"action": "seek", "value": 0})
        assert not runtime.trial_valid
        client.post("/api/control", json={"action": "stop_recording"})
    assert list(tmp_path.glob("sessions/*.jsonl"))
