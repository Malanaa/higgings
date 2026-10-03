"""Record original public file hashes without redistributing EEG."""

import hashlib
import json
from pathlib import Path

from neurostreamlab.datasets.adapter import DATA_ROOT

files = [*DATA_ROOT.rglob("*.edf"), *DATA_ROOT.joinpath("NEMAR/nm000139/sourcedata").glob("*.mat")]
record = {
    "PhysionetMI": {"source": "https://physionet.org/files/eegmmidb/1.0.0/", "version": "1.0.0"},
    "BNCI2014_001": {
        "source": "MOABB NEMAR nm000139 original sourcedata",
        "version": "v1.0.2",
        "notice": "data/NEMAR/nm000139/sourcedata/sourcedata_provenance.json",
    },
    "files": {
        str(file.relative_to(DATA_ROOT)): {
            "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
            "bytes": file.stat().st_size,
        }
        for file in files
    },
}
target = Path("results/manifests/data_sources.json")
if target.exists():
    previous = json.loads(target.read_text())
    for name, entry in previous["files"].items():
        if name in record["files"] and entry != record["files"][name]:
            raise ValueError(f"public source bytes changed: {name}")
target.write_text(json.dumps(record, indent=2))
print(f"Recorded {len(files)} original EEG file hashes")
