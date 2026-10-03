import hashlib
import importlib.metadata
import json
import platform
import random
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd
from threadpoolctl import threadpool_info, threadpool_limits

from neurostreamlab.adaptation.rms import RMSAlignment
from neurostreamlab.config import load_config
from neurostreamlab.datasets.adapter import load_subject
from neurostreamlab.decoders.registry import create_decoder
from neurostreamlab.evaluation.metrics import (
    audit_split,
    bootstrap_mean,
    classification_metrics,
    latency,
)
from neurostreamlab.perturbations.engine import PerturbationEngine
from neurostreamlab.preprocessing.pipeline import preprocess_epochs


def git_commit() -> str:
    result = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else "uncommitted"


def software_metadata() -> dict:
    return {
        "timestamp": datetime.now(UTC).isoformat(),
        "git_commit": git_commit(),
        "python": sys.version,
        "os": platform.platform(),
        "architecture": platform.machine(),
        "processor": platform.processor(),
        "packages": {
            name: importlib.metadata.version(name)
            for name in (
                "numpy",
                "scipy",
                "pandas",
                "mne",
                "moabb",
                "brainflow",
                "scikit-learn",
                "torch",
                "braindecode",
            )
        },
        "cpu_threads": 1,
        "accelerator": "none",
        "native_threadpools": threadpool_info(),
    }


@threadpool_limits.wrap(limits=1)
def run_benchmark(config_path: str, force: bool = False) -> Path:
    config = load_config(config_path)
    random.seed(config.seed)
    np.random.seed(config.seed)
    code_hash = hashlib.sha256(
        b"".join(p.read_bytes() for p in sorted(Path("src/neurostreamlab").rglob("*.py")))
    ).hexdigest()
    config_hash = hashlib.sha256(Path(config_path).read_bytes()).hexdigest()
    run_id = hashlib.sha256((config_hash + code_hash).encode()).hexdigest()[:16]
    output = Path(config.output)
    directory = output / "raw" / run_id
    if (directory / "run.json").exists() and not force:
        print(f"Compatible completed run: {directory}")
        return directory
    directory.mkdir(parents=True, exist_ok=True)
    metadata = {
        **software_metadata(),
        "run_id": run_id,
        "config_hash": config_hash,
        "code_hash": code_hash,
        "config": config.model_dump(),
        "evaluation": "complete held-out run for PhysionetMI, complete held-out session for BNCI2014_001",
        "preprocessing": "trial-local zero-phase Butterworth before decoding",
        "subjects": [],
    }
    rows = []
    for dataset, subjects in config.datasets.items():
        for subject in subjects:
            print(f"Loading {dataset}, subject {subject}", flush=True)
            data = load_subject(dataset, subject, config)
            split = audit_split(data.metadata)
            train = np.flatnonzero(data.metadata.split == "train")
            test = np.flatnonzero(data.metadata.split == "test")
            rms_raw = np.sqrt(
                np.square(data.x[train] - data.x[train].mean(axis=-1, keepdims=True)).mean(
                    axis=(0, 2)
                )
            )
            training = preprocess_epochs(data.x[train], data.fs, config.preprocessing)
            rms_filtered = np.sqrt(np.square(training).mean(axis=(0, 2)))
            subject_meta = {
                "dataset": dataset,
                "subject": subject,
                "fs": data.fs,
                "channels": data.channels,
                "sessions": sorted(data.metadata.session.astype(str).unique().tolist()),
                "n_train": len(train),
                "n_test": len(test),
                **split,
            }
            metadata["subjects"].append(subject_meta)
            for decoder in config.decoders:
                print(f"Training {decoder}", flush=True)
                model_meta = {
                    "channels": data.channels,
                    "fs": data.fs,
                    "n_times": data.x.shape[-1],
                    "classes": ["left_hand", "right_hand"],
                    "seed": config.seed,
                    "dataset": dataset,
                    "subjects": [subject],
                    "preprocessing": config.preprocessing.model_dump(),
                    "preprocessing_id": "trial_zero_phase_v1",
                    "git_commit": metadata["git_commit"],
                    "training_run": run_id,
                    "training_trial_ids": split["train_trial_ids"],
                }
                kwargs = (
                    {"epochs": config.eegnet_epochs, "patience": config.eegnet_patience}
                    if decoder == "eegnet"
                    else {}
                )
                model = create_decoder(decoder, model_meta, **kwargs)
                start = time.perf_counter()
                model.fit(training, data.y[train])
                duration = time.perf_counter() - start
                model.metadata["training_seconds"] = duration
                model_dir = Path("models") / run_id / dataset / str(subject) / decoder
                model.save(model_dir)
                latency_metrics = latency(model, training, config.latency_calls)
                for condition, perturbations in config.conditions.items():
                    engine = PerturbationEngine(perturbations, data.fs, rms_raw)
                    shifted = np.stack(
                        [
                            engine.transform(trial, i * (config.tmax - config.tmin))
                            for i, trial in enumerate(data.x[test])
                        ]
                    )
                    processed = preprocess_epochs(shifted, data.fs, config.preprocessing)
                    for adaptation in (
                        ["none", "unlabeled_rms"]
                        if config.adaptation and condition != "clean"
                        else ["none"]
                    ):
                        alignment = RMSAlignment(rms_filtered)
                        probabilities, overhead = [], []
                        for trial in processed:
                            start = time.perf_counter_ns()
                            x = alignment.transform(trial) if adaptation != "none" else trial
                            overhead.append((time.perf_counter_ns() - start) / 1e6)
                            probabilities.append(model.predict_proba(x)[0])
                        p = np.asarray(probabilities)
                        metrics = classification_metrics(data.y[test], p)
                        predictions_file = (
                            f"{dataset}_{subject}_{decoder}_{condition}_{adaptation}.npz"
                        )
                        np.savez_compressed(
                            directory / predictions_file,
                            probabilities=p,
                            labels=data.y[test],
                            trial_ids=data.metadata.iloc[test].trial_id.to_numpy(dtype=str),
                        )
                        row = {
                            "dataset": dataset,
                            "subject": subject,
                            "decoder": decoder,
                            "condition": condition,
                            "adaptation": adaptation,
                            "n_train": len(train),
                            "n_test": len(test),
                            "training_seconds": duration,
                            "adaptation_mean_ms": float(np.mean(overhead)),
                            "predictions_file": predictions_file,
                            "model_manifest": str(model_dir / "manifest.json"),
                            "model_hash": json.loads((model_dir / "manifest.json").read_text())[
                                "sha256"
                            ],
                            **metrics,
                            **latency_metrics,
                        }
                        rows.append(row)
                clean_row = next(
                    r
                    for r in rows
                    if r["dataset"] == dataset
                    and r["subject"] == subject
                    and r["decoder"] == decoder
                    and r["condition"] == "clean"
                    and r["adaptation"] == "none"
                )
                model_manifest = json.loads((model_dir / "manifest.json").read_text())
                model_manifest["evaluation_summary"] = {
                    key: clean_row[key]
                    for key in ("accuracy", "balanced_accuracy", "roc_auc", "f1", "brier", "n_test")
                }
                (model_dir / "manifest.json").write_text(json.dumps(model_manifest, indent=2))
                (directory / "metrics.json").write_text(json.dumps(rows, indent=2))
    metadata["completed"] = True
    (directory / "run.json").write_text(json.dumps(metadata, indent=2))
    output.joinpath("manifests").mkdir(parents=True, exist_ok=True)
    (output / "manifests" / "latest.json").write_text(
        json.dumps({"run_directory": str(directory), "config_path": config_path}, indent=2)
    )
    print(f"Completed {directory}", flush=True)
    return directory


