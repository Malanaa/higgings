from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError

from neurostreamlab.adaptation.rms import RMSAlignment
from neurostreamlab.config import FilterConfig, PerturbationConfig, load_config
from neurostreamlab.decoders.base import validate_metadata
from neurostreamlab.decoders.registry import create_decoder, load_decoder
from neurostreamlab.evaluation.metrics import (
    audit_split,
    bootstrap_mean,
    classification_metrics,
    latency,
)
from neurostreamlab.perturbations.engine import PerturbationEngine
from neurostreamlab.preprocessing.pipeline import CausalFilter, preprocess_epochs, spectrum
from neurostreamlab.sources.base import SignalChunk


def test_configuration():
    with pytest.raises(ValidationError):
        PerturbationConfig(name="gaussian_noise", intensity=float("inf"))
    config = load_config("configs/benchmarks/smoke.yaml")
    assert config.datasets["PhysionetMI"] == [1]
    with pytest.raises(ValidationError):
        FilterConfig(low=40, high=20)
    with pytest.raises(ValidationError):
        PerturbationConfig(name="sample_loss", intensity=2)
    with pytest.raises(ValidationError):
        PerturbationConfig(name="unknown")


def test_bandpass_attenuation_and_chunk_equivalence():
    fs = 160
    t = np.arange(3200) / fs
    x = np.array([np.sin(2 * np.pi * 12 * t) + np.sin(2 * np.pi * 60 * t)])
    filtered = preprocess_epochs(x, fs, FilterConfig())
    fft = abs(np.fft.rfft(filtered[:, 320:-320]))[0]
    f = np.fft.rfftfreq(filtered[:, 320:-320].shape[1], 1 / fs)
    assert fft[np.argmin(abs(f - 60))] < 0.01 * fft[np.argmin(abs(f - 12))]
    a, b = CausalFilter(1, fs, FilterConfig()), CausalFilter(1, fs, FilterConfig())
    full = a.transform(x)
    chunks = np.concatenate([b.transform(c) for c in np.array_split(x, 20, axis=1)], axis=1)
    assert np.allclose(full, chunks)
    with pytest.raises(ValueError):
        preprocess_epochs(x, 40, FilterConfig())
    freq, psd, bands = spectrum(x, fs)
    assert len(freq) == len(psd) and all(v >= 0 for v in bands.values())


@pytest.mark.parametrize(
    "name,intensity",
    [
        ("gaussian_noise", 1),
        ("amplitude", 2),
        ("baseline_drift", 2),
        ("channel_dropout", 1),
        ("random_dropout", 1),
        ("line_noise", 1),
        ("channel_noise", 1),
        ("timing_jitter", 0.2),
        ("sample_loss", 0.1),
        ("interruption", 0.2),
    ],
)
def test_perturbations_deterministic(name, intensity):
    c = PerturbationConfig(
        name=name,
        intensity=intensity,
        seed=12,
        channels=[0],
        frequency=0.2 if name == "baseline_drift" else 50,
    )
    x = np.ones((3, 480))
    a, b = PerturbationEngine([c], 160, np.ones(3)), PerturbationEngine([c], 160, np.ones(3))
    assert np.array_equal(a.transform(x), b.transform(x))
    assert np.array_equal(x, np.ones_like(x))


def test_dropout_and_noise_scale():
    x = np.zeros((3, 100000))
    p = PerturbationEngine(
        [PerturbationConfig(name="gaussian_noise", intensity=2)], 160, np.array([1, 2, 3])
    )
    assert np.allclose(p.transform(x).std(axis=1), [2, 4, 6], rtol=0.02)
    p = PerturbationEngine(
        [PerturbationConfig(name="channel_dropout", channels=[0, 2])], 160, np.ones(3)
    )
    y = p.transform(np.ones((3, 10)))
    assert np.array_equal(y[:, 0], [0, 1, 0])


def test_perturbation_schedule_and_transport():
    p = PerturbationEngine(
        [PerturbationConfig(name="amplitude", intensity=2, start=1, end=2)], 10, np.ones(3)
    )
    x = np.ones((3, 30))
    y = p.transform(x)
    assert np.all(y[:, :10] == 1) and np.all(y[:, 10:20] == 2) and np.all(y[:, 20:] == 1)
    p = PerturbationEngine([PerturbationConfig(name="sample_loss", intensity=0.5)], 10, np.ones(3))
    c = p.transform_chunk(SignalChunk(x, np.arange(30) / 10, 0))
    assert 0 < c.data.shape[1] < 30 and np.all(np.diff(c.timestamps) > 0)


def test_unlabeled_rms_alignment():
    t = np.arange(100) / 100
    x = np.tile(np.sin(2 * np.pi * 10 * t), (3, 1))
    adaptation = RMSAlignment(np.std(x, axis=1))
    assert np.allclose(adaptation.transform(2 * x), x)
    assert adaptation.count == 100


@pytest.mark.parametrize("name", ["bandpower_logreg", "csp_lda", "eegnet"])
def test_decoder_training_safe_serialization_and_latency(name, classification_fixture, tmp_path):
    x, y = classification_fixture
    metadata = {
        "channels": ["C3", "Cz", "C4"],
        "fs": 160,
        "n_times": 480,
        "seed": 42,
        "classes": ["left_hand", "right_hand"],
    }
    model = create_decoder(
        name, metadata, **({"epochs": 2, "patience": 2} if name == "eegnet" else {})
    )
    model.fit(x[:40], y[:40])
    p = model.predict_proba(x[40:])
    assert p.shape == (20, 2) and np.allclose(p.sum(axis=1), 1)
    if name != "eegnet":
        assert (p.argmax(axis=1) == y[40:]).mean() > 0.9
    model.save(tmp_path)
    loaded = load_decoder(tmp_path)
    assert np.allclose(loaded.predict_proba(x[40:]), p, atol=1e-7)
    with pytest.raises(ValueError):
        model.predict_proba(x[:, :2])
    with pytest.raises(ValueError):
        validate_metadata(model.metadata, ["C4", "Cz", "C3"], 160)
    assert latency(model, x, 10)["latency_median_ms"] >= 0
    manifest = Path(tmp_path / "manifest.json")
    assert "sha256" in manifest.read_text()
    weights = next(p for p in tmp_path.iterdir() if p.name.startswith("weights"))
    weights.write_bytes(weights.read_bytes() + b"corrupt")
    with pytest.raises(ValueError, match="checksum"):
        load_decoder(tmp_path)


def test_split_audit_and_statistics():
    metadata = pd.DataFrame({"split": ["train", "test"], "trial_id": ["a", "b"]})
    assert audit_split(metadata)["disjoint"]
    metadata.loc[1, "trial_id"] = "a"
    with pytest.raises(ValueError):
        audit_split(metadata)
    a = bootstrap_mean(np.array([0.5, 0.7, 0.9]), 1000, 42)
    assert a == bootstrap_mean(np.array([0.5, 0.7, 0.9]), 1000, 42)
    assert a["ci_low"] <= a["mean"] <= a["ci_high"]
    m = classification_metrics(np.array([0, 1]), np.array([[0.8, 0.2], [0.1, 0.9]]))
    assert m["accuracy"] == m["balanced_accuracy"] == m["roc_auc"] == 1
