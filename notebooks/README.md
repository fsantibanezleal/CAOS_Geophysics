# Geophysics notebooks

This directory is reserved for the bilingual, executable research lessons that will connect the documented theory to the repository's real pipeline modules and released arrays. Notebook execution is local and uses an isolated `.venv-notebooks`; CI runs only the static notebook guard.

The files are intentionally not copied from the SIR example product. No `.ipynb` files are registered yet. The static check will remain red until the English and Spanish lesson trees have matching, sourced notebooks whose setup, data, methods, outputs and references satisfy the template v0.11.000 notebook contract.

Install the pinned notebook environment with the repository's setup tooling, run `python scripts/check_notebooks.py`, and execute a selected lesson with `python scripts/run_notebooks.py --only notebooks/en/<topic>/<lesson>.ipynb`. For a clean, non-writing execution check, provide the device temporary root with `python scripts/run_notebooks.py --check --tmp <device-temp-root>`.

The lesson sequence should follow the existing science documentation and algorithms: data rights and physical metadata; potential-field forward operators and ambiguity; weighted inverse problems and regularization; EDI quality control and layered-earth inversion; wave propagation and FWI; joint inversion; held-out learned-method evaluation; reproducibility and uncertainty. This outline is not a claim that those notebook lessons have been authored.
