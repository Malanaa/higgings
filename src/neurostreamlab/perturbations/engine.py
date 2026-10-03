import numpy as np

from neurostreamlab.config import PerturbationConfig
from neurostreamlab.sources.base import SignalChunk


class PerturbationEngine:
    """Seeded transforms in microvolt units. Noise uses training-only channel RMS.

    Dropout and timing transforms are source-level. Array mode models missing samples
    as zero-filled values and timing jitter as interpolation on displaced time points.
    """

    def __init__(self, configs: list[PerturbationConfig], fs: float, reference_rms: np.ndarray):
        self.configs, self.fs = configs, fs
        self.rms = np.asarray(reference_rms).reshape(-1, 1)
        self.rngs = [np.random.default_rng(c.seed) for c in configs]

    def transform(self, x: np.ndarray, start_time: float = 0) -> np.ndarray:
        if x.ndim != 2 or x.shape[0] != len(self.rms):
            raise ValueError("perturbation channel mismatch")
        y = x.copy()
        times = start_time + np.arange(x.shape[-1]) / self.fs
        for c, rng in zip(self.configs, self.rngs, strict=True):
            active = (times >= c.start) & ((times < c.end) if c.end else True)
            idx = np.flatnonzero(active)
            if len(idx) == 0 or c.name == "clean":
                continue
            ch = c.channels or list(range(x.shape[0]))
            if any(i >= x.shape[0] for i in ch):
                raise ValueError("perturbation channel out of range")
            if c.name == "gaussian_noise":
                y[:, idx] += c.intensity * self.rms * rng.normal(size=(x.shape[0], len(idx)))
            elif c.name == "channel_noise":
                y[np.ix_(ch, idx)] += (
                    c.intensity * self.rms[ch] * rng.normal(size=(len(ch), len(idx)))
                )
            elif c.name == "amplitude":
                y[:, idx] *= c.intensity
            elif c.name == "baseline_drift":
                y[:, idx] += c.intensity * self.rms * np.sin(2 * np.pi * c.frequency * times[idx])
            elif c.name == "line_noise":
                y[:, idx] += c.intensity * self.rms * np.sin(2 * np.pi * c.frequency * times[idx])
            elif c.name == "channel_dropout":
                y[np.ix_(ch, idx)] = 0
            elif c.name == "random_dropout":
                count = min(round(c.intensity), x.shape[0])
                lost = rng.choice(x.shape[0], count, replace=False)
                y[np.ix_(lost, idx)] = 0
            elif c.name == "sample_loss":
                y[:, idx[rng.random(len(idx)) < c.intensity]] = 0
            elif c.name == "interruption":
                y[:, idx[: round(c.intensity * len(idx))]] = 0
            elif c.name == "timing_jitter":
                warped = times[idx] + rng.normal(0, c.intensity / self.fs, len(idx))
                for channel in range(x.shape[0]):
                    y[channel, idx] = np.interp(warped, times, y[channel])
        return y

    def transform_chunk(self, chunk: SignalChunk) -> SignalChunk | None:
        # Transport effects preserve timestamps and expose real missing-sample gaps.
        signal_configs = [
            c
            for c in self.configs
            if c.name not in ("sample_loss", "timing_jitter", "interruption")
        ]
        original = self.configs
        self.configs = signal_configs
        original_rngs = self.rngs
        self.rngs = [
            r
            for c, r in zip(original, original_rngs, strict=True)
            if c.name not in ("sample_loss", "timing_jitter", "interruption")
        ]
        try:
            y = self.transform(chunk.data, float(chunk.timestamps[0]))
        finally:
            self.configs, self.rngs = original, original_rngs
        keep = np.ones(len(chunk.timestamps), dtype=bool)
        t = chunk.timestamps.copy()
        for c, rng in zip(self.configs, self.rngs, strict=True):
            active = (t >= c.start) & ((t < c.end) if c.end else True)
            if c.name == "sample_loss":
                keep &= ~(active & (rng.random(len(t)) < c.intensity))
            elif c.name == "interruption":
                duration = c.intensity if c.end is None else (c.end - c.start) * c.intensity
                keep &= ~((t >= c.start) & (t < c.start + duration))
            elif c.name == "timing_jitter":
                # Bounded jitter below half a sample retains within-chunk order.
                t[active] += (
                    rng.uniform(-0.45, 0.45, int(active.sum())) * min(c.intensity, 1) / self.fs
                )
        if not keep.any():
            return None
        return SignalChunk(y[:, keep], t[keep], chunk.sequence, chunk.events)
