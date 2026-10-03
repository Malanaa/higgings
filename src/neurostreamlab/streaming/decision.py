import numpy as np


class DecisionLayer:
    def __init__(
        self,
        alpha: float = 0.3,
        threshold: float = 0.6,
        dwell: float = 0.5,
        refractory: float = 0.2,
    ):
        if not 0 < alpha <= 1 or not 0.5 <= threshold <= 1 or dwell < 0 or refractory < 0:
            raise ValueError("invalid temporal decision configuration")
        self.alpha, self.threshold, self.dwell, self.refractory = (
            alpha,
            threshold,
            dwell,
            refractory,
        )
        self.smooth = np.array([0.5, 0.5])
        self.candidate: int | None = None
        self.since = 0.0
        self.last_change = float("-inf")
        self.decision: int | None = None

    def update(self, probabilities: np.ndarray, timestamp: float) -> dict:
        p = np.asarray(probabilities)
        if p.shape != (2,) or np.any(p < 0) or not np.isclose(p.sum(), 1):
            raise ValueError("binary probabilities required")
        self.smooth = self.alpha * p + (1 - self.alpha) * self.smooth
        candidate = int(self.smooth.argmax()) if self.smooth.max() >= self.threshold else None
        if candidate != self.candidate:
            self.candidate, self.since = candidate, timestamp
        if (
            timestamp - self.since >= self.dwell
            and timestamp - self.last_change >= self.refractory
            and candidate != self.decision
        ):
            self.decision, self.last_change = candidate, timestamp
        return {
            "raw": p.tolist(),
            "smoothed": self.smooth.tolist(),
            "decision": self.decision,
            "confidence": float(self.smooth.max()),
        }
