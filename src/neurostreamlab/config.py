from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, model_validator


class StrictConfig(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class FilterConfig(StrictConfig):
    low: float = Field(default=8, gt=0)
    high: float = Field(default=30, gt=0)
    order: int = Field(default=4, ge=1, le=10)
    notch: float | None = Field(default=None, gt=0)
    reference: Literal["none", "average"] = "none"
    detrend: bool = True

    @model_validator(mode="after")
    def ordered(self):
        if self.low >= self.high:
            raise ValueError("low must be below high")
        return self


class PerturbationConfig(StrictConfig):
    name: Literal[
        "clean",
        "gaussian_noise",
        "amplitude",
        "baseline_drift",
        "channel_dropout",
        "random_dropout",
        "line_noise",
        "channel_noise",
        "timing_jitter",
        "sample_loss",
        "interruption",
    ] = "clean"
    intensity: float = Field(default=0, ge=0)
    seed: int = 42
    channels: list[int] = Field(default_factory=list)
    frequency: float = Field(default=50, gt=0)
    start: float = Field(default=0, ge=0)
    end: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def validate_range(self):
        if self.end is not None and self.end <= self.start:
            raise ValueError("schedule end must exceed start")
        if any(c < 0 for c in self.channels):
            raise ValueError("channel indices must be nonnegative")
        if self.name in ("sample_loss", "interruption") and self.intensity > 1:
            raise ValueError("fraction must be in [0,1]")
        return self


class BenchmarkConfig(StrictConfig):
    version: str = "v1"
    seed: int = 42
    datasets: dict[str, list[int]]
    decoders: list[Literal["bandpower_logreg", "csp_lda", "eegnet"]]
    channels: list[str] = Field(default_factory=lambda: ["C3", "Cz", "C4"])
    preprocessing: FilterConfig = Field(default_factory=FilterConfig)
    tmin: float = Field(default=0.5, ge=0)
    tmax: float = Field(default=3.5, gt=0)
    conditions: dict[str, list[PerturbationConfig]]
    adaptation: bool = True
    eegnet_epochs: int = Field(default=30, ge=1)
    eegnet_patience: int = Field(default=8, ge=1)
    latency_calls: int = Field(default=100, ge=10)
    bootstrap_samples: int = Field(default=2000, ge=100)
    output: str = "results"

    @model_validator(mode="after")
    def check(self):
        if self.tmax <= self.tmin:
            raise ValueError("tmax must exceed tmin")
        if not self.datasets or not self.decoders or "clean" not in self.conditions:
            raise ValueError("datasets, decoders and a clean condition are required")
        return self


def load_config(path: str | Path) -> BenchmarkConfig:
    return BenchmarkConfig.model_validate(yaml.safe_load(Path(path).read_text()))
