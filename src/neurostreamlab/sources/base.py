from dataclasses import dataclass, field
from typing import Literal, Protocol

import numpy as np
from pydantic import BaseModel, ConfigDict, Field, model_validator


class SourceMetadata(BaseModel):
    model_config = ConfigDict(allow_inf_nan=False)
    identifier: str
    name: str
    source_type: Literal["SYNTHETIC", "RECORDED EEG REPLAY", "LIVE HARDWARE"]
    sampling_frequency: float = Field(gt=0)
    channel_names: list[str]
    channel_types: list[str]
    units: str = "uV"
    board_id: int | None = None
    session: str = "local"
    subject: str | None = None
    dataset: str | None = None
    start_timestamp: float = 0

    @property
    def n_channels(self) -> int:
        return len(self.channel_names)

    @model_validator(mode="after")
    def channel_lengths(self):
        if not self.channel_names or len(self.channel_names) != len(self.channel_types):
            raise ValueError("channel names and types must have equal nonzero length")
        return self


@dataclass
class SignalChunk:
    data: np.ndarray  # channels x samples, microvolts
    timestamps: np.ndarray  # strictly increasing session-relative monotonic seconds
    sequence: int
    events: list[dict] = field(default_factory=list)

    def __post_init__(self):
        if self.data.ndim != 2 or self.timestamps.shape != (self.data.shape[1],):
            raise ValueError("chunk shape mismatch")
        if not np.all(np.isfinite(self.data)) or not np.all(np.isfinite(self.timestamps)):
            raise ValueError("nonfinite chunk")
        if len(self.timestamps) > 1 and np.any(np.diff(self.timestamps) <= 0):
            raise ValueError("timestamps must increase")


class NeuralSignalSource(Protocol):
    metadata: SourceMetadata

    def connect(self) -> None: ...
    def start(self) -> None: ...
    def read(self) -> SignalChunk | None: ...
    def stop(self) -> None: ...
    def close(self) -> None: ...
