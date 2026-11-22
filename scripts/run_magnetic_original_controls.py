"""Run magnetic original-noise controls with their retained M04 source closure.

The M04 native controls are retained as six exact source files outside this
checkout. This runner pins BLAS/OpenMP before NumPy imports and preloads those
frozen magnetic modules before pytest adds the current product pipeline.
"""

from __future__ import annotations

import argparse
import importlib
import os
from pathlib import Path
import sys


MODULES = (
    "magnetic_forward",
    "magnetic_inverse_precision",
    "magnetic_inverse",
    "magnetic_optimizer_adapter",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True,
                        help="external directory containing the retained six-file M04 source closure")
    args, pytest_args = parser.parse_known_args()

    repo = Path(__file__).resolve().parents[1]
    source = args.source_root.resolve(strict=True)
    if not source.is_absolute() or (source / ".git").exists():
        parser.error("--source-root must be an external source snapshot, not a Git checkout")

    for key in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[key] = "1"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    os.environ["GEOPHYSICS_M02_MAGNETIC_SOURCE"] = str(source)

    # Import the test module only after its helper can validate the pinned
    # source closure; importing it also loads the current physical solvers.
    sys.path.insert(0, str(repo / "tests" / "numerics"))
    sys.path.insert(0, str(repo / "data-pipeline"))
    import test_physical_original_optimizer as controls

    try:
        controls.magnetic_control_source()
    except (OSError, RuntimeError) as error:
        parser.error(str(error))

    sys.path.insert(0, str(source / "data-pipeline"))
    for module in MODULES:
        importlib.import_module(module)

    import pytest

    if pytest_args[:1] == ["--"]:
        pytest_args = pytest_args[1:]
    has_test_target = any(
        value == "tests"
        or value.startswith(("tests/", "tests\\", "test_"))
        or "::" in value
        for value in pytest_args
    )
    if not has_test_target:
        pytest_args.insert(0, "tests/numerics/test_physical_original_optimizer.py")
    return int(pytest.main(pytest_args))


if __name__ == "__main__":
    raise SystemExit(main())
