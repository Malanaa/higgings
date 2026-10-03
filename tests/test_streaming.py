import time

import numpy as np
import pytest
from pydantic import ValidationError

from neurostreamlab.sources.base import SignalChunk, SourceMetadata
from neurostreamlab.sources.brainflow import BrainFlowSource
from neurostreamlab.sources.recorded import RecordedSource
from neurostreamlab.streaming.buffer import RollingBuffer
from neurostreamlab.streaming.decision import DecisionLayer


def test_metadata_validation(metadata):
    assert metadata.n_channels == 3
    with pytest.raises(ValidationError):
        SourceMetadata(**{**metadata.model_dump(), "sampling_frequency": float("inf")})
    with pytest.raises(ValidationError):
        SourceMetadata(**{**metadata.model_dump(), "sampling_frequency": 0})
    with pytest.raises(ValidationError):
        SourceMetadata(**{**metadata.model_dump(), "channel_types": []})


@pytest.mark.parametrize("times", [[0, 0], [1, 0], [0, float("nan")]])
def test_chunk_validation(times):
    with pytest.raises(ValueError):
        SignalChunk(np.zeros((3, 2)), np.array(times), 0)


def test_replay_pacing_pause_seek_loop(metadata):
    now = [0.0]
    data = np.arange(96).reshape(3, 32)
    source = RecordedSource(
        data,
        metadata,
        [{"sample": 5, "type": "trial_start"}],
        chunk_size=8,
        clock=lambda: now[0],
        loop=True,
    )
    with pytest.raises(RuntimeError):
        source.start()
    source.connect()
    source.start()
    a = source.read()
    assert a.data.shape == (3, 8) and len(a.events) == 1
    assert source.read() is None
    now[0] += 0.05
    b = source.read()
    assert b.timestamps[0] > a.timestamps[-1]
    source.pause()
    now[0] += 10
    assert source.read() is None
    source.resume()
    assert source.read() is not None
    source.seek(0)
    assert source.generation == 1
    source.accelerated = True
    chunks = [source.read() for _ in range(5)]
    assert chunks[-1].timestamps[0] > chunks[-2].timestamps[-1]
    source.close()
    assert not source.connected


def test_replay_complete(metadata):
    s = RecordedSource(np.ones((3, 16)), metadata, chunk_size=8, accelerated=True)
    s.connect()
    s.start()
    assert s.read() is not None
    assert s.read() is not None
    assert s.read() is None and s.complete
    with pytest.raises(ValueError):
        s.seek(1)
    with pytest.raises(ValueError):
        s.set_speed(0)
    s.stop()
    assert s.position == 0


def test_buffer_boundary_overlap_and_gaps():
    b = RollingBuffer(3, 10, 2)
    b.append(SignalChunk(np.ones((3, 10)), np.arange(10) / 10, 0))
    assert b.latest(2) is None
    assert len(b.windows(1, 0.5)) == 1
    b.append(SignalChunk(np.ones((3, 10)), np.arange(10, 20) / 10, 1))
    windows = b.windows(1, 0.5)
    assert len(windows) == 2
    assert np.allclose(windows[0][1], np.arange(5, 15) / 10)
    assert not b.append(SignalChunk(np.ones((3, 2)), np.array([1.7, 1.8]), 2))
    b.append(SignalChunk(np.ones((3, 2)), np.array([2.2, 2.3]), 3))
    assert b.stats.missing_samples == 2 and b.stats.late_chunks == 1
    assert b.stats.evicted_samples == 2 and len(b.times) == 20
    assert not b.windows(1, 0.1)
    with pytest.raises(ValueError):
        b.latest(3)
    with pytest.raises(ValueError):
        b.append(SignalChunk(np.ones((2, 1)), np.array([3.0]), 4))


def test_buffer_empty():
    b = RollingBuffer(2, 10)
    assert b.windows(1, 0.1) == []


def test_decision_dwell():
    decision = DecisionLayer(alpha=1, dwell=0.5)
    assert decision.update(np.array([0.8, 0.2]), 0)["decision"] is None
    assert decision.update(np.array([0.8, 0.2]), 0.6)["decision"] == 0
    assert decision.update(np.array([0.2, 0.8]), 0.7)["decision"] == 0
    assert decision.update(np.array([0.2, 0.8]), 1.3)["decision"] == 1
    with pytest.raises(ValueError):
        decision.update(np.array([1, 1]), 2)


def test_brainflow_real_synthetic_lifecycle():
    source = BrainFlowSource()
    try:
        source.connect()
        source.start()
        time.sleep(0.08)
        chunk = source.read()
        assert chunk is not None and chunk.data.shape[0] == source.metadata.n_channels
        assert np.all(np.diff(chunk.timestamps) > 0)
        assert source.metadata.source_type == "SYNTHETIC"
        source.stop()
        assert source.read() is None
    finally:
        source.close()


@pytest.mark.parametrize("board_id", [-2, 0, 1])
def test_hardware_requires_explicit_permission(board_id):
    with pytest.raises(ValueError, match="allow_hardware"):
        BrainFlowSource(board_id)
