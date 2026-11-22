"""Regression controls for the post-cap IRLS research harness."""
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts" / "research"))

import continue_irls_floor as harness  # noqa: E402


def test_floor_continuation_starts_from_exact_native_q_not_physical_roundtrip():
    terminal_q = np.array([-0.019140498131655415], dtype=np.float64)
    physical_model = terminal_q * 1000.0
    assert not np.array_equal(physical_model / 1000.0, terminal_q)
    fit = {
        "models_q": np.array([terminal_q]),
        "stages": [{"inner": {"trace": {"models_q": np.array([terminal_q])}}}],
    }

    actual = harness._archived_terminal_q(fit)

    assert np.array_equal(actual, terminal_q)
    assert actual is not fit["models_q"][-1]


def test_floor_continuation_rejects_native_terminal_trace_drift():
    fit = {
        "models_q": np.array([[0.25]], dtype=np.float64),
        "stages": [{"inner": {"trace": {"models_q": np.array([[0.25000000000000006]])}}}],
    }

    with pytest.raises(ValueError, match="differs from final native stage"):
        harness._archived_terminal_q(fit)
