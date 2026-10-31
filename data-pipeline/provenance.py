"""Dependency-free scientific source fingerprints shared by producer and CI guard."""
from pathlib import Path
import hashlib
import json


# The committed 0.04.002 learned artifacts were generated with the historical
# adaptive pooling implementation. At the canonical 32x32 survey shape its
# output is bitwise equal to the current divisible-shape average-pooling path.
# Keep the producer fingerprint intact and admit only this exact historical
# fingerprint in release readers. Never use this alias for artifact generation.
_HISTORICAL_FINGERPRINTS = {
    ('learned', '0.04.002', 28, 180): frozenset({
        '9d1b09a6af91c92ee79765ee264f63b254ad2312214371c90da770aee55708b3',
    }),
}


def generator_fingerprint(family,iterations=28,epochs=180,version='0.04.003'):
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


def accepted_generator_fingerprints(family, iterations=28, epochs=180, version='0.04.003'):
    """Return exact fingerprints accepted for reading this producer version."""
    current = generator_fingerprint(family, iterations, epochs, version)
    historical = _HISTORICAL_FINGERPRINTS.get((family, version, iterations, epochs), ())
    return frozenset((current, *historical))


def matches_generator_fingerprint(family, fingerprint, iterations=28, epochs=180, version='0.04.003'):
    return fingerprint in accepted_generator_fingerprints(family, iterations, epochs, version)
