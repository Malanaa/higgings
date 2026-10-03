"""Record design hash before executing final experiments."""

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

path = Path("configs/benchmarks/paper_v1.yaml")
target = Path("results/manifests/experiment_freeze.json")
record = {
    "config": str(path),
    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
    "timestamp": datetime.now(UTC).isoformat(),
    "reason": "Laptop-sized exploratory systems evaluation. Cohort selected before final results. Smoke used subject 1.",
}
if target.exists() and json.loads(target.read_text())["sha256"] != record["sha256"]:
    raise SystemExit("Frozen design differs. Increment experiment version and document the reason.")
if not target.exists():
    target.write_text(json.dumps(record, indent=2))
print(record["sha256"])
