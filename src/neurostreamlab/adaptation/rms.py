import numpy as np


class RMSAlignment:
    """Unlabeled expanding RMS alignment. Current trial is included, no future trial.

    Reference statistics are fixed from training. No class labels are accepted.
    Per-channel correction is clipped to avoid exploding dropped channels.
    """

    def __init__(self, reference: np.ndarray):
        self.reference = np.asarray(reference)
        self.sum_squares = np.zeros_like(self.reference)
        self.count = 0

    def transform(self, trial: np.ndarray) -> np.ndarray:
        centered = trial - trial.mean(axis=-1, keepdims=True)
        self.sum_squares += np.square(centered).sum(axis=-1)
        self.count += trial.shape[-1]
        rms = np.sqrt(self.sum_squares / self.count)
        ratio = np.clip(self.reference / np.maximum(rms, 1e-9), 0.25, 4)
        return centered * ratio[:, None]
