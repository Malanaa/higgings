"""Stage the existing Markdown and public paper for the static docs build."""

import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "tmp" / "docs-site"
if DEST.exists():
    shutil.rmtree(DEST)
shutil.copytree(ROOT / "docs", DEST)
shutil.copy2(ROOT / "paper" / "main.pdf", DEST / "paper.pdf")
shutil.copy2(ROOT / "paper" / "README.md", DEST / "PAPER.md")
for name in ("CONTRIBUTING.md", "THIRD_PARTY_NOTICES.md"):
    shutil.copy2(ROOT / name, DEST / name)


def link(match):
    target = match.group(1)
    if target.startswith(("https:", "http:", "#")):
        return match.group(0)
    if target.startswith("docs/"):
        target = target[5:]
    elif target == "paper/main.pdf":
        target = "paper.pdf"
    elif target == "paper/README.md":
        target = "PAPER.md"
    elif target not in ("CONTRIBUTING.md", "THIRD_PARTY_NOTICES.md"):
        target = "https://github.com/Malanaa/higgings/blob/master/" + target
    return "](" + target + ")"


home = re.sub(r"\]\(([^)]+)\)", link, (ROOT / "README.md").read_text())
(DEST / "index.md").write_text(home)
print(f"Staged documentation in {DEST}")
