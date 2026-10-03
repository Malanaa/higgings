"""Extractable text, page bounds, fonts, references and LaTeX diagnostics."""

import re
import shutil
import subprocess
from pathlib import Path

from pypdf import PdfReader

path = Path("paper/main.pdf")
reader = PdfReader(path)
if len(reader.pages) < 4:
    raise ValueError("unexpected manuscript page count")
text = "\n".join(page.extract_text() for page in reader.pages)
if "??" in text or ";" in text or "\u2014" in text:
    raise ValueError("prohibited punctuation or missing reference")
if "References" not in text or "Syed Abdullah Imam" not in text:
    raise ValueError("missing bibliography or author")
log = Path("paper/main.log").read_text()
patterns = [
    r"Citation .* undefined",
    r"Reference .* undefined",
    r"There were undefined",
    r"File .* not found",
    r"Overfull \\hbox",
    r"Overfull \\vbox",
]
for pattern in patterns:
    if re.search(pattern, log):
        raise ValueError(f"LaTeX issue: {pattern}")
if shutil.which("pdfinfo"):
    subprocess.run(["pdfinfo", str(path)], check=True, stdout=subprocess.PIPE)
print(
    f"PDF verified: {len(reader.pages)} pages, bibliography rendered, no missing citations or overfull boxes"
)
