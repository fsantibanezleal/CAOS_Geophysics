"""Actual trusted-positive science/export; not installed resource qualification."""

import copy
import json
from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from waveform_input import WaveformInputError, iter_record_ledger, pack_record_ledger, scan_miniseed, sha
from waveform_processing import WaveformResult, process_waveform_record
from waveform_evaluation import seal_result, _sealed_metadata
from tests.data.test_waveform_input import inventory, request, source
from tests.data.test_waveform_record_ledger import with_intervals


def test_actual_calculation_seal_and_export_reopen(tmp_path):
    # Imports need the exact previously qualified scientific dependency versions.
    from waveform_m08_export import plan_export, write_export, verify_export
    from waveform_m08_files import create_output

    raw = source()
    result = process_waveform_record(raw, inventory(), request())
    assert result.metadata["status"] == "computed"
    assert result.metadata["channels"][0]["records"]["schema"] == "caos.waveform-record-ledger/v1"
    assert list(iter_record_ledger(result.metadata["channels"][0]["records"])) == with_intervals(
        scan_miniseed(raw, request())
    )
    sealed = seal_result(result)
    assert len(sealed.metadata_bytes) <= 2097152
    plan = plan_export(result, sealed)
    with create_output(tmp_path / "compact", trusted_parent=tmp_path) as directory:
        write_export(plan, directory)
        assert verify_export(directory) == sealed


def test_historical_list_seal_is_not_rewritten(tmp_path):
    from waveform_m08_export import plan_export, write_export, verify_export
    from waveform_m08_files import create_output

    result = process_waveform_record(source(), inventory(), request())
    metadata = copy.deepcopy(result.metadata)
    for channel in metadata["channels"]:
        channel["records"] = list(iter_record_ledger(channel["records"]))
    before = copy.deepcopy(metadata)
    historical = WaveformResult(metadata, result.arrays)
    sealed = seal_result(historical)
    assert json.loads(sealed.metadata_bytes)["channels"][0]["records"] == before["channels"][0]["records"]
    assert metadata == before and sha(sealed.metadata_bytes) == sealed.calculation_sha256
    plan = plan_export(historical, sealed)
    with create_output(tmp_path / "historical", trusted_parent=tmp_path) as directory:
        write_export(plan, directory)
        assert verify_export(directory) == sealed
    assert metadata == before and type(metadata["channels"][0]["records"]) is list


@pytest.mark.parametrize("change", ["channel", "nslc", "aggregate_records"])
def test_seal_rejects_compact_relation_or_station_record_excess(change):
    metadata = copy.deepcopy(process_waveform_record(source(), inventory(), request()).metadata)
    channel = metadata["channels"][0]
    rows = list(iter_record_ledger(channel["records"]))
    if change == "channel":
        for row in rows: row["channel_index"] = 1
        channel["records"] = pack_record_ledger(rows)
    elif change == "nslc":
        for row in rows: row["nslc"][3] = "BHN"
        channel["records"] = pack_record_ledger(rows)
    else:
        # All three channels individually admitted, but total4098 records must
        # still fail even though the compact metadata fits2MiB.
        one = rows[0]
        expanded = []
        for i in range(1366):
            row = copy.deepcopy(one)
            row["npts"] = 1
            row["end_exclusive_us"] = row["start_us"] + 10000
            row["sample_interval"] = {"start": i, "stop": i + 1}
            expanded.append(row)
        metadata["channels"] = []
        req = metadata["request"]["submitted"]
        names = ("BHZ", "BHN", "BHE")
        req["channels"] = [{**req["channels"][0], "channel": name} for name in names]
        req["adc_rails"] *= 3
        from waveform_input import scientific_identity
        metadata["request"]["scientific_sha256"] = scientific_identity(req)
        for i in range(3):
            new = copy.deepcopy(channel)
            new["channel_index"] = i
            new["nslc"][3] = names[i]
            current = copy.deepcopy(expanded)
            for row in current:
                row["channel_index"] = i
                row["nslc"][3] = names[i]
            new["records"] = pack_record_ledger(current)
            metadata["channels"].append(new)
    with pytest.raises(WaveformInputError) as error:
        _sealed_metadata(metadata)
    assert error.value.code == ("waveform_limit" if change == "aggregate_records" else "waveform_contract")
