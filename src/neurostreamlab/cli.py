import importlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import typer

from neurostreamlab import NAME, __version__

app = typer.Typer(
    help=f"{NAME}: local EEG replay and reproducible robustness research", no_args_is_help=True
)
datasets = typer.Typer(help="Public dataset discovery and local downloads")
benchmarks = typer.Typer(help="Frozen experiment execution and subject aggregation")
models = typer.Typer(help="Train and evaluate model artifacts")
papers = typer.Typer(help="Build, lint and package the manuscript")
figures = typer.Typer(help="Generate publication outputs from measured results")
app.add_typer(datasets, name="dataset")
app.add_typer(benchmarks, name="benchmark")
app.add_typer(models, name="model")
app.add_typer(papers, name="paper")
app.add_typer(figures, name="figures")


@app.command()
def version() -> None:
    print(f"{NAME} {__version__}")


@app.command()
def doctor() -> None:
    import platform

    checks = {"python": platform.python_version()}
    for name in ("brainflow", "mne", "moabb", "torch", "braindecode"):
        try:
            importlib.import_module(name)
            checks[name] = "ok"
        except ImportError as exc:
            checks[name] = f"missing: {exc}. Run ./scripts/bootstrap.sh"
    for tool in ("node", "pdflatex", "latexmk", "pdftotext"):
        checks[tool] = shutil.which(tool) or "missing: install the tool for its build target"
    checks["frontend"] = (
        "ok" if Path("frontend/node_modules").exists() else "Run npm ci --prefix frontend"
    )
    Path("data").mkdir(exist_ok=True)
    checks["data_write_access"] = str(os.access("data", os.W_OK))
    print(json.dumps(checks, indent=2))


@app.command()
def server(mode: str = "synthetic", port: int = 8000) -> None:
    import uvicorn

    from neurostreamlab.server.app import create_app

    if mode not in ("synthetic", "replay"):
        raise typer.BadParameter("mode must be synthetic or replay")
    uvicorn.run(create_app(mode), host="127.0.0.1", port=port)


@app.command()
def demo() -> None:
    subprocess.run(["bash", "scripts/demo.sh"], check=True)


@app.command()
def replay(prepare: bool = False, config: str = "configs/benchmarks/paper_v1.yaml") -> None:
    from neurostreamlab.server.runtime import prepare_replay

    if prepare:
        print(prepare_replay(config))
    else:
        server("replay")


@datasets.command("list")
def dataset_list() -> None:
    from neurostreamlab.datasets.adapter import DATASETS

    print(json.dumps(DATASETS, indent=2))


@datasets.command("info")
def dataset_info(name: str) -> None:
    from neurostreamlab.datasets.adapter import dataset_info

    print(json.dumps(dataset_info(name), indent=2))


@datasets.command("fetch")
def dataset_fetch(
    name: str, subject: int = 1, config: str = "configs/benchmarks/smoke.yaml", force: bool = False
) -> None:
    from neurostreamlab.config import load_config
    from neurostreamlab.datasets.adapter import load_subject

    data = load_subject(name, subject, load_config(config), force)
    print(f"Cached {len(data.y)} trials, {data.fs} Hz, {data.channels}")


@benchmarks.command("run")
def benchmark_run(config: str, force: bool = False) -> None:
    from neurostreamlab.evaluation.runner import run_benchmark

    print(run_benchmark(config, force))


@benchmarks.command("aggregate")
def benchmark_aggregate(output: str = "results") -> None:
    from neurostreamlab.evaluation.runner import aggregate

    print(aggregate(output))


@models.command("train")
def model_train(
    dataset: str = "PhysionetMI",
    subject: int = 1,
    decoder: str = "csp_lda",
    config: str = "configs/benchmarks/smoke.yaml",
    output: str = "models/custom",
) -> None:
    import time

    import numpy as np

    from neurostreamlab.config import load_config
    from neurostreamlab.datasets.adapter import load_subject
    from neurostreamlab.decoders.registry import create_decoder
    from neurostreamlab.evaluation.metrics import audit_split
    from neurostreamlab.evaluation.runner import git_commit
    from neurostreamlab.preprocessing.pipeline import preprocess_epochs

    settings = load_config(config)
    data = load_subject(dataset, subject, settings)
    split = audit_split(data.metadata)
    train = np.flatnonzero(data.metadata.split == "train")
    metadata = {
        "channels": data.channels,
        "fs": data.fs,
        "n_times": data.x.shape[-1],
        "seed": settings.seed,
        "classes": ["left_hand", "right_hand"],
        "dataset": dataset,
        "subjects": [subject],
        "training_trial_ids": split["train_trial_ids"],
        "preprocessing": settings.preprocessing.model_dump(),
        "preprocessing_id": "trial_zero_phase_v1",
        "git_commit": git_commit(),
    }
    kwargs = (
        {"epochs": settings.eegnet_epochs, "patience": settings.eegnet_patience}
        if decoder == "eegnet"
        else {}
    )
    model = create_decoder(decoder, metadata, **kwargs)
    start = time.perf_counter()
    model.fit(preprocess_epochs(data.x[train], data.fs, settings.preprocessing), data.y[train])
    model.metadata["training_seconds"] = time.perf_counter() - start
    model.save(Path(output))
    print(f"Saved training-only artifact: {output}")


@models.command("evaluate")
def model_evaluate(
    artifact: str,
    dataset: str = "PhysionetMI",
    subject: int = 1,
    config: str = "configs/benchmarks/smoke.yaml",
) -> None:
    import numpy as np

    from neurostreamlab.config import FilterConfig, load_config
    from neurostreamlab.datasets.adapter import load_subject
    from neurostreamlab.decoders.base import validate_metadata
    from neurostreamlab.decoders.registry import load_decoder
    from neurostreamlab.evaluation.metrics import classification_metrics
    from neurostreamlab.preprocessing.pipeline import preprocess_epochs

    data = load_subject(dataset, subject, load_config(config))
    model = load_decoder(Path(artifact))
    validate_metadata(model.metadata, data.channels, data.fs)
    test = np.flatnonzero(data.metadata.split == "test")
    if set(data.metadata.iloc[test].trial_id) & set(model.metadata.get("training_trial_ids", [])):
        raise ValueError("evaluation trials overlap training")
    p = model.predict_proba(
        preprocess_epochs(
            data.x[test], data.fs, FilterConfig.model_validate(model.metadata["preprocessing"])
        )
    )
    print(json.dumps(classification_metrics(data.y[test], p), indent=2))


@figures.command("generate")
def figures_generate(output: str = "results") -> None:
    from neurostreamlab.evaluation.publication import generate

    generate(output)


@papers.command("build")
def paper_build() -> None:
    subprocess.run(["make", "paper"], check=True)


@papers.command("lint")
def paper_lint() -> None:
    subprocess.run(["make", "paper-lint"], check=True)


@papers.command("package")
def paper_package() -> None:
    subprocess.run(["make", "arxiv"], check=True)


if __name__ == "__main__":
    app()
