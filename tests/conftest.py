import numpy as np
import pytest

from neurostreamlab.sources.base import SourceMetadata


@pytest.fixture
def metadata():
    return SourceMetadata(
        identifier="fixture",
        name="Deterministic fixture",
        source_type="RECORDED EEG REPLAY",
        sampling_frequency=160,
        channel_names=["C3", "Cz", "C4"],
        channel_types=["eeg"] * 3,
    )


@pytest.fixture
def classification_fixture():
    rng = np.random.default_rng(42)
    y = np.tile([0, 1], 30)
    x = rng.normal(size=(60, 3, 480))
    t = np.arange(480) / 160
    x[y == 0, 0] += 3 * np.sin(2 * np.pi * 10 * t)
    x[y == 1, 2] += 3 * np.sin(2 * np.pi * 18 * t)
    return x, y
