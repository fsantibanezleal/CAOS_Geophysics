"""Ordinary fixed science boundary; direct executable native launch is denied."""

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data-pipeline"))
from waveform_input import bounded_json, sha
from waveform_processing import process_waveform_record
from waveform_evaluation import seal_result


def calculate_bytes(mseed, stationxml, request_bytes):
    request = bounded_json(request_bytes, 65536)
    result = process_waveform_record(mseed, stationxml, request)
    result.metadata["request"]["original_json_bytes"] = len(request_bytes)
    result.metadata["request"]["original_json_sha256"] = sha(request_bytes)
    return result, seal_result(result)


if __name__ == "__main__":
    # No tokens/CLI flags can manufacture native containment or bypass its hold.
    print('{"status":"engine_unavailable","reason":"supervisor_unavailable"}')
    raise SystemExit(4)
