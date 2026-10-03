import json

from fastapi.testclient import TestClient

from neurostreamlab.server.app import create_app


def test_synthetic_to_websocket_recording_and_shutdown(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    app = create_app("synthetic")
    with TestClient(app) as client:
        assert client.get("/api/health").json()["status"] == "ok"
        assert client.get("/api/session").json()["source"]["source_type"] == "SYNTHETIC"
        assert "csp_lda" in client.get("/api/decoders").json()
        assert client.post("/api/control", json={"action": "record"}).status_code == 200
        with client.websocket_connect("/ws") as ws:
            assert ws.receive_json()["type"] == "source_status"
            message = ws.receive_json()
            assert message["schema_version"] == 1
            assert message["type"] == "frame"
            assert message["payload"]["source"]["source_type"] == "SYNTHETIC"
            assert message["payload"]["prediction"] is None
            assert "system-test" in message["payload"]["control_mode"]
        assert (
            client.post(
                "/api/perturbations",
                json={"configurations": [{"name": "channel_dropout", "channels": [0]}]},
            ).status_code
            == 200
        )
        assert (
            client.post(
                "/api/perturbations",
                json={"configurations": [{"name": "channel_dropout", "channels": [999]}]},
            ).status_code
            == 400
        )
        assert client.post("/api/control", json={"action": "seek", "value": 3}).status_code == 400
        assert client.post("/api/control", json={"action": "stop_recording"}).status_code == 200
    records = list(tmp_path.glob("sessions/*.jsonl"))
    assert len(records) == 1
    lines = [json.loads(line) for line in records[0].read_text().splitlines()]
    assert lines[0]["type"] == "metadata" and any(row["type"] == "frame" for row in lines)
    assert not app.state.runtime.source.connected
