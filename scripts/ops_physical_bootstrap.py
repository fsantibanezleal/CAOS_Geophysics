"""Initialize only named private participation locks; no activation/account/schema."""

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.physical_bootstrap import initialize_private_locks  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--data-root', required=True, type=Path)
    args = parser.parse_args()
    records = initialize_private_locks(args.data_root)
    print(json.dumps(dict(schema='geophysics.physical-lock-initialization/v1', locks=records,
        activation=False, schema_changed=False, accounts_created=False), sort_keys=True))


if __name__ == '__main__':
    main()
