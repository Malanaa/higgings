import time

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    brier_score_loss,
    confusion_matrix,
    f1_score,
    roc_auc_score,
)

from neurostreamlab.decoders.base import Decoder


def classification_metrics(y: np.ndarray, p: np.ndarray) -> dict:
    prediction = p.argmax(axis=1)
    return {
        "accuracy": float(accuracy_score(y, prediction)),
        "balanced_accuracy": float(balanced_accuracy_score(y, prediction)),
        "roc_auc": float(roc_auc_score(y, p[:, 1])),
        "f1": float(f1_score(y, prediction, zero_division=0)),
        "brier": float(brier_score_loss(y, p[:, 1])),
        "confusion": confusion_matrix(y, prediction, labels=[0, 1]).tolist(),
    }


def latency(model: Decoder, x: np.ndarray, calls: int) -> dict:
    for _ in range(10):
        model.predict_proba(x[:1])
    durations = []
    for _ in range(calls):
        start = time.perf_counter_ns()
        model.predict_proba(x[:1])
        durations.append((time.perf_counter_ns() - start) / 1e6)
    return {
        "latency_ms": durations,
        "latency_median_ms": float(np.median(durations)),
        "latency_mean_ms": float(np.mean(durations)),
        "latency_p95_ms": float(np.percentile(durations, 95)),
        "throughput_windows_s": float(1000 / np.mean(durations)),
        "batch_size": 1,
        "warmup_calls": 10,
        "calls": calls,
        "window_shape": list(x.shape[1:]),
    }


def bootstrap_mean(values: np.ndarray, samples: int = 2000, seed: int = 42) -> dict:
    values = np.asarray(values)
    if values.size == 0:
        raise ValueError("empty bootstrap")
    rng = np.random.default_rng(seed)
    distribution = rng.choice(values, (samples, len(values)), replace=True).mean(axis=1)
    return {
        "mean": float(values.mean()),
        "ci_low": float(np.percentile(distribution, 2.5)),
        "ci_high": float(np.percentile(distribution, 97.5)),
        "n_subjects": len(values),
        "bootstrap_samples": samples,
        "seed": seed,
    }


def audit_split(metadata) -> dict:
    train = metadata[metadata.split == "train"].trial_id.tolist()
    test = metadata[metadata.split == "test"].trial_id.tolist()
    if (
        not train
        or not test
        or set(train) & set(test)
        or len(set(train + test)) != len(train + test)
    ):
        raise ValueError("invalid or overlapping trial split")
    return {"train_trial_ids": train, "test_trial_ids": test, "disjoint": True}
