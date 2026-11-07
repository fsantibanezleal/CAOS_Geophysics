from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))
from provenance import accepted_generator_fingerprints, generator_fingerprint, matches_generator_fingerprint


LEGACY_LEARNED_004002 = "9d1b09a6af91c92ee79765ee264f63b254ad2312214371c90da770aee55708b3"


def test_historical_learned_fingerprint_is_readable_without_relabeling():
    accepted = accepted_generator_fingerprints("learned", version="0.04.002")
    assert LEGACY_LEARNED_004002 in accepted
    assert generator_fingerprint("learned", version="0.04.002") in accepted
    assert matches_generator_fingerprint("learned", LEGACY_LEARNED_004002, version="0.04.002")


@pytest.mark.parametrize("family,version", [
    ("gravity", "0.04.002"),
    ("learned", "0.04.001"),
    ("learned", "0.04.002"),
])
def test_historical_fingerprint_does_not_cross_family_or_producer_version(family, version):
    current = generator_fingerprint(family, version=version)
    assert current in accepted_generator_fingerprints(family, version=version)
    if (family, version) != ("learned", "0.04.002"):
        assert not matches_generator_fingerprint(family, LEGACY_LEARNED_004002, version=version)


def test_unknown_fingerprint_is_rejected():
    assert not matches_generator_fingerprint("learned", "0" * 64, version="0.04.002")