def aggregate(output: str = "results") -> Path:
    root = Path(output)
    latest = json.loads((root / "manifests/latest.json").read_text())
    directory = Path(latest["run_directory"])
    run = json.loads((directory / "run.json").read_text())
    frame = pd.DataFrame(json.loads((directory / "metrics.json").read_text()))
    result = []
    for keys, group in frame.groupby(["dataset", "decoder", "condition", "adaptation"], sort=True):
        entry = dict(zip(["dataset", "decoder", "condition", "adaptation"], keys, strict=True))
        entry.update(
            bootstrap_mean(
                group.balanced_accuracy.to_numpy(),
                run["config"]["bootstrap_samples"],
                run["config"]["seed"],
            )
        )
        entry["latency_median_ms"] = float(group.latency_median_ms.median())
        entry["latency_p95_ms"] = float(group.latency_p95_ms.median())
        entry["adaptation_mean_ms"] = float(group.adaptation_mean_ms.mean())
        result.append(entry)
    statistics = []
    # Paired bootstrap effects, no small-cohort significance testing.
    for (dataset, decoder, condition), group in frame[frame.adaptation == "unlabeled_rms"].groupby(
        ["dataset", "decoder", "condition"]
    ):
        base = frame[
            (frame.dataset == dataset)
            & (frame.decoder == decoder)
            & (frame.condition == condition)
            & (frame.adaptation == "none")
        ]
        merged = group.merge(base, on="subject", suffixes=("_adapt", "_base"))
        diff = merged.balanced_accuracy_adapt - merged.balanced_accuracy_base
        statistics.append(
            {
                "dataset": dataset,
                "decoder": decoder,
                "condition": condition,
                "contrast": "unlabeled RMS minus no adaptation",
                **bootstrap_mean(
                    diff.to_numpy(), run["config"]["bootstrap_samples"], run["config"]["seed"]
                ),
            }
        )
    path = root / "aggregated"
    path.mkdir(parents=True, exist_ok=True)
    (path / "metrics.json").write_text(json.dumps(result, indent=2))
    (path / "statistics.json").write_text(json.dumps(statistics, indent=2))
    frame.drop(columns=["latency_ms", "confusion"]).to_csv(path / "subjects.csv", index=False)
    return path
