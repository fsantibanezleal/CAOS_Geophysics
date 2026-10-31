"""CLI entry point for the source-pinned post-freeze joint state exporter."""

from __future__ import annotations

from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'data-pipeline'))

import joint_survey_instrument  # noqa: E402


if __name__ == '__main__':
    raise SystemExit(joint_survey_instrument.main())
