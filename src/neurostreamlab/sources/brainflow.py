import time
from typing import Literal

import numpy as np
from brainflow.board_shim import BoardIds, BoardShim, BrainFlowInputParams

from neurostreamlab.sources.base import SignalChunk, SourceMetadata


class BrainFlowSource:
    """Explicit board acquisition. BrainFlow EEG units are microvolts."""

    def __init__(
        self, board_id: int = -1, parameters: dict | None = None, *, allow_hardware: bool = False
    ):
        if board_id not in (-1, -3) and not allow_hardware:
            raise ValueError("physical boards require explicit allow_hardware=True")
        params = BrainFlowInputParams()
        for key, value in (parameters or {}).items():
            if not hasattr(params, key):
                raise ValueError(f"unknown BrainFlow parameter: {key}")
            setattr(params, key, value)
        master = params.master_board if board_id == BoardIds.PLAYBACK_FILE_BOARD.value else board_id
        self.board = BoardShim(board_id, params)
        self.eeg = BoardShim.get_eeg_channels(master)
        fs = BoardShim.get_sampling_rate(master)
        names = BoardShim.get_eeg_names(master)
        if len(names) != len(self.eeg):
            names = [f"EEG {i + 1}" for i in range(len(self.eeg))]
        kind: Literal["SYNTHETIC", "RECORDED EEG REPLAY", "LIVE HARDWARE"] = (
            "SYNTHETIC"
            if board_id == -1
            else "RECORDED EEG REPLAY"
            if board_id == -3
            else "LIVE HARDWARE"
        )
        self.metadata = SourceMetadata(
            identifier=f"brainflow:{board_id}",
            name=f"BrainFlow board {board_id}",
            source_type=kind,
            sampling_frequency=fs,
            channel_names=names,
            channel_types=["eeg"] * len(names),
            board_id=board_id,
        )
        self.count = 0
        self.sequence = 0
        self.running = False
        self.connected = False

    def connect(self) -> None:
        if not self.connected:
            self.board.prepare_session()
            self.connected = True

    def start(self) -> None:
        if not self.connected:
            raise RuntimeError("connect before start")
        if not self.running:
            self.board.start_stream(45000)
            self.running = True
            self.metadata.start_timestamp = time.time()

    def read(self) -> SignalChunk | None:
        if not self.running:
            return None
        data = self.board.get_board_data()
        if data.shape[1] == 0:
            return None
        n = data.shape[1]
        # Preserve the board's relative acquisition timing, rather than polling timing.
        raw_t = data[
            BoardShim.get_timestamp_channel(
                self.metadata.board_id
                if self.metadata.board_id != -3
                else self.board.get_board_id()
            )
        ]
        if not hasattr(self, "origin"):
            self.origin = raw_t[0]
        times = raw_t - self.origin
        if len(times) > 1 and np.any(np.diff(times) <= 0):
            raise RuntimeError("board returned non-monotonic acquisition timestamps")
        chunk = SignalChunk(data[self.eeg], times, self.sequence)
        self.count += n
        self.sequence += 1
        return chunk

    def stop(self) -> None:
        if self.running:
            self.board.stop_stream()
            self.running = False

    def close(self) -> None:
        self.stop()
        if self.connected:
            self.board.release_session()
            self.connected = False


class PlaybackSource(BrainFlowSource):
    def __init__(self, file: str, master_board: int = -1):
        super().__init__(-3, {"file": file, "master_board": master_board})
