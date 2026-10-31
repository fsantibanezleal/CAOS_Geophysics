"""Focused regression tests for deterministic notebook output handling."""
from __future__ import annotations

import base64
import io
import json
from pathlib import Path

import numpy as np
from PIL import Image

from scripts.run_notebooks import (
    canonical_png,
    discover,
    notebook_scratch_path,
    staged_notebook_source,
    within_declared_plot_tolerance,
)


POLICY = {
    "kind": "png-pixel-drift",
    "max_changed_pixel_fraction": 0.01,
    "max_normalized_mean_absolute_error": 0.01,
}


def test_discover_accepts_multiple_notebook_paths_and_deduplicates() -> None:
    english = "notebooks/en/03-magnetics/01-magnetic-quantities-and-frame.ipynb"
    spanish = "notebooks/es/03-magnetics/01-magnetic-quantities-and-frame.ipynb"

    assert discover([english, spanish, english]) == [
        (Path(__file__).resolve().parents[1] / english).resolve(),
        (Path(__file__).resolve().parents[1] / spanish).resolve(),
    ]


def test_notebook_scratch_isolated_between_language_mirrors() -> None:
    root = Path("external-temp")
    english = notebook_scratch_path(root, "notebooks/en/08-learning/05-m12-velocity-checkpoint.ipynb")
    spanish = notebook_scratch_path(root, "notebooks/es/08-learning/05-m12-velocity-checkpoint.ipynb")
    assert english != spanish
    assert english.is_relative_to(root) and spanish.is_relative_to(root)


def test_check_workspace_stages_released_models_with_notebooks(tmp_path: Path) -> None:
    source = tmp_path / "product"
    model = source / "models" / "picker" / "weights.json"
    notebook = source / "notebooks" / "en" / "06-seismology" / "04-learned-picker.ipynb"
    model.parent.mkdir(parents=True)
    notebook.parent.mkdir(parents=True)
    model.write_text('{"weights": [1, 2, 3]}', encoding="utf-8")
    notebook.write_text("{}", encoding="utf-8")
    (source / "VERSION").write_text("0.04.003\n", encoding="utf-8")
    experiment_output = source / "data" / "experiments" / "discardable-run" / "large-result.bin"
    experiment_output.parent.mkdir(parents=True)
    experiment_output.write_bytes(b"generated run output")
    support = source / "tests" / "data" / "magnetic_survey_support.py"
    fixture = source / "tests" / "fixtures" / "magnetic_survey" / "generate.py"
    support.parent.mkdir(parents=True)
    fixture.parent.mkdir(parents=True)
    support.write_text("SUPPORT = True\n", encoding="utf-8")
    fixture.write_text("FIXTURE = True\n", encoding="utf-8")

    staged = staged_notebook_source(tmp_path / "check", notebook.relative_to(source).as_posix(), source)

    assert staged.is_file()
    repo = staged.parents[3]
    assert (repo / "models" / "picker" / "weights.json").read_bytes() == model.read_bytes()
    assert (repo / "VERSION").read_text(encoding="utf-8") == "0.04.003\n"
    assert not (repo / "data" / "experiments").exists()
    assert (repo / "tests" / "data" / "magnetic_survey_support.py").read_bytes() == support.read_bytes()
    assert (repo / "tests" / "fixtures" / "magnetic_survey" / "generate.py").read_bytes() == fixture.read_bytes()


def encoded_png(image: Image.Image, *, compression: int) -> str:
    stream = io.BytesIO()
    image.save(stream, format="PNG", compress_level=compression)
    return base64.b64encode(stream.getvalue()).decode("ascii")


def write_notebook(path: Path, image: Image.Image, *, label: str = "same", policy: dict | None = POLICY) -> None:
    output = {
        "output_type": "display_data",
        "data": {"image/png": encoded_png(image, compression=1), "text/plain": [label]},
        "metadata": {},
    }
    metadata = {"caos": {}}
    if policy is not None:
        metadata["caos"]["render_tolerance"] = policy
    notebook = {
        "metadata": metadata,
        "cells": [{"cell_type": "code", "source": ["display(image)"], "outputs": [output]}],
    }
    path.write_text(json.dumps(notebook), encoding="utf-8")


def test_canonical_png_is_idempotent_and_pixel_preserving():
    pixels = np.zeros((12, 16, 4), dtype=np.uint8)
    pixels[:, :, :] = [17, 83, 149, 255]
    pixels[2:7, 4:10] = [201, 52, 91, 255]
    image = Image.fromarray(pixels, mode="RGBA")
    encoded = encoded_png(image, compression=1)

    canonical = canonical_png(encoded)
    canonical_again = canonical_png(canonical)

    assert canonical_again == canonical
    with Image.open(io.BytesIO(base64.b64decode(canonical))) as decoded:
        assert decoded.mode == "RGBA"
        assert decoded.size == image.size
        assert decoded.tobytes() == image.tobytes()


def test_declared_tolerance_accepts_only_small_pixel_drift(tmp_path: Path):
    original = Image.new("RGBA", (32, 32), (30, 80, 120, 255))
    changed = original.copy()
    changed.putpixel((4, 7), (31, 81, 121, 255))
    left, right = tmp_path / "fresh.ipynb", tmp_path / "saved.ipynb"
    write_notebook(left, changed)
    write_notebook(right, original)

    assert within_declared_plot_tolerance(left, right)


def test_declared_tolerance_rejects_large_plot_changes(tmp_path: Path):
    original = Image.new("RGBA", (32, 32), (30, 80, 120, 255))
    changed = original.copy()
    for x in range(12):
        for y in range(12):
            changed.putpixel((x, y), (230, 20, 30, 255))
    left, right = tmp_path / "fresh.ipynb", tmp_path / "saved.ipynb"
    write_notebook(left, changed)
    write_notebook(right, original)

    assert not within_declared_plot_tolerance(left, right)


def test_declared_tolerance_does_not_hide_non_image_output_changes(tmp_path: Path):
    image = Image.new("RGBA", (8, 8), (20, 40, 60, 255))
    left, right = tmp_path / "fresh.ipynb", tmp_path / "saved.ipynb"
    write_notebook(left, image, label="fresh metric")
    write_notebook(right, image, label="saved metric")

    assert not within_declared_plot_tolerance(left, right)


def test_plot_tolerance_is_opt_in(tmp_path: Path):
    image = Image.new("RGBA", (8, 8), (20, 40, 60, 255))
    left, right = tmp_path / "fresh.ipynb", tmp_path / "saved.ipynb"
    write_notebook(left, image, policy=None)
    write_notebook(right, image, policy=None)
    fresh = json.loads(left.read_text(encoding="utf-8"))
    fresh["cells"][0]["outputs"][0]["data"]["image/png"] = encoded_png(
        Image.new("RGBA", (8, 8), (21, 40, 60, 255)), compression=1
    )
    left.write_text(json.dumps(fresh), encoding="utf-8")

    assert not within_declared_plot_tolerance(left, right)
