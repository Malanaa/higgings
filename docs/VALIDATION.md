# Executed validation

Local macOS arm64, Python 3.12.14 and Node 24.21.0. This file records executed checks, not remote CI claims.

- The documented bootstrap script completed successfully. The replay demo script launched both services, the browser received held-out predictions, and Ctrl-C stopped both services.
- uv dependency installation and locked synchronization completed. Linux lock resolution selects official CPU torch/torchaudio, with CUDA distributions removed from the lock.
- Real BrainFlow synthetic acquisition, typed sources, paced and accelerated replay, buffer gaps/overlap, causal filter chunk equivalence, all perturbation determinism, three decoder safe round trips, statistics and API/session recording tests passed.
- Browser console received the real synthetic stream and held-out PhysioNet decoder stream. Source switching, pause/resume and standard-label scalp mapping were exercised. Actual screenshots are in docs/screenshots.
- Frontend ESLint, strict TypeScript, nine Vitest cases and production build passed. npm audit reported zero vulnerabilities after the Vitest update.
- Python Ruff formatting/lint and mypy passed. Backend pytest has 38 test cases after the explicit non-dummy-board permission regression tests.
- The frozen benchmark and make reproduce-paper actually ran. It trained 24 CPU subject-model instances and wrote 408 subject/model/condition metric rows, with 507 held-out test trials across eight subjects. Timing results are measured software durations, not hardware latency.
- Publication provenance recomputes classification scores, subject-bootstrap summaries, paired adaptation effects and streaming timing summaries. It checks 450 artifacts linked to the current manuscript.
- The manuscript compiled to eight pages. Source and pypdf-extracted text passed zero-semicolon, zero-em-dash checks. Bibliography and references resolved. No overfull boxes were reported. Final pages were rendered with PyMuPDF for visual inspection.
- The arXiv source directory compiled independently and its clean tarball passed a file-type audit. No external submission was performed.
- make audit passed locally. GitHub Actions are configured but have not run on a remote host. No Linux execution or physical EEG hardware test was performed.

Poppler was not installed. pypdf extraction and PyMuPDF rendering were used as the documented local fallback. Upstream Braindecode montage/deprecation warnings and the FastAPI test-client deprecation notice are non-fatal. The frontend build reports the size of the Three.js-inclusive bundle, without affecting the successful build or local stream operation.
