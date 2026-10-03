import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path

import mne
import numpy as np
import pandas as pd

from neurostreamlab.config import BenchmarkConfig

DATA_ROOT = Path(os.environ.get("NEUROSTREAMLAB_DATA", "data")).resolve()
os.environ.setdefault("MNE_DATA", str(DATA_ROOT))
os.environ.setdefault("MNE_DONTWRITE_HOME", "true")
DATASETS = {
    "PhysionetMI": {
        "license": "Open Data Commons Attribution License v1.0",
        "url": "https://physionet.org/content/eegmmidb/1.0.0/",
        "protocol": "imagined left/right hands, runs 4 and 8 train, run 12 test",
    },
    "BNCI2014_001": {
        "license": "CC BY-ND 4.0 (see source terms)",
        "url": "https://bnci-horizon-2020.eu/database/data-sets",
        "protocol": "left/right hands, first session train, second session test",
    },
}


@dataclass
class EpochDataset:
    x: np.ndarray
    y: np.ndarray
    metadata: pd.DataFrame
    channels: list[str]
    fs: float


def _physionet(subject: int, config: BenchmarkConfig) -> EpochDataset:
    """MNE's official EDF reader downloads only the three hand-imagery runs.

    MOABB's Physionet adapter is also exposed by dataset commands, but its full
    imagined task download includes feet/hands tasks unused in this binary protocol.
    """
    xs, ys = [], []
    rows: list[dict] = []
    fs = 0.0
    channels = []
    for run in (4, 8, 12):
        filenames = mne.datasets.eegbci.load_data(
            subject, [run], path=DATA_ROOT, update_path=False, verbose="ERROR"
        )
        raw = mne.io.read_raw_edf(filenames[0], preload=True, verbose="ERROR")
        mne.datasets.eegbci.standardize(raw)
        raw.pick(config.channels)
        raw.reorder_channels(config.channels)
        fs, channels = raw.info["sfreq"], raw.ch_names
        events, _ = mne.events_from_annotations(raw, event_id={"T1": 1, "T2": 2}, verbose="ERROR")
        epochs = mne.Epochs(
            raw,
            events,
            event_id={"left_hand": 1, "right_hand": 2},
            tmin=config.tmin,
            tmax=config.tmax - 1 / fs,
            baseline=None,
            preload=True,
            reject_by_annotation=True,
            verbose="ERROR",
        )
        xs.append(epochs.get_data(copy=True) * 1e6)
        ys.append(epochs.events[:, 2] - 1)
        rows.extend(
            {
                "subject": subject,
                "session": "0",
                "run": str(run),
                "trial_id": f"PhysionetMI:{subject}:{run}:{int(event[0])}",
                "split": "test" if run == 12 else "train",
            }
            for event in epochs.events
        )
    return EpochDataset(np.concatenate(xs), np.concatenate(ys), pd.DataFrame(rows), channels, fs)


def _moabb(name: str, subject: int, config: BenchmarkConfig) -> EpochDataset:
    from moabb.datasets import BNCI2014_001, PhysionetMI
    from moabb.paradigms import LeftRightImagery

    registry = {
        "PhysionetMI": lambda: PhysionetMI(imagined=True, executed=False),
        "BNCI2014_001": BNCI2014_001,
    }
    dataset = registry[name]()
    # No offline filter here: perturbation is applied to raw epochs, then our explicit filter.
    paradigm = LeftRightImagery(
        fmin=None, fmax=None, tmin=config.tmin, tmax=config.tmax, channels=config.channels
    )
    epochs, labels, metadata = paradigm.get_data(dataset, subjects=[subject], return_epochs=True)
    epochs.reorder_channels(config.channels)
    x = epochs.get_data(copy=True) * 1e6
    expected = round((config.tmax - config.tmin) * epochs.info["sfreq"])
    x = x[:, :, :expected]
    y = np.asarray([0 if label == "left_hand" else 1 for label in labels])
    metadata = metadata.copy()
    sessions = sorted(metadata.session.unique())
    if len(sessions) < 2:
        raise ValueError("cross-session dataset requires two sessions")
    metadata["split"] = np.where(metadata.session == sessions[0], "train", "test")
    metadata["trial_id"] = [
        f"{name}:{subject}:{row.session}:{row.run}:{i}" for i, row in metadata.iterrows()
    ]
    return EpochDataset(x, y, metadata, config.channels, epochs.info["sfreq"])


def load_subject(
    name: str, subject: int, config: BenchmarkConfig, force: bool = False
) -> EpochDataset:
    if name not in DATASETS:
        raise ValueError("unsupported dataset")
    settings = {
        "adapter": 1,
        "dataset": name,
        "subject": subject,
        "channels": config.channels,
        "tmin": config.tmin,
        "tmax": config.tmax,
        "mne_version": mne.__version__,
    }
    key = hashlib.sha256(json.dumps(settings, sort_keys=True).encode()).hexdigest()[:20]
    directory = DATA_ROOT / "epochs" / key
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "epochs.npz"
    if path.exists() and not force:
        with np.load(path, allow_pickle=False) as data:
            return EpochDataset(
                data["x"],
                data["y"],
                pd.read_json(directory / "metadata.json"),
                data["channels"].tolist(),
                float(data["fs"]),
            )
    result = _physionet(subject, config) if name == "PhysionetMI" else _moabb(name, subject, config)
    np.savez_compressed(path, x=result.x, y=result.y, channels=result.channels, fs=result.fs)
    result.metadata.to_json(directory / "metadata.json")
    (directory / "config.json").write_text(json.dumps(settings, indent=2))
    return result


def dataset_info(name: str) -> dict:
    if name not in DATASETS:
        raise ValueError("unknown dataset")
    from moabb.datasets import BNCI2014_001, PhysionetMI

    dataset = (
        PhysionetMI(imagined=True, executed=False) if name == "PhysionetMI" else BNCI2014_001()
    )
    return {
        "name": name,
        **DATASETS[name],
        "subjects_available": dataset.subject_list,
        "sessions_available": dataset.n_sessions,
        "events": dataset.event_id,
        "data_root": str(DATA_ROOT),
    }
