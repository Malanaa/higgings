from collections import deque
from dataclasses import dataclass
from threading import RLock

import numpy as np

from neurostreamlab.sources.base import SignalChunk


@dataclass
class BufferStats:
    received_samples: int = 0
    missing_samples: int = 0
    late_chunks: int = 0
    evicted_samples: int = 0
    windows: int = 0


class RollingBuffer:
    def __init__(self, channels: int, fs: float, capacity_seconds: float = 20):
        if channels < 1 or fs <= 0 or capacity_seconds <= 0:
            raise ValueError("positive buffer dimensions required")
        self.channels, self.fs = channels, fs
        self.capacity = int(fs * capacity_seconds)
        self.data: deque = deque(maxlen=self.capacity)
        self.times: deque = deque(maxlen=self.capacity)
        self.lock = RLock()
        self.stats = BufferStats()
        self.last_window_end = float("-inf")

    def append(self, chunk: SignalChunk) -> bool:
        if chunk.data.shape[0] != self.channels:
            raise ValueError("channel mismatch")
        if chunk.data.shape[1] == 0:
            return True
        with self.lock:
            if self.times and chunk.timestamps[0] <= self.times[-1]:
                self.stats.late_chunks += 1
                return False
            deltas = np.diff(chunk.timestamps)
            if self.times:
                deltas = np.r_[chunk.timestamps[0] - self.times[-1], deltas]
            self.stats.missing_samples += int(np.maximum(np.rint(deltas * self.fs) - 1, 0).sum())
            self.stats.evicted_samples += max(
                0, len(self.times) + len(chunk.timestamps) - self.capacity
            )
            self.data.extend(chunk.data.T)
            self.times.extend(chunk.timestamps)
            self.stats.received_samples += len(chunk.timestamps)
            return True

    def latest(self, seconds: float) -> tuple[np.ndarray, np.ndarray] | None:
        n = round(seconds * self.fs)
        if n < 1 or n > self.capacity:
            raise ValueError("window must fit buffer")
        with self.lock:
            if len(self.times) < n:
                return None
            return np.asarray(list(self.data)[-n:]).T.copy(), np.asarray(list(self.times)[-n:])

    def windows(self, seconds: float, stride: float) -> list[tuple[np.ndarray, np.ndarray]]:
        n, step = round(seconds * self.fs), round(stride * self.fs)
        if n < 1 or step < 1 or n > self.capacity:
            raise ValueError("invalid window or stride")
        result = []
        with self.lock:
            data, times = np.asarray(self.data), np.asarray(self.times)
            for end in range(n, len(times) + 1):
                if times[end - 1] <= self.last_window_end + stride - 0.5 / self.fs:
                    continue
                t = times[end - n : end]
                if np.any(np.diff(t) > 1.5 / self.fs):
                    continue
                result.append((data[end - n : end].T.copy(), t.copy()))
                self.last_window_end = float(t[-1])
                self.stats.windows += 1
        return result
