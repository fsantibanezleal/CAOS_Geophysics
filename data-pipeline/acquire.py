"""Select and verify one raw asset from the reviewed source ledger."""
import argparse
import json
from pathlib import Path
import sys

from sources import SourceError, acquire_source, load_ledger


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--source-id", help="Stable ID from data/source-ledger.json")
    group.add_argument("--list", action="store_true", help="Show the reviewed source allowlist")
    parser.add_argument("--file", type=Path, help="Existing local file for a manual or offline import")
    parser.add_argument("--data-root", type=Path, help="External working-data root; otherwise GEOPHYSICS_LOCAL_DATA_ROOT")
    args = parser.parse_args(argv)
    try:
        if args.list:
            if args.file:
                parser.error("--file requires --source-id")
            print(json.dumps([{key: record[key] for key in
                               ("source_id", "provider_url", "object_url", "acquisition", "format", "rights_decision")}
                              for record in load_ledger().values()], indent=2))
            return 0
        _, _, receipt = acquire_source(args.source_id, local_file=args.file, root=args.data_root)
    except SourceError as error:
        print(f"Acquisition failed: {error}", file=sys.stderr)
        return 2
    print(json.dumps(receipt, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
