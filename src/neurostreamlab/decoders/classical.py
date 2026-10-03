from pathlib import Path

import numpy as np
from mne.decoding import CSP
from scipy.special import expit
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

from neurostreamlab.decoders.base import read_manifest, validate_window, write_manifest


class ClassicalDecoder:
    def __init__(self, kind: str, metadata: dict):
        if kind not in ("csp_lda", "bandpower_logreg"):
            raise ValueError("unknown classical model")
        self.kind, self.metadata = kind, {**metadata, "decoder": kind}
        self.arrays: dict[str, np.ndarray] = {}

    def _features(self, x: np.ndarray) -> np.ndarray:
        if self.kind == "csp_lda":
            projected = np.einsum("kc,nct->nkt", self.arrays["filters"], x)
            return np.log(np.maximum(np.square(projected).mean(axis=-1), 1e-30))
        # Log bandpower in the configured sensorimotor band, after filtering.
        return np.log(np.maximum(np.square(x).mean(axis=-1), 1e-30))

    def fit(self, x: np.ndarray, y: np.ndarray) -> None:
        x = validate_window(x, self.metadata)
        if set(np.unique(y)) != {0, 1}:
            raise ValueError("training requires both classes 0 and 1")
        if self.kind == "csp_lda":
            components = min(4, x.shape[1])
            csp = CSP(n_components=components, reg="oas", log=True, norm_trace=False)
            csp.fit(x, y)
            self.arrays["filters"] = csp.filters_[:components]
            classifier = LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto")
        else:
            classifier = LogisticRegression(
                C=1, random_state=self.metadata.get("seed", 42), max_iter=1000
            )
        features = self._features(x)
        scaler = StandardScaler().fit(features)
        classifier.fit(scaler.transform(features), y)
        self.arrays.update(
            mean=scaler.mean_,
            scale=scaler.scale_,
            coef=classifier.coef_,
            intercept=classifier.intercept_,
        )
        self.metadata["architecture"] = {
            "features": "log spatial variance"
            if self.kind == "csp_lda"
            else "log channel variance",
            "components": len(self.arrays.get("filters", [])),
            "classifier": type(classifier).__name__,
        }

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        if "coef" not in self.arrays:
            raise RuntimeError("decoder is not fitted")
        features = self._features(validate_window(x, self.metadata))
        z = ((features - self.arrays["mean"]) / self.arrays["scale"]) @ self.arrays[
            "coef"
        ].T + self.arrays["intercept"]
        p = expit(z[:, 0])
        return np.column_stack([1 - p, p])

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(directory / "weights.npz", **self.arrays)  # type: ignore[arg-type]
        write_manifest(directory, self.metadata, "weights.npz")

    @classmethod
    def load(cls, directory: Path):
        metadata = read_manifest(directory)
        model = cls(metadata["decoder"], metadata)
        with np.load(directory / metadata["weights"], allow_pickle=False) as arrays:
            model.arrays = {key: arrays[key] for key in arrays.files}
        return model
