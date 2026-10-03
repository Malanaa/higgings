import shutil
import subprocess
import tarfile
from pathlib import Path

source = Path("paper")
bundle = source / "arxiv_bundle"
if bundle.exists():
    shutil.rmtree(bundle)
bundle.mkdir()
for filename in ("main.tex", "refs.bib", "macros.tex"):
    shutil.copy2(source / filename, bundle / filename)
for directory in ("figures", "generated"):
    target = bundle / directory
    target.mkdir()
    for file in (source / directory).iterdir():
        if file.suffix in (".tex", ".pdf", ".png"):
            shutil.copy2(file, target / file.name)
subprocess.run(
    ["latexmk", "-pdf", "-interaction=nonstopmode", "-halt-on-error", "main.tex"],
    cwd=bundle,
    check=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
)
subprocess.run(
    [".venv/bin/python", "scripts/lint_paper_punctuation.py", "--root", str(bundle), "--pdf"],
    check=True,
)
# The compiled bundle PDF is retained separately for review, not in submission source.
shutil.copy2(bundle / "main.pdf", source / "arxiv_verified.pdf")
for file in bundle.iterdir():
    if file.is_file() and file.name not in ("main.tex", "refs.bib", "macros.tex", "main.bbl"):
        file.unlink()
archive = source / "neurostreamlab-arxiv.tar.gz"
with tarfile.open(archive, "w:gz") as tar:
    for file in sorted(bundle.rglob("*")):
        if file.is_file():
            tar.add(file, arcname=str(file.relative_to(bundle)))
with tarfile.open(archive) as tar:
    if any(
        Path(m.name).suffix not in (".tex", ".bib", ".bbl", ".pdf", ".png")
        for m in tar.getmembers()
    ):
        raise ValueError("unexpected submission file")
print(f"Independent bundle compile passed: {archive}")
