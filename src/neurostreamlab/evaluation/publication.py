"""All publication numbers and numerical figures originate from completed runs."""

import hashlib
import json
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

from neurostreamlab import __version__
from neurostreamlab.evaluation.runner import aggregate

LABELS = {"csp_lda": "CSP + LDA", "bandpower_logreg": "Bandpower + LR", "eegnet": "EEGNet"}
COLORS = {"csp_lda": "#007c91", "bandpower_logreg": "#be7738", "eegnet": "#7c5ea1"}
MARKERS = {"csp_lda": "o", "bandpower_logreg": "s", "eegnet": "^"}


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def table_text(aggregated: list[dict], run: dict) -> dict[str, str]:
    result = {}
    for dataset in run["config"]["datasets"]:
        rows = [r for r in aggregated if r["dataset"] == dataset and r["condition"] == "clean"]
        text = [
            r"\begin{tabular}{lrrr}",
            r"\toprule",
            r"Decoder & BA (95\% CI) & Median (ms) & P95 (ms) \\",
            r"\midrule",
        ]
        for row in rows:
            text.append(
                f"{LABELS[row['decoder']]} & {100 * row['mean']:.1f} [{100 * row['ci_low']:.1f}, {100 * row['ci_high']:.1f}] & {row['latency_median_ms']:.3f} & {row['latency_p95_ms']:.3f} "
                + r"\\"
            )
        text.extend([r"\bottomrule", r"\end{tabular}"])
        result[f"clean_{dataset}.tex"] = "\n".join(text) + "\n"
    subjects = run["subjects"]
    text = [
        r"\begin{tabular}{lrrrrr}",
        r"\toprule",
        r"Dataset & Subjects & Train & Test & Channels & Hz \\",
        r"\midrule",
    ]
    for dataset in run["config"]["datasets"]:
        group = [s for s in subjects if s["dataset"] == dataset]
        text.append(
            f"{dataset.replace('_', r'\_')} & {len(group)} & {sum(s['n_train'] for s in group)} & {sum(s['n_test'] for s in group)} & {len(group[0]['channels'])} & {group[0]['fs']:.0f} "
            + r"\\"
        )
    text.extend([r"\bottomrule", r"\end{tabular}"])
    result["cohort.tex"] = "\n".join(text) + "\n"
    text = [
        r"\begin{tabular}{llrr}",
        r"\toprule",
        r"Dataset & Decoder & Shifted BA & RMS BA \\",
        r"\midrule",
    ]
    for dataset in run["config"]["datasets"]:
        for decoder in run["config"]["decoders"]:
            baseline = next(
                r
                for r in aggregated
                if r["dataset"] == dataset
                and r["decoder"] == decoder
                and r["condition"] == "amplitude_2"
                and r["adaptation"] == "none"
            )
            adapted = next(
                r
                for r in aggregated
                if r["dataset"] == dataset
                and r["decoder"] == decoder
                and r["condition"] == "amplitude_2"
                and r["adaptation"] == "unlabeled_rms"
            )
            text.append(
                f"{dataset.replace('_', r'\_')} & {LABELS[decoder]} & {baseline['mean'] * 100:.1f} & {adapted['mean'] * 100:.1f} "
                + r"\\"
            )
    text.extend([r"\bottomrule", r"\end{tabular}"])
    result["adaptation.tex"] = "\n".join(text) + "\n"
    macros = {
        "SoftwareVersion": __version__,
        "TotalSubjects": len(subjects),
        "TrainTrials": sum(s["n_train"] for s in subjects),
        "TestTrials": sum(s["n_test"] for s in subjects),
        "EpochSeconds": run["config"]["tmax"] - run["config"]["tmin"],
        "SeedValue": run["config"]["seed"],
        "MaxEpochs": run["config"]["eegnet_epochs"],
        "BootstrapSamples": run["config"]["bootstrap_samples"],
        "LatencyCalls": run["config"]["latency_calls"],
    }
    for dataset, prefix in (("PhysionetMI", "Physio"), ("BNCI2014_001", "BNCI")):
        for decoder, short in (
            ("csp_lda", "CSP"),
            ("eegnet", "EEGNet"),
            ("bandpower_logreg", "Bandpower"),
        ):
            for condition, suffix in (
                ("clean", "Clean"),
                ("noise_2", "Noise"),
                ("dropout_2", "Dropout"),
                ("amplitude_2", "Amplitude"),
            ):
                r = next(
                    r
                    for r in aggregated
                    if r["dataset"] == dataset
                    and r["decoder"] == decoder
                    and r["condition"] == condition
                    and r["adaptation"] == "none"
                )
                macros[f"{prefix}{short}{suffix}"] = f"{r['mean'] * 100:.1f}"
                if condition == "clean":
                    macros[f"{prefix}{short}Latency"] = f"{r['latency_median_ms']:.3f}"
            r = next(
                r
                for r in aggregated
                if r["dataset"] == dataset
                and r["decoder"] == decoder
                and r["condition"] == "amplitude_2"
                and r["adaptation"] == "unlabeled_rms"
            )
            macros[f"{prefix}{short}Adapted"] = f"{r['mean'] * 100:.1f}"
    result["results_macros.tex"] = (
        "\n".join(f"\\newcommand{{\\{key}}}{{{value}}}" for key, value in macros.items()) + "\n"
    )
    return result


