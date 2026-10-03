import importlib.util
from pathlib import Path

import pytest


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, Path("scripts") / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("text", ["invalid; sentence", "invalid\u2014sentence"])
def test_punctuation_rejected(text):
    with pytest.raises(ValueError, match="prohibited punctuation"):
        load_script("lint_paper_punctuation").check_text(text, "fixture.tex")


def test_punctuation_valid():
    load_script("lint_paper_punctuation").check_text(
        "Valid punctuation, and a colon: yes.", "fixture.tex"
    )


def test_publication_provenance_if_available():
    if not Path("results/manifests/paper_results.json").exists():
        pytest.skip("optional measured artifact verification")
    load_script("verify_results_provenance").verify()
