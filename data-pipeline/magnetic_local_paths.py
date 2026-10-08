"""Explicit device-external data/scratch locations; no repository defaults."""

import os
from pathlib import Path

from magnetic_survey_json import fail


def external_path(path):
    value = Path(path)
    if not value.is_absolute():
        fail('durability', '$/path', 'Explicit absolute external device path required')
    # Inspect lexical parents before resolving so a repository symlink cannot
    # disguise a repository-owned output as an external data location.
    resolved = value.resolve()
    for candidate in (value, resolved):
        for parent in (candidate, *candidate.parents):
            if (parent.is_symlink() or parent.is_junction() or (parent/'.git').exists()
                    or parent.name.lower() in ('_repos', '_worktrees', '.git')):
                fail('durability', '$/path', 'Data/models/temp cannot be inside a repository or worktree')
    if resolved == Path(resolved.anchor):
        fail('durability', '$/path', 'A whole device volume is not a data generation root')
    return resolved


def local_data_root(root=None):
    explicit = root if root is not None else os.environ.get('GEOPHYSICS_LOCAL_DATA_ROOT')
    if not explicit:
        fail('durability', '$/data-root', 'Set GEOPHYSICS_LOCAL_DATA_ROOT or supply --data-root; no repository fallback')
    return external_path(explicit)


def data_output(path, root=None):
    storage = local_data_root(root)
    output = external_path(path)
    if output == storage or not output.is_relative_to(storage):
        fail('durability', '$/output', 'Fresh output must be a child of the explicit external data root')
    if not output.parent.is_dir():
        fail('durability', '$/output', 'Create the external parent directory explicitly')
    return output


def configure_scratch(root=None):
    explicit = root if root is not None else os.environ.get('GEOPHYSICS_TEMP_ROOT')
    if not explicit:
        fail('durability', '$/temp-root', 'Supply --temp-root or GEOPHYSICS_TEMP_ROOT from device workspace data roots')
    scratch = external_path(explicit)
    if not scratch.is_dir():
        fail('durability', '$/temp-root', 'Explicit external scratch directory must already exist')
    os.environ.update(TEMP=str(scratch), TMP=str(scratch), TMPDIR=str(scratch),
                      NUMBA_CACHE_DIR=str(scratch/'numba'), PYTHONDONTWRITEBYTECODE='1',
                      OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
    return scratch