def streaming_text(profile: dict) -> dict[str, str]:
    lines = [
        r"\begin{tabular}{lrrrr}",
        r"\toprule",
        r"Mode & Frames & Median (ms) & P95 (ms) & Predictions \\",
        r"\midrule",
    ]
    macros = []
    for mode, prefix in (("synthetic", "Synthetic"), ("replay", "Replay")):
        row = profile["modes"][mode]
        lines.append(
            f"{mode.capitalize()} & {row['frames']} & {row['median_ms']:.3f} & {row['p95_ms']:.3f} & {row['predictions']} "
            + r"\\"
        )
        for key, suffix in (
            ("median_ms", "PipelineMedian"),
            ("p95_ms", "PipelinePninetyfive"),
            ("frames", "Frames"),
            ("predictions", "Predictions"),
            ("missing_samples", "Gaps"),
        ):
            value = f"{row[key]:.3f}" if key.endswith("ms") else str(row[key])
            macros.append(f"\\newcommand{{\\{prefix}{suffix}}}{{{value}}}")
    lines.extend([r"\bottomrule", r"\end{tabular}"])
    return {
        "streaming.tex": "\n".join(lines) + "\n",
        "streaming_macros.tex": "\n".join(macros) + "\n",
    }


def generate(output: str = "results") -> None:
    root = Path(output)
    aggregate(output)
    latest = json.loads((root / "manifests/latest.json").read_text())
    directory = Path(latest["run_directory"])
    run = json.loads((directory / "run.json").read_text())
    aggregated = json.loads((root / "aggregated/metrics.json").read_text())
    generated = Path("paper/generated")
    generated.mkdir(parents=True, exist_ok=True)
    profile = json.loads((root / "raw/streaming_profile.json").read_text())
    texts = {**table_text(aggregated, run), **streaming_text(profile)}
    for filename, text in texts.items():
        (generated / filename).write_text(text)
        (root / "tables").mkdir(exist_ok=True)
        (root / "tables" / filename).write_text(text)
    plt.rcParams.update(
        {"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "pdf.fonttype": 42}
    )
    figure_dir = Path("paper/figures")
    figure_dir.mkdir(exist_ok=True)
    for kind in ("noise", "dropout"):
        fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8), sharey=True)
        levels = [0, 0.5, 1, 2] if kind == "noise" else [0, 1, 2]
        conditions = (
            ["clean", "noise_0.5", "noise_1", "noise_2"]
            if kind == "noise"
            else ["clean", "dropout_1", "dropout_2"]
        )
        for ax, dataset in zip(axes, run["config"]["datasets"], strict=True):
            for decoder in run["config"]["decoders"]:
                rows = [
                    next(
                        r
                        for r in aggregated
                        if r["dataset"] == dataset
                        and r["decoder"] == decoder
                        and r["condition"] == c
                        and r["adaptation"] == "none"
                    )
                    for c in conditions
                ]
                mean = np.array([r["mean"] for r in rows])
                lo, hi = (
                    np.array([r["ci_low"] for r in rows]),
                    np.array([r["ci_high"] for r in rows]),
                )
                ax.plot(
                    levels,
                    mean,
                    marker=MARKERS[decoder],
                    color=COLORS[decoder],
                    label=LABELS[decoder],
                )
                ax.fill_between(levels, lo, hi, color=COLORS[decoder], alpha=0.1)
            ax.set_title(dataset.replace("_", " "))
            ax.set_ylim(0, 1)
            ax.set_xlabel(
                "Noise SD / training channel RMS" if kind == "noise" else "Dropped central channels"
            )
            ax.set_xticks(levels)
            ax.grid(alpha=0.15)
            ax.axhline(0.5, color="#777777", linewidth=0.7, linestyle="--")
        axes[0].set_ylabel("Balanced accuracy")
        axes[1].legend(fontsize=8, loc="lower left")
        fig.tight_layout()
        fig.savefig(figure_dir / f"{kind}.pdf", metadata={"CreationDate": None})
        plt.close(fig)
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 3.8), sharey=True)
    for ax, dataset in zip(axes, run["config"]["datasets"], strict=True):
        x = np.arange(3)
        for condition in ("clean", "amplitude_2"):
            for adaptation in ["none"] if condition == "clean" else ["none", "unlabeled_rms"]:
                rows = [
                    next(
                        r
                        for r in aggregated
                        if r["dataset"] == dataset
                        and r["decoder"] == decoder
                        and r["condition"] == condition
                        and r["adaptation"] == adaptation
                    )
                    for decoder in run["config"]["decoders"]
                ]
                offset = -0.23 if condition == "clean" else 0 if adaptation == "none" else 0.23
                ax.bar(
                    x + offset,
                    [r["mean"] for r in rows],
                    width=0.22,
                    label="Clean"
                    if condition == "clean"
                    else "Gain x2"
                    if adaptation == "none"
                    else "Gain x2 + RMS",
                    color="#557b91"
                    if condition == "clean"
                    else "#c38e59"
                    if adaptation == "none"
                    else "#78a78d",
                    yerr=np.array(
                        [
                            [r["mean"] - r["ci_low"] for r in rows],
                            [r["ci_high"] - r["mean"] for r in rows],
                        ]
                    ),
                    capsize=2,
                    error_kw={"linewidth": 0.7},
                )
        ax.set_title(dataset.replace("_", " "))
        ax.set_xticks(x, [LABELS[d] for d in run["config"]["decoders"]], fontsize=8)
        ax.set_ylim(0, 1)
        ax.grid(axis="y", alpha=0.15)
    axes[0].set_ylabel("Balanced accuracy")
    axes[1].legend(fontsize=8, loc="lower left")
    fig.tight_layout()
    fig.savefig(figure_dir / "adaptation.pdf", metadata={"CreationDate": None})
    plt.close(fig)
    # Architecture is a conceptual figure, not an experimental numerical result.
    fig, ax = plt.subplots(figsize=(10.5, 2.7))
    ax.set_axis_off()
    boxes = [
        (0.02, 0.6, "Synthetic / replay\nexplicit hardware adapter"),
        (0.35, 0.6, "Seeded perturbations\ntimestamps + markers"),
        (0.68, 0.6, "Rolling buffer\ncausal signal processing"),
        (0.68, 0.12, "Trial decoder\nprobabilities + decisions"),
        (0.35, 0.12, "FastAPI / WebSocket\nCanvas + 3D console"),
        (0.02, 0.12, "Metrics + manifests\nfigures + manuscript"),
    ]
    for box_x, y, label in boxes:
        ax.text(
            box_x + 0.14,
            y + 0.1,
            label,
            transform=ax.transAxes,
            ha="center",
            va="center",
            fontsize=10,
            bbox={"boxstyle": "round,pad=0.6", "facecolor": "#eef4f5", "edgecolor": "#718c98"},
        )
    for a, b in ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5)):
        xa, ya, _ = boxes[a]
        xb, yb, _ = boxes[b]
        start = (
            (xa + 0.29, ya + 0.1)
            if a < 2
            else (xa + 0.14, ya - 0.05)
            if a == 2
            else (xa - 0.01, ya + 0.1)
        )
        end = (
            (xb - 0.01, yb + 0.1)
            if a < 2
            else (xb + 0.14, yb + 0.25)
            if a == 2
            else (xb + 0.29, yb + 0.1)
        )
        ax.annotate(
            "",
            xy=end,
            xytext=start,
            xycoords="axes fraction",
            arrowprops={"arrowstyle": "->", "color": "#496573"},
        )
    fig.savefig(
        figure_dir / "architecture.pdf", bbox_inches="tight", metadata={"CreationDate": None}
    )
    plt.close(fig)
    rows = json.loads((directory / "metrics.json").read_text())
    # Preserve model metadata in the published result tree, without redistributing weights.
    for row in rows:
        model_path = Path(row["model_manifest"])
        target = directory / f"model_{row['dataset']}_{row['subject']}_{row['decoder']}.json"
        if model_path.exists():
            target.write_bytes(model_path.read_bytes())
        elif not target.exists():
            raise FileNotFoundError(f"missing model provenance: {target}")
    artifacts = [
        *directory.glob("*.json"),
        *directory.glob("*.npz"),
        *root.joinpath("aggregated").glob("*"),
        *generated.glob("*.tex"),
        *figure_dir.glob("*.pdf"),
    ]
    if (root / "raw/streaming_profile.json").exists():
        artifacts.append(root / "raw/streaming_profile.json")
    if (root / "manifests/data_sources.json").exists():
        artifacts.append(root / "manifests/data_sources.json")
    manifest = {
        "paper_commit": run["git_commit"],
        "run_directory": str(directory),
        "run_id": run["run_id"],
        "config_path": latest["config_path"],
        "config_hash": run["config_hash"],
        "software": run["packages"],
        "subjects": run["subjects"],
        "model_hashes": sorted({r["model_hash"] for r in rows}),
        "artifacts": {str(p): digest(p) for p in artifacts},
        "tables": [str(p) for p in generated.glob("*.tex")],
        "figures": [str(p) for p in figure_dir.glob("*.pdf")],
    }
    (root / "manifests/paper_results.json").write_text(json.dumps(manifest, indent=2))
    print("Generated verified-result tables, macros, figures and paper manifest")
