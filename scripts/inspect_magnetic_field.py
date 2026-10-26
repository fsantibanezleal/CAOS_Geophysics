"""Inspect complete pinned field acquisition without executing provider code."""

import argparse
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1]/'data-pipeline'))
from magnetic_field_evaluation import inspect_clear_lake
from magnetic_local_paths import external_path
from magnetic_survey_json import canonical


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--original', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    ledger = json.loads((Path(__file__).parents[1]/'data'/'source-ledger.json').read_text())
    record = next(r for r in ledger['sources'] if r['source_id'] == 'clear-lake-author-potentials-v2')
    result = inspect_clear_lake(args.original, record)
    with external_path(args.output).open('xb') as stream:
        stream.write(canonical(result))
        stream.flush()
        os.fsync(stream.fileno())
    print(result['scientific_verdict'])
    return 2 if not result['modelling_eligible'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
