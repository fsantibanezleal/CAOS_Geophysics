"""Actual local fitted numeric ZIP command; explicit external data/temp roots."""

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parents[1]/'data-pipeline'))
from magnetic_local_paths import configure_scratch, data_output
from magnetic_result_export import export_zip, import_zip
from magnetic_survey_json import canonical


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=('export', 'import'))
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--data-root', required=True)
    parser.add_argument('--temp-root', required=True)
    args = parser.parse_args()
    configure_scratch(args.temp_root)
    output = data_output(args.output, args.data_root)
    if args.operation == 'export':
        result = export_zip(args.input, output)
    else:
        imported = import_zip(args.input, output)
        result = dict(schema='magnetic-numeric-import-receipt-1', generation_sha256=imported['generation_sha256'],
                      raw_original_included=False, online_admitted=False)
    print(canonical(result).decode())


if __name__ == '__main__':
    main()
