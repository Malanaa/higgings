from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from neurostreamlab.config import PerturbationConfig


class HealthResponse(BaseModel):
    status: str
    version: str


class ControlRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    action: Literal[
        "pause",
        "resume",
        "stop",
        "seek",
        "speed",
        "synthetic",
        "replay",
        "record",
        "stop_recording",
    ]
    value: float | None = None


class PerturbationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    configurations: list[PerturbationConfig] = Field(max_length=12)


class StreamMessage(BaseModel):
    schema_version: Literal[1] = 1
    type: Literal["frame", "warning", "source_status"]
    session_id: str
    payload: dict
