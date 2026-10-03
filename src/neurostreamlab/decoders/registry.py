from pathlib import Path

from neurostreamlab.decoders.base import Decoder, read_manifest
from neurostreamlab.decoders.classical import ClassicalDecoder

REGISTRY = {
    "bandpower_logreg": "Log bandpower + logistic regression",
    "csp_lda": "CSP + shrinkage LDA",
    "eegnet": "EEGNet (Braindecode, CPU)",
}


def create_decoder(name: str, metadata: dict, **kwargs) -> Decoder:
    if name not in REGISTRY:
        raise ValueError(f"unknown decoder {name}")
    if name == "eegnet":
        from neurostreamlab.decoders.eegnet import EEGNetDecoder

        return EEGNetDecoder(metadata, **kwargs)
    return ClassicalDecoder(name, metadata)


def load_decoder(directory: Path) -> Decoder:
    metadata = read_manifest(directory)
    if metadata["decoder"] == "eegnet":
        from neurostreamlab.decoders.eegnet import EEGNetDecoder

        return EEGNetDecoder.load(directory)
    return ClassicalDecoder.load(directory)
