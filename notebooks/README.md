# Geophysics research lessons

This bilingual course connects geophysical theory, documented assumptions, executable repository methods, and case evidence. It covers inverse-problem foundations; gravity and magnetic surveys; magnetotelluric data and layered-earth responses; electrical resistivity; seismic waveforms and travel-time/FWI methods; joint inversion; and held-out evaluation of learned methods.

The [English index](en/README.md) and [índice en español](es/README.md) enumerate each lesson by topic and level and link to its counterpart. Lessons import repository methods instead of reimplementing solvers. Their code cells are executed by the pinned `.venv-notebooks` environment through `scripts/run_notebooks.py`; CI runs the static contract only.

Build the environment with `scripts/setup.ps1 -Notebooks` on Windows or `scripts/setup.sh --notebooks` on Linux/macOS. Run `python scripts/check_notebooks.py` for the static gate. Use `python scripts/run_notebooks.py --check --tmp <device-temp-root>` for a non-writing fresh execution check; the runner itself owns committed outputs and execution counts.
