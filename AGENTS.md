# Repository work

Preserve the scientific boundary: synthetic streams are engineering tests, recorded replay uses held-out human EEG, hardware connections require explicit configuration. No clinical claims.

Use Python 3.12 and uv.lock, Node 22 or 24 and the npm lockfile. Run make backend and make frontend after relevant changes. Run make audit for publication changes.

Do not change the frozen paper_v1 evaluation design based on outcomes. Bug fixes require a documented experiment revision and rerunning affected comparisons. Every paper number belongs in generated TeX from machine-readable results. Do not fabricate results, confidence intervals, timings or citations.

Keep datasets, checkpoints and sessions local and excluded from Git. Never use pickle for model import. Preserve checksums and exact channel-order checks.

No semicolons or em dashes in visible manuscript text. PDF punctuation scan is authoritative.
