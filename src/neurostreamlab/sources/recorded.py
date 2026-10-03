import time
from collections.abc import Callable

import numpy as np

from neurostreamlab.sources.base import SignalChunk, SourceMetadata


class RecordedSource:
    """Paced incremental replay, with deterministic accelerated reads for tests.

    Source time is independent of playback speed. Loop timestamps remain monotonic.
    Seek increments a generation so consumers can flush filter and buffer state.
    """

    def __init__(
        self,
        data: np.ndarray,
        metadata: SourceMetadata,
        events: list[dict] | None = None,
        *,
        chunk_size: int = 32,
        speed: float = 1,
        loop: bool = False,
        accelerated: bool = False,
        clock: Callable[[], float] = time.monotonic,
    ):
        if data.ndim != 2 or data.shape[0] != metadata.n_channels or data.shape[1] == 0:
            raise ValueError("recording shape incompatible with metadata")
        if chunk_size <= 0 or speed <= 0:
            raise ValueError("positive chunk size and speed required")
        self.data = data
        self.metadata = metadata.model_copy(update={"source_type": "RECORDED EEG REPLAY"})
        self.events = events or []
        self.chunk_size, self.speed, self.loop = chunk_size, speed, loop
        self.accelerated, self.clock = accelerated, clock
        self.position = self.cycle = self.sequence = self.generation = 0
        self.running = self.connected = self.complete = False
        self.deadline = 0.0

    def connect(self) -> None:
        self.connected = True

    def start(self) -> None:
        if not self.connected:
            raise RuntimeError("connect before start")
        self.running = True
        self.deadline = self.clock()
        self.metadata.start_timestamp = time.time()

    def pause(self) -> None:
        self.running = False

    def resume(self) -> None:
        self.start()

    def seek(self, seconds: float) -> None:
        if not 0 <= seconds < self.data.shape[1] / self.metadata.sampling_frequency:
            raise ValueError("seek outside recording")
        self.position = int(seconds * self.metadata.sampling_frequency)
        self.cycle = self.sequence = 0
        self.generation += 1
        self.complete = False
        self.deadline = self.clock()

    def set_speed(self, speed: float) -> None:
        if not 0.1 <= speed <= 20:
            raise ValueError("speed must be between 0.1 and 20")
        self.speed = speed
        self.deadline = self.clock()

    def read(self) -> SignalChunk | None:
        if not self.running or (not self.accelerated and self.clock() < self.deadline):
            return None
        fs, length = self.metadata.sampling_frequency, self.data.shape[1]
        if self.position == length:
            if not self.loop:
                self.running = False
                self.complete = True
                return None
            self.position = 0
            self.cycle += 1
        end = min(self.position + self.chunk_size, length)
        offset = self.cycle * length
        events = [
            {**e, "sample": e["sample"] + offset, "cycle": self.cycle}
            for e in self.events
            if self.position <= e["sample"] < end
        ]
        chunk = SignalChunk(
            self.data[:, self.position : end].copy(),
            (np.arange(self.position, end) + offset) / fs,
            self.sequence,
            events,
        )
        self.deadline = max(self.deadline, self.clock()) + (end - self.position) / fs / self.speed
        self.position = end
        self.sequence += 1
        return chunk

    def stop(self) -> None:
        self.running = False
        self.position = self.cycle = self.sequence = 0
        self.complete = False
        self.generation += 1

    def close(self) -> None:
        self.stop()
        self.connected = False
