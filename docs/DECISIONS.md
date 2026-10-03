# Decisions

## 2026-10-02: initial design
- Name: NeuroStreamLab. Exact-name searches on the web, GitHub, PyPI and npm returned no occupied scientific or developer project. This is a best-effort collision check, not a trademark clearance. Package registries will also be queried directly. Branding is centralized in package metadata.
- Python 3.12: available locally, with scientific wheels, instead of the host default 3.14.
- Local FastAPI + versioned JSON WebSocket protocol. Acquisition and inference run outside browser rendering.
- React/TypeScript/Vite, Canvas traces, Three.js control scene. No paid services or CUDA.
- MIT software license. Dataset rights remain separate. Raw EEG and model artifacts are excluded from Git.
- Offline evaluation uses trial-local zero-phase filters. Replay uses the exact same epoch preprocessing for trial-end decoding. Continuous live processing uses stateful causal filters and is not assigned offline accuracy claims.
- Primary protocol: Physionet imagined left/right hands, held-out complete runs, fixed seed. Multi-session BNCI adapter for train-session/test-session evaluation.
- Statistical unit is subject, with paired subject bootstrap intervals. Small cohorts are explicitly exploratory, no formal significance claims.
- Adaptation: unlabeled per-channel RMS alignment to training RMS, causal expanding statistics at test trial boundaries. No test labels. No promise of improvement.

## Experiment freeze
The PhysioNet and BNCI smoke runs completed. Final scope is five PhysioNet subjects (1-5), three BNCI subjects (1-3), three decoders, nine clean/shift conditions, and unlabeled RMS alignment for every shifted condition. The cohort is chosen for laptop feasibility, not model performance. EEGNet uses at most 30 epochs and inner-training validation early stopping. Small cohort results are exploratory. Three common central electrodes make the cross-dataset implementation test explicit and limit accuracy claims. Noise magnitudes are multiples of training-only broadband centered channel RMS. The filters are applied after perturbation. Dropout targets C3 and then C3/C4, not an optimized electrode search. Drift is 0.2 Hz. No rest classification or clinical inference.

PyPI and npm both returned HTTP 404 for neurostreamlab on 2026-10-02. Searches found no exact-name conflict. Final brand is NeuroStreamLab.

## Validation fixes before release
The initial manuscript compiled after adding xcolor, and PDF checks use a pypdf fallback when Poppler is absent. PyMuPDF provides local rendered-page QA. UI pause state now updates immediately and synthetic mode shows no fabricated probability output. The scalp electrode panel uses standard MNE label coordinates with no individualized-location or interpolation claims.

The final reproduction enforces native scientific thread pools at one thread and records threadpool metadata. The first development run used one PyTorch thread but did not explicitly constrain native classical-library pools, so its timings are superseded by the final reproduction. This correction does not change subjects, splits, signal conditions or algorithm choices.

Linux uv sources explicitly select official CPU PyTorch and torchaudio wheels. The hardware permission gate also covers network/streaming board IDs, not just positive physical board IDs. These packaging and access checks do not change scientific evaluation design. Git commits use the supplied author name with an explicitly empty email, so no contact information is invented.

Trace rendering now uses source timestamps rather than sample-array position. Timing gaps are drawn as gaps, seeks reset history, and state-only changes do not append duplicate samples. Canvas FPS is measured locally, with the target cadence separately labeled. Nonfinite config and metadata values are rejected before starting a stream.

## GitHub Pages documentation

Publish existing Markdown with MkDocs Material on GitHub Pages. Staging copies the existing guides, screenshots and committed paper PDF without duplicating source documents. Pull requests build in strict mode. Master updates deploy through the github-pages environment. The static site documents the locally run console and does not run its backend.

## Preprint preparation and discoverability

Add a dedicated paper landing page with citation metadata and an explicit preprint status. Disclose Codex assistance in the manuscript and landing page. engrXiv currently prohibits verbatim AI-generated paragraphs, so this AI-drafted version should not be submitted there. External submission requires the author's scientific review and account access. No acceptance, DOI, or Scholar indexing is assumed.
