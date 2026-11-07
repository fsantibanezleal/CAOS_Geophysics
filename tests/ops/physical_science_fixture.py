"""Actual science fixture generation; telemetry remains explicitly fixture-only."""

import base64
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
sys.path.insert(0,str(ROOT/'data-pipeline'))


def encode(value):
    if type(value) is bytes:
        return {'__fixture_bytes__':base64.b64encode(value).decode()}
    if type(value) is dict:
        return {key:encode(item) for key,item in value.items()}
    return value


def main():
    from tests.numerics.test_physical_producer import packet
    target=Path(sys.argv[1])
    assert target.is_absolute() and not target.is_relative_to(ROOT)
    for parent in (target.parent,*target.parent.parents):
        assert not parent.is_symlink() and not (parent/'.git').exists()
    value=packet.__wrapped__()
    with target.open('x',encoding='utf-8') as stream:
        json.dump(encode(value),stream,sort_keys=True,ensure_ascii=True,allow_nan=False)


if __name__=='__main__':
    main()
