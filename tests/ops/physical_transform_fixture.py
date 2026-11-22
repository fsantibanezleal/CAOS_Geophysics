"""Original pass/non-pass science fixture producer. Telemetry is fixture-only."""

import base64
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT), str(ROOT/'data-pipeline')]
from tests.numerics.test_physical_transform_producer import transform_packet


def encoded(value):
    if type(value) is bytes:
        return {'__fixture_bytes__':base64.b64encode(value).decode()}
    if type(value) is dict:
        return {key:encoded(item) for key,item in value.items()}
    return value


if __name__ == '__main__':
    target = Path(sys.argv[1])
    assert target.is_absolute() and not target.exists() and not target.is_relative_to(ROOT)
    packets = {}
    for non_pass in (False, True):
        correction, transform = transform_packet(non_pass, with_parent=True)
        packets[str(non_pass)] = dict(correction=encoded(correction), transform=encoded(transform))
    with target.open('xb') as output:
        output.write(json.dumps(packets, sort_keys=True, separators=(',',':'), allow_nan=False).encode())
