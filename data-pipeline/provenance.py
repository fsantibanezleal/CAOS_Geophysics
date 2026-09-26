"""Dependency-free scientific source fingerprints shared by producer and CI guard."""
from pathlib import Path
import hashlib
import json


def generator_fingerprint(family,iterations=28,epochs=180,version='0.04.001'):
    modules=['geology.py']
    if family=='seismic':modules+=['seismic.py']
    elif family=='mt':modules+=['electromagnetics.py']
    else:
        modules+=['potential.py','spatial_inverse.py','evaluation.py']
        if family=='joint':modules+=['joint.py','petrophysics.py']
        if family=='learned':modules+=['learning.py']
    digest=hashlib.sha256()
    for name in sorted(modules):
        digest.update(name.encode())
        digest.update((Path(__file__).parent/name).read_bytes())
    digest.update(json.dumps(dict(version=version,iterations=iterations if family=='seismic' else None,
                                  epochs=epochs if family=='learned' else None),sort_keys=True).encode())
    return digest.hexdigest()
