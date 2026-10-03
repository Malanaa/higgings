import hashlib
import json
from pathlib import Path
from typing import Protocol

import numpy as np

from neurostreamlab import __version__


class Decoder(Protocol):
    metadata: dict

    def fit(self, x: np.ndarray, y: np.ndarray) -> None: ...
    def predict_proba(self, x: np.ndarray) -> np.ndarray: ...
    def save(self, directory: Path) -> None: ...


def validate_window(x: np.ndarray, metadata: dict) -> np.ndarray:
    if x.ndim == 2:
        x = x[None]
    if x.ndim != 3 or x.shape[1:] != (len(metadata["channels"]), metadata["n_times"]):
        raise ValueError("model channel count or window length mismatch")
    if not np.all(np.isfinite(x)):
        raise ValueError("nonfinite model input")
    return x


def validate_metadata(metadata: dict, channels: list[str], fs: float) -> None:
    if metadata["channels"] != channels or metadata["fs"] != fs:
        raise ValueError("model requires exact channel ordering and sampling frequency")


def write_manifest(directory: Path, metadata: dict, filename: str) -> None:
    contents = {
        **metadata,
        "version": __version__,
        "weights": filename,
        "sha256": hashlib.sha256((directory / filename).read_bytes()).hexdigest(),
    }
    (directory / "manifest.json").write_text(json.dumps(contents, indent=2))


def read_manifest(directory: Path) -> dict:
    manifest = json.loads((directory / "manifest.json").read_text())
    filename = manifest["weights"]
    if Path(filename).name != filename:
        raise ValueError("invalid artifact path")
    if hashlib.sha256((directory / filename).read_bytes()).hexdigest() != manifest["sha256"]:
        raise ValueError("model checksum mismatch")
    return manifest
