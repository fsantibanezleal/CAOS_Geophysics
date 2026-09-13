import json

from pipeline import run_all


def test_all_cases_are_deterministic_and_manifest_backed(tmp_path):
    first = run_all(seed=7, output_root=tmp_path / "first")
    second = run_all(seed=7, output_root=tmp_path / "second")
    assert len(first) == len(second) == 20
    for entry in first:
        a = json.loads((tmp_path / "first" / "manifests" / f"{entry['case_id']}.json").read_text())
        b = json.loads((tmp_path / "second" / "manifests" / f"{entry['case_id']}.json").read_text())
        assert a["artifact"]["bytes"] == b["artifact"]["bytes"]
        assert a["lane"] == a["gate"]["lane"]
        assert (tmp_path / "first" / a["artifact"]["path"]).exists()
