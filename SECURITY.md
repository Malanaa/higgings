# Security and privacy

The default server binds to 127.0.0.1, allows only local development browser origins, has no telemetry, and makes no external EEG uploads. Public dataset downloads are the only required research network activity. Do not expose the unauthenticated research API to other networks. Configuration is typed YAML, not executable code. Models use numeric NPZ or safetensors with SHA-256 manifests, never arbitrary pickle import. Session exports are local JSONL and omit raw EEG by default. Keep sessions and datasets outside Git.

Report vulnerabilities privately through the repository hosting platform if private vulnerability reporting is enabled, otherwise contact the maintainer before disclosing exploit details. The current release has no physical hardware validation and is not a medical device.
