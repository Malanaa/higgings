import numpy as np
from scipy.signal import butter, detrend, iirnotch, sosfilt, sosfiltfilt, tf2sos, welch

from neurostreamlab.config import FilterConfig


def design_filter(config: FilterConfig, fs: float) -> np.ndarray:
    if config.high >= fs / 2 or (config.notch is not None and config.notch >= fs / 2):
        raise ValueError("filter frequencies must lie below Nyquist")
    sos = butter(config.order, [config.low, config.high], btype="bandpass", fs=fs, output="sos")
    if config.notch is not None:
        b, a = iirnotch(config.notch, 30, fs)
        sos = np.vstack([tf2sos(b, a), sos])
    return sos


def preprocess_epochs(x: np.ndarray, fs: float, config: FilterConfig) -> np.ndarray:
    """Trial-local zero-phase filtering. Never learns from other trials."""
    x = np.asarray(x, dtype=np.float64)
    if config.reference == "average":
        x = x - x.mean(axis=-2, keepdims=True)
    if config.detrend:
        x = detrend(x, axis=-1, type="constant")
    return sosfiltfilt(design_filter(config, fs), x, axis=-1)


class CausalFilter:
    def __init__(self, channels: int, fs: float, config: FilterConfig):
        self.sos = design_filter(config, fs)
        self.zi = np.zeros((len(self.sos), channels, 2))
        self.config = config

    def transform(self, x: np.ndarray) -> np.ndarray:
        if self.config.reference == "average":
            x = x - x.mean(axis=0, keepdims=True)
        # Bandpass removes DC causally. No per-chunk mean subtraction.
        y, self.zi = sosfilt(self.sos, x, axis=-1, zi=self.zi)
        return y


def spectrum(x: np.ndarray, fs: float) -> tuple[np.ndarray, np.ndarray, dict[str, float]]:
    f, p = welch(x, fs=fs, nperseg=min(x.shape[-1], round(fs * 2)), axis=-1)
    p = p.mean(axis=0)
    bands = {
        "delta": (1, 4),
        "theta": (4, 8),
        "alpha": (8, 13),
        "beta": (13, 30),
        "gamma": (30, min(45, fs / 2)),
    }
    powers = {
        name: float(np.trapezoid(p[(f >= lo) & (f < hi)], f[(f >= lo) & (f < hi)]))
        for name, (lo, hi) in bands.items()
    }
    return f, p, powers


def artifact_flags(x: np.ndarray) -> dict:
    return {
        "peak_uv": float(np.max(np.abs(x))),
        "flat_channels": np.where(np.std(x, axis=-1) < 1e-6)[0].tolist(),
        "high_amplitude": bool(np.max(np.abs(x)) > 200),
    }
