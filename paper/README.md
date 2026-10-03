# Manuscript and reproduction map

**NeuroStreamLab: Hardware-Free Real-Time BCI Development and EEG Replay Robustness**

Syed Abdullah Imam, University of North Texas. No invented email or DOI.

| Paper component | Configuration or source | Command | Output |
|---|---|---|---|
| Cohort and clean results | configs/benchmarks/paper_v1.yaml | neurostreamlab benchmark run configs/benchmarks/paper_v1.yaml | results/raw/<run ID>/run.json and metrics.json |
| Robustness and RMS reference | same frozen YAML, conditions/adaptation | same benchmark command | probabilities/labels NPZ per subject/model/condition |
| Subject bootstrap and paired effects | bootstrap_samples/seed in frozen YAML | neurostreamlab benchmark aggregate | results/aggregated/metrics.json and statistics.json |
| Runtime profile | scripts/profile_streaming.py | neurostreamlab replay --prepare && python scripts/profile_streaming.py | results/raw/streaming_profile.json |
| Tables, macros and figures | completed result artifacts | neurostreamlab figures generate | paper/generated and paper/figures |
| Source and PDF validation | generated result manifest | make paper | paper/main.pdf |
| Independent submission source | main.tex, refs.bib, macros, figures, tables | make arxiv | paper/arxiv_bundle and paper/neurostreamlab-arxiv.tar.gz |

Run `make reproduce-paper` from the root after `./scripts/bootstrap.sh`. It downloads only the specified public subset, runs all three CPU decoders, profiles the source-to-frame worker, generates publication inputs, verifies provenance, compiles, scans punctuation and compiles the independent bundle. The plain `python` commands in the table use the activated .venv, or invoke `.venv/bin/python` explicitly.

`make paper` builds from committed measured results without EEG downloads. It fails on absent result artifacts, hash or table inconsistency, missing references, overfull boxes, or prohibited punctuation. `make paper-lint` rejects semicolons and Unicode em dashes in contributing TeX sources. The complete PDF scan also checks bibliography output. Poppler is used when present, with pypdf as the local extraction fallback and PyMuPDF for rendered page inspection.

The arXiv directory contains only submission sources and required generated assets, with a BBL retained for compatibility. Its verified compiled PDF is stored separately as paper/arxiv_verified.pdf. No arXiv submission was performed. Read docs/SCIENTIFIC_METHOD.md and docs/KNOWN_LIMITATIONS.md before interpreting exploratory results.
