"""New actual CSV supplied-input control, not a repeat of failed nonzero528.

Original public binding/caps/precision are unchanged. Actual null7cell physics
is fitted once; its retained generation is input to separate protected custody
tests. No fabricated complete bundle or field/native-host acceptance.
"""

import csv
import hashlib
import importlib.util
import io
import json
from pathlib import Path

import run_magnetic_survey as cli
from magnetic_original_adapter import binding_for_sources
from magnetic_survey_json import canonical, digest


def test_actual_original_csv_null_control(tmp_path):
    spec = importlib.util.spec_from_file_location("actual_csv_local_control", Path(__file__).with_name("test_magnetic_local_cli.py"))
    control = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(control)
    doc = control.inputs(tmp_path)
    text = io.StringIO(newline="")
    writer = csv.writer(text, lineterminator="\n")
    writer.writerow(["row", "line", "E_m", "N_m", "U_m", "bE", "bN", "bU"])
    for i, row in enumerate(doc["acquisition"]["row_ids"]):
        writer.writerow([row, doc["acquisition"]["group_ids"][i],
            *doc["geometry"]["receivers_m"]["data"][3*i:3*i+3],
            *doc["observations"]["values"]["data"][3*i:3*i+3]])
    original = text.getvalue().encode()
    (tmp_path / "original.csv").write_bytes(original)
    doc["source"]["original_sha256"] = hashlib.sha256(original).hexdigest()
    doc["source"]["original_bytes"] = len(original)
    doc["source"]["citation"] = "Actual authored288-row CSV null control, not acquired field data"
    doc["processing"]["nodes"][0]["input_sha256"] = doc["source"]["original_sha256"]
    sources = cli.source_inventory(original=True)
    binding = binding_for_sources(sources, digest(sources))
    doc["policy"]["optimizer_binding"] = dict(accepted_source=binding.optimizer_source_sha256,
        accepted_export=binding.accepted_export, epoch=binding.runtime_epoch)
    (tmp_path / "request.json").write_bytes(canonical(doc))
    receipt = dict(schema="magnetic-local-binding-1", scope="local_candidate_only",
        review_reference="Actual CSV input-null-control only, not original528/fullmethod/field/host acceptance",
        sources=sources, source_inventory_sha256=digest(sources), runtime_epoch=binding.runtime_epoch, policy=binding.policy)
    (tmp_path / "binding.json").write_bytes(canonical(receipt))
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    code, result = control.run("calibrate", "--request", tmp_path / "request.json", "--original", tmp_path / "original.csv",
        "--output", tmp_path / "generation", "--data-root", tmp_path, "--temp-root", scratch,
        "--binding-receipt", tmp_path / "binding.json", "--allow-candidate-core", "--wall-seconds", "120")
    assert code == 0, result
    assert result["status"] == "complete" and not any(result["claims"].values())
    records = [json.loads(line) for line in (scratch / "optimizer-audit.jsonl").read_bytes().splitlines()]
    assert len(records) >= 49 and all(r["actual_result"]["terminal_audits"][-1]["check"]["passed"] for r in records)
    assert (tmp_path / "original.csv").read_bytes() == original
    (tmp_path / "physical-columns.json").write_bytes(canonical(dict(row_id_column="row", line_id_column="line",
        x_column="E_m", y_column="N_m", z_column="U_m", value_column="bE", quantity="secondary_enu_nT",
        component_columns=dict(E="bE", N="bN", U="bU"))))
