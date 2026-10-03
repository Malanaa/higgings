import copy
from pathlib import Path

import numpy as np
import torch
from braindecode.models import EEGNet
from safetensors.torch import load_file, save_file
from sklearn.model_selection import train_test_split

from neurostreamlab.decoders.base import read_manifest, validate_window, write_manifest


class EEGNetDecoder:
    def __init__(self, metadata: dict, epochs: int = 30, patience: int = 8):
        self.metadata = {**metadata, "decoder": "eegnet", "epochs": epochs, "patience": patience}
        self.seed = metadata.get("seed", 42)
        torch.manual_seed(self.seed)
        torch.set_num_threads(1)
        self.net = EEGNet(
            n_chans=len(metadata["channels"]),
            n_outputs=2,
            n_times=metadata["n_times"],
            sfreq=metadata["fs"],
            F1=8,
            D=2,
            drop_prob=0.25,
        )
        self.metadata["architecture"] = {
            "implementation": "braindecode.models.EEGNet",
            "F1": 8,
            "D": 2,
            "drop_prob": 0.25,
            "device": "cpu",
            "threads": 1,
        }
        self.history: list[dict] = []
        self.fitted = False

    def fit(self, x: np.ndarray, y: np.ndarray) -> None:
        x = validate_window(x, self.metadata)
        train, val = train_test_split(
            np.arange(len(y)), test_size=0.2, stratify=y, random_state=self.seed
        )
        # Scaling learned only on the inner training split.
        self.scale = np.std(x[train], axis=(0, 2)).clip(1e-6)
        tx = torch.tensor(x / self.scale[None, :, None], dtype=torch.float32)
        ty = torch.tensor(y, dtype=torch.long)
        optimizer = torch.optim.Adam(self.net.parameters(), lr=0.001)
        loss_fn = torch.nn.CrossEntropyLoss()
        best, stale = float("inf"), 0
        state = copy.deepcopy(self.net.state_dict())
        generator = torch.Generator().manual_seed(self.seed)
        for epoch in range(self.metadata["epochs"]):
            self.net.train()
            losses = []
            order = torch.tensor(train)[torch.randperm(len(train), generator=generator)]
            for batch in order.split(16):
                optimizer.zero_grad()
                loss = loss_fn(self.net(tx[batch]), ty[batch])
                loss.backward()
                optimizer.step()
                losses.append(float(loss.detach()))
            self.net.eval()
            with torch.no_grad():
                val_loss = float(loss_fn(self.net(tx[val]), ty[val]))
            self.history.append(
                {
                    "epoch": epoch + 1,
                    "train_loss": float(np.mean(losses)),
                    "validation_loss": val_loss,
                }
            )
            if val_loss < best - 1e-5:
                best, stale = val_loss, 0
                state = copy.deepcopy(self.net.state_dict())
                self.metadata["selected_epoch"] = epoch + 1
            else:
                stale += 1
            if stale >= self.metadata["patience"]:
                break
        self.net.load_state_dict(state)
        self.net.eval()
        self.fitted = True
        self.metadata["history"] = self.history
        self.metadata["validation_indices"] = val.tolist()
        self.metadata["inner_training_indices"] = train.tolist()

    def predict_proba(self, x: np.ndarray) -> np.ndarray:
        if not self.fitted:
            raise RuntimeError("decoder is not fitted")
        x = validate_window(x, self.metadata)
        self.net.eval()
        with torch.no_grad():
            return torch.softmax(
                self.net(torch.tensor(x / self.scale[None, :, None], dtype=torch.float32)), dim=1
            ).numpy()

    def save(self, directory: Path) -> None:
        directory.mkdir(parents=True, exist_ok=True)
        weights = {key: value.contiguous() for key, value in self.net.state_dict().items()}
        weights["input_scale"] = torch.tensor(self.scale)
        save_file(weights, str(directory / "weights.safetensors"))
        write_manifest(directory, self.metadata, "weights.safetensors")

    @classmethod
    def load(cls, directory: Path):
        metadata = read_manifest(directory)
        model = cls(metadata, metadata["epochs"], metadata["patience"])
        weights = load_file(str(directory / metadata["weights"]))
        model.scale = weights.pop("input_scale").numpy()
        model.net.load_state_dict(weights)
        model.fitted = True
        model.net.eval()
        return model
