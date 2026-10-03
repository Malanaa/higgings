"""Fail closed on missing, stale, corrupted or inconsistent publication results."""

import hashlib
import json
from pathlib import Path

import numpy as np

from neurostreamlab.evaluation.metrics import bootstrap_mean, classification_metrics
from neurostreamlab.evaluation.publication import streaming_text, table_text


def verify(root: Path = Path("results")) -> None:
    manifest = json.loads((root / "manifests/paper_results.json").read_text())
    config = Path(manifest["config_path"])
    if hashlib.sha256(config.read_bytes()).hexdigest() != manifest["config_hash"]:
        raise ValueError("paper config hash differs")
    freeze = json.loads((root / "manifests/experiment_freeze.json").read_text())
    if freeze["sha256"] != manifest["config_hash"]:
        raise ValueError("paper design differs from frozen config")
    for path, expected in manifest["artifacts"].items():
        actual = hashlib.sha256(Path(path).read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"artifact hash mismatch: {path}")
    directory = Path(manifest["run_directory"])
    run = json.loads((directory / "run.json").read_text())
    if not run["completed"]:
        raise ValueError("incomplete experiment")
    for subject in run["subjects"]:
        if set(subject["train_trial_ids"]) & set(subject["test_trial_ids"]):
            raise ValueError("training/test overlap")
    rows = json.loads((directory / "metrics.json").read_text())
    for row in rows:
        with np.load(directory / row["predictions_file"], allow_pickle=False) as predictions:
            m = classification_metrics(predictions["labels"], predictions["probabilities"])
        for key, value in m.items():
            if key == "confusion":
                if value != row[key]:
                    raise ValueError("confusion matrix inconsistency")
            elif not np.isclose(value, row[key], atol=1e-12):
                raise ValueError(f"metric inconsistency: {key}")
        if any(t < 0 for t in row["latency_ms"]):
            raise ValueError("negative latency")
        meta = json.loads(
            (
                directory / f"model_{row['dataset']}_{row['subject']}_{row['decoder']}.json"
            ).read_text()
        )
        if meta["sha256"] != row["model_hash"]:
            raise ValueError("model provenance mismatch")
    aggregated = json.loads((root / "aggregated/metrics.json").read_text())
    for entry in aggregated:
        group = [
            r
            for r in rows
            if all(r[k] == entry[k] for k in ("dataset", "decoder", "condition", "adaptation"))
        ]
        group.sort(key=lambda r: r["subject"])
        derived = bootstrap_mean(
            np.array([r["balanced_accuracy"] for r in group]),
            run["config"]["bootstrap_samples"],
            run["config"]["seed"],
        )
        for key in ("mean", "ci_low", "ci_high", "n_subjects"):
            if not np.isclose(entry[key], derived[key], atol=1e-12):
                raise ValueError(f"aggregated metric inconsistency: {key}")
    statistics = json.loads((root / "aggregated/statistics.json").read_text())
    for entry in statistics:
        adapted = sorted(
            [
                r
                for r in rows
                if all(r[k] == entry[k] for k in ("dataset", "decoder", "condition"))
                and r["adaptation"] == "unlabeled_rms"
            ],
            key=lambda r: r["subject"],
        )
        baseline = sorted(
            [
                r
                for r in rows
                if all(r[k] == entry[k] for k in ("dataset", "decoder", "condition"))
                and r["adaptation"] == "none"
            ],
            key=lambda r: r["subject"],
        )
        differences = np.array(
            [
                a["balanced_accuracy"] - b["balanced_accuracy"]
                for a, b in zip(adapted, baseline, strict=True)
            ]
        )
        derived = bootstrap_mean(
            differences, run["config"]["bootstrap_samples"], run["config"]["seed"]
        )
        if any(
            not np.isclose(entry[key], derived[key], atol=1e-12)
            for key in ("mean", "ci_low", "ci_high")
        ):
            raise ValueError("paired bootstrap inconsistency")
    profile = json.loads((root / "raw/streaming_profile.json").read_text())
    for mode, data in profile["modes"].items():
        if not np.isclose(data["median_ms"], np.median(data["raw_pipeline_ms"])) or not np.isclose(
            data["p95_ms"], np.percentile(data["raw_pipeline_ms"], 95)
        ):
            raise ValueError(f"streaming timing inconsistency: {mode}")
    for filename, expected in {**table_text(aggregated, run), **streaming_text(profile)}.items():
        if Path("paper/generated", filename).read_text() != expected:
            raise ValueError(f"table/macros differ from results: {filename}")
    print(
        f"Provenance verified: {len(rows)} subject/condition results, {len(manifest['artifacts'])} artifacts"
    )


if __name__ == "__main__":
    verify()
