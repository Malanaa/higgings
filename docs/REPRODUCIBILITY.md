# Reproduction

Use Python 3.12, Node 22 or 24, and a standard TeX Live/MacTeX installation with latexmk, pdflatex, bibtex and optionally Poppler (pdfinfo/pdftotext/pdftoppm). pypdf and PyMuPDF provide extraction/rendering when Poppler is unavailable. macOS arm64 was used locally. Linux uses the same CPU scientific pipeline, but native BrainFlow packaging and timing need platform verification.

```bash
./scripts/bootstrap.sh
make benchmark                 # subject-1 smoke
make reproduce-paper           # downloads fixed subset, trains, measures, generates and builds
make audit                     # complete release validation using existing results
```

uv.lock and frontend/package-lock.json resolve dependencies. The bootstrap uses frozen locks. The paper config is configs/benchmarks/paper_v1.yaml and its freeze SHA-256 is recorded before execution. The run stores Python, OS, architecture, package versions, source digest, seed, subjects, sessions, filters, shifts, split identifiers, model hashes, training duration, inference distributions and raw probabilities. At initial execution the repository had no Git history, so commit is honestly recorded as uncommitted and the source digest identifies the executed tree. A later Git commit does not retroactively alter this metadata.

Numerical outputs reside in results/raw/<run ID>, results/aggregated, results/tables, paper/generated and paper/figures. results/manifests/paper_results.json hashes every manuscript input. `scripts/verify_results_provenance.py` recomputes metrics and generated tables, and rejects missing or altered artifacts. No manual paper result values are needed, because prose uses generated macros.

`make reproduce-paper` forces scientific reruns, then prepares held-out replay, profiles processing, regenerates output and independently compiles the arXiv source. Values may differ slightly with package or CPU implementations. Timing is expected to vary. The cached raw epochs are never model fit statistics. To download raw epochs afresh use dataset fetch --force. Expensive model/results cache keys include configuration and source digests, and incompatible source changes yield a new run ID.

For a build without dataset downloads use make paper and make arxiv against checked-in results. For a local real-EEG demonstration use make replay-demo, which creates held-out data and model artifacts as needed, then serves http://127.0.0.1:5173. Ctrl-C shuts both services down. Synthetic `make demo` uses no dataset or trained motor imagery model.
