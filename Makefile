PY = .venv/bin/python
CLI = .venv/bin/neurostreamlab
export MPLCONFIGDIR ?= /private/tmp/neurostreamlab-mpl
.PHONY: bootstrap demo replay-demo benchmark figures paper paper-lint arxiv reproduce-paper audit backend frontend
bootstrap:
	./scripts/bootstrap.sh
demo:
	./scripts/demo.sh
replay-demo:
	$(CLI) benchmark run configs/benchmarks/paper_v1.yaml
	$(CLI) replay --prepare
	./scripts/demo.sh replay
benchmark:
	$(CLI) benchmark run configs/benchmarks/smoke.yaml
figures:
	$(PY) experiments/generate_all.py
paper-lint:
	$(PY) scripts/lint_paper_punctuation.py
paper: paper-lint
	$(PY) scripts/verify_results_provenance.py
	cd paper && latexmk -pdf -interaction=nonstopmode -halt-on-error main.tex
	$(PY) scripts/lint_paper_punctuation.py --pdf
	$(PY) scripts/verify_pdf.py
arxiv: paper
	$(PY) scripts/package_arxiv.py
reproduce-paper:
	$(CLI) doctor
	$(PY) scripts/freeze_experiment.py
	$(CLI) benchmark run configs/benchmarks/paper_v1.yaml --force
	$(CLI) replay --prepare
	$(PY) scripts/profile_streaming.py
	$(PY) scripts/record_data_provenance.py
	$(PY) experiments/generate_all.py
	$(MAKE) arxiv
backend:
	.venv/bin/ruff format --check src tests scripts experiments
	.venv/bin/ruff check src tests scripts experiments
	.venv/bin/mypy src
	$(PY) -m pytest -q
frontend:
	npm run lint --prefix frontend
	npm run typecheck --prefix frontend
	npm test --prefix frontend
	npm run build --prefix frontend
audit: backend frontend arxiv
	@echo "AUDIT PASS: backend, frontend, provenance, paper punctuation, PDF, independent arXiv compile"
