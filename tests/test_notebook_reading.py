"""Regression tests for the reader-facing notebook content parser."""
import importlib.util
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "check_notebooks.py"
SPEC = importlib.util.spec_from_file_location("product_notebooks_check", SCRIPT)
CHECK = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(CHECK)


def test_fenced_markdown_examples_do_not_start_notebook_sections() -> None:
    bar = json.loads((ROOT / "scripts" / "notebook_depth.json").read_text(encoding="utf-8"))
    notebook = {
        "metadata": {"caos": {"level": 0}},
        "cells": [{
            "cell_type": "markdown",
            "source": "## Data\n\n```markdown\n## Example, not a section\n```\n\n## Results\n",
        }],
    }

    reading = CHECK.Reading(notebook, "en", ROOT, bar)

    assert "Data" in reading.prose_sections
    assert "Results" in reading.prose_sections
    assert "Example, not a section" not in reading.prose_sections
