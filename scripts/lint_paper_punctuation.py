import argparse
import shutil
import subprocess
from pathlib import Path


def check_text(text: str, source: str) -> None:
    for prohibited in (";", "\u2014"):
        if prohibited in text:
            line = text[: text.index(prohibited)].count("\n") + 1
            raise ValueError(f"{source}:{line}: prohibited punctuation {prohibited!r}")


def lint(root: Path, pdf: bool = False) -> None:
    for path in root.rglob("*.tex"):
        check_text(path.read_text(), str(path))
    if pdf:
        document = root / "main.pdf"
        if shutil.which("pdftotext"):
            result = subprocess.run(
                ["pdftotext", str(document), "-"], capture_output=True, text=True, check=True
            )
            text = result.stdout
        else:
            from pypdf import PdfReader

            text = "\n".join(page.extract_text() for page in PdfReader(document).pages)
        check_text(text, str(document))
        if "??" in text:
            raise ValueError("undefined PDF reference")
    print("Paper punctuation and reference text check passed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default="paper")
    parser.add_argument("--pdf", action="store_true")
    args = parser.parse_args()
    lint(Path(args.root), args.pdf)
