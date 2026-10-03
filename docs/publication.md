# NeuroStreamLab: Hardware-Free Real-Time BCI Development and EEG Replay Robustness

**Syed Abdullah Imam** · University of North Texas

**Preprint · Not peer reviewed** · First publicly posted October 2, 2026

[Download the complete paper (PDF)](paper.pdf)

## Abstract

NeuroStreamLab is an open source local environment for hardware-free brain computer interface software development. It separates acquisition from timestamped processing and supports BrainFlow synthetic streams, recorded EEG replay, and an explicit future hardware adapter. Its browser console exposes signals, decoder probabilities, temporal decisions, controlled perturbations, and runtime telemetry. The exploratory evaluation compares bandpower logistic regression, common spatial patterns with shrinkage linear discriminant analysis, and EEGNet on held-out motor imagery EEG from PhysioNet and cross-session BNCI2014-001. Eight subjects and 507 held-out test trials are included. Controlled shifts cover additive noise, channel loss, amplitude scaling, drift, and a mixed condition. Clean CSP/LDA mean balanced accuracy is 55.9% on PhysioNet and 73.1% on BNCI. Unlabeled RMS alignment gives condition-dependent recovery. All numerical results are linked to stored predictions, manifests, and generated publication artifacts. Synthetic acquisition and replay timing are engineering demonstrations, not evidence of online human control or physical-device latency.

## Materials and status

- [Source code and measured results](https://github.com/Malanaa/higgings)
- [Reproduction instructions](REPRODUCIBILITY.md)
- [Scientific method](SCIENTIFIC_METHOD.md)
- [Limitations](KNOWN_LIMITATIONS.md)

This manuscript is self-hosted. No external preprint-server acceptance, journal publication, DOI, or Google Scholar indexing is claimed.

## AI assistance disclosure

OpenAI Codex generated software, ran the reported computational experiments and automated checks, and drafted manuscript text under the author's instructions. AI assistance also supported literature searches, figures, and publication packaging. These activities are disclosed rather than represented as human-only work. The manuscript requires author review before an external submission. AI systems are not listed as authors.
