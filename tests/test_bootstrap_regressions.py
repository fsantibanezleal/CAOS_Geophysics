"""Adversarial admission and process tests using the production bootstrap helpers."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import re
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_local_bootstrap import ROOT, free_port, present, write
from test_local_bootstrap import fixture_repo as fixture_repo
from test_local_bootstrap import workflow as workflow


def stamp(root, config, module, name=".venv"):
    item = next(row for row in config["environments"] if row["path"] == name)
    write(
        root / name / ".bootstrap-requirements.sha256", module.requirements_digest(root, item["requirements"])
    )


def metadata(root, stage):
    shutil.copyfile(root / "VERSION", stage / "VERSION")
    shutil.copytree(root / "docs/contracts", stage / "docs/contracts", dirs_exist_ok=True)


DIALECT = "https://json-schema.org/draft/2020-12/schema"


def reads_data_selector(copy_data):
    """Whether a copy-data script reads the CAOS_DATA_ROOT selector from its environment (code, not a comment)."""
    code = re.sub(r"/\*.*?\*/|//[^\n]*", "", copy_data.read_text(encoding="utf-8"), flags=re.S)
    return re.search(r"process\.env(?:\.CAOS_DATA_ROOT\b|\[\s*['\"]CAOS_DATA_ROOT['\"]\s*\])", code) is not None


def catalog_ids(root):
    """The row ids of ``docs/contracts/catalog.md`` (a row of 13 or more cells whose first cell is not the header)."""
    ids = set()
    for line in (root / "docs/contracts/catalog.md").read_text(encoding="utf-8").splitlines():
        cells = [part.strip() for part in line.strip().strip("|").split("|")]
        if line.startswith("|") and len(cells) >= 13 and cells[0] != "id" and set(cells[0]) - {"-", ":"}:
            ids.add(cells[0])
    return ids


def seal(module, root, config, stage):
    write(
        stage / "local-generation.json",
        json.dumps(
            {"source": module.source_identity(root, config), "files": module.payload_hashes(stage, config)}
        ),
    )


def test_adversarial_receipt_current_contract_and_recursive_pins(workflow, fixture_repo):
    root, config, env = fixture_repo
    if not (ROOT / "scripts/check_documents.py").is_file():
        pytest.skip("The generic template document validator is not part of this product.")
    write(root / "requirements.txt", "-r data-pipeline/requirements.txt\n-c constraints.txt\n")
    write(root / "data-pipeline/requirements.txt", "-r nested/more.txt\n")
    write(root / "data-pipeline/nested/more.txt", "numpy==2.4.6\n")
    write(root / "constraints.txt", "example==1\n")
    # Actual document validator and schema registry; the catalog mapping is fixture data.
    for name in (
        "scripts/check_documents.py",
        "scripts/check_contracts.py",
        "tests/contracts/contract_schemas.py",
    ):
        write(root / name, (ROOT / name).read_text(encoding="utf-8"))
    write(root / "docs/contracts/api.openapi.json", "{}")
    for name, required in (("lenient", []), ("strict", ["NEW_CONTRACT_FIELD"])):
        # each fixture schema names its own $id and dialect, as the catalog's schemas do: a product registry that admits a
        # schema only at its own $id and dialect admits these too (#89)
        write(
            root / f"docs/contracts/schemas/{name}.schema.json",
            json.dumps({"$schema": DIALECT, "$id": f"{name}.schema.json", "type": "object", "required": required}),
        )
    header = (
        "id",
        "version",
        "kind",
        "schema file",
        "producer",
        "consumer",
        "example",
        "missing-data behavior",
        "producer test",
        "consumer test",
        "model io",
        "provider",
        "documents",
    )
    paths = config["required"]
    rows = ["| " + " | ".join(header) + " |", "| " + " | ".join(["---"] * 13) + " |"]
    for index, name in enumerate(paths):
        cells = [
            f"doc{index}",
            "1",
            "json",
            "docs/contracts/schemas/lenient.schema.json",
            "-",
            "-",
            "-",
            "-",
            "-",
            "-",
            "-",
            "-",
            name,
        ]
        rows.append("| " + " | ".join(cells) + " |")
    catalog = "\n".join(rows) + "\n"
    write(root / "docs/contracts/catalog.md", catalog)
    config["validators"] = [{"script": "scripts/check_documents.py", "args": ["{stage}"]}]
    write(root / "scripts/local/workflow.json", json.dumps(config))
    stage = root.parent / "candidate"
    for name in paths:
        write(stage / name, json.dumps({"engine_version": (root / "VERSION").read_text().strip()}))
    ready = {
        "product_version": (root / "VERSION").read_text().strip(),
        "catalog_sha256": hashlib.sha256(catalog.encode()).hexdigest(),
        # one readiness row per catalog row: the catalog has one row per required path, however many the product declares (#89)
        "contracts": [{"id": f"doc{i}", "state": "available"} for i in range(len(paths))],
    }
    write(stage / "data/derived/readiness.json", json.dumps(ready))
    metadata(root, stage)
    seal(workflow, root, config, stage)
    workflow.validate_stage(root, config, stage, sys.executable, env, receipt=True)
    original_identity = workflow.source_identity(root, config)
    for name, replacement in (
        ("data-pipeline/nested/more.txt", "numpy==2.4.5\n"),
        ("constraints.txt", "example==2\n"),
        ("docs/contracts/catalog.md", catalog.replace("lenient.schema", "strict.schema")),
        (
            "docs/contracts/schemas/strict.schema.json",
            '{"type":"object","required":["SECOND_REQUIRED_FIELD"]}',
        ),
        (
            "scripts/check_documents.py",
            (root / "scripts/check_documents.py").read_text() + "\n# revised admission\n",
        ),
        (
            "tests/contracts/contract_schemas.py",
            (root / "tests/contracts/contract_schemas.py").read_text() + "\n# revised registry\n",
        ),
    ):
        path = root / name
        before = path.read_bytes()
        write(path, replacement)
        assert workflow.source_identity(root, config) != original_identity, name
        with pytest.raises(workflow.Failure, match="fingerprint"):
            workflow.promote(root, config, stage, sys.executable, env)
        assert not (root / "models").exists()
        if name.endswith("catalog.md"):
            with pytest.raises(workflow.Failure, match="metadata|catalog"):
                workflow.validate_stage(root, config, stage, sys.executable, env)
        path.write_bytes(before)
    # Same IDs, new schema mapping: current validator fails old bytes, not just an identity string.
    strict_catalog = catalog.replace("lenient.schema", "strict.schema")
    write(root / "docs/contracts/catalog.md", strict_catalog)
    metadata(root, stage)
    bad = subprocess.run(
        [sys.executable, root / "scripts/check_documents.py", stage],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert bad.returncode == 1 and "NEW_CONTRACT_FIELD" in bad.stdout
    ready["catalog_sha256"] = hashlib.sha256(strict_catalog.encode()).hexdigest()
    write(stage / "data/derived/readiness.json", json.dumps(ready))
    for name in paths:
        value = json.loads((stage / name).read_text())
        value["NEW_CONTRACT_FIELD"] = True
        write(stage / name, json.dumps(value))
    seal(workflow, root, config, stage)
    workflow.promote(root, config, stage, sys.executable, env)
    workflow.check_shipped(root, config)
    write(root / "docs/contracts/catalog.md", strict_catalog + "\nChanged contract notes\n")
    with pytest.raises(workflow.Failure, match="stale admission catalog"):
        workflow.check_shipped(root, config)


def test_adversarial_actual_readiness_inventory(workflow, tmp_path):
    if workflow.settings(ROOT).get("readiness_provider"):
        pytest.skip("The product uses its explicitly guarded inverse-earth readiness provider.")
    # Invoke the real compute API, preserving its genuine missing states. No engine solves.
    code = (
        "import json,sys; from pathlib import Path; from pipeline.core import readiness; "
        "root=Path(sys.argv[1]); stage=Path(sys.argv[2]); "
        "print(json.dumps(readiness.compute(repo_root=root,derived_root=stage/'data',models_dir=stage/'models')))"
    )
    result = subprocess.run(
        [sys.executable, "-c", code, str(ROOT), str(tmp_path)],
        cwd=ROOT / "data-pipeline",
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        check=False,
    )
    assert result.returncode == 0, result.stderr
    ready = json.loads(result.stdout)
    config = workflow.settings(ROOT)
    workflow.check_readiness_inventory(ROOT, config, ready)
    # the inventory is the product's own catalog less its declared exclusions, never a count of the template's or another
    # product's, and never inferred from an optional pipeline module (#89, #102: ChancaDEM has a registry and 12 rows)
    expected = catalog_ids(ROOT) - set(config.get("readiness_excludes", []))
    ids = [row["id"] for row in ready["contracts"]]
    assert len(ids) == len(expected) and set(ids) == expected, (sorted(ids), sorted(expected))
    assert ("readiness" in ids) == ("readiness" in expected)
    for bad_rows in (
        ready["contracts"][:-1],
        ready["contracts"] + [ready["contracts"][0]],
        ready["contracts"] + [{"id": "unknown", "state": "available"}],
    ):
        with pytest.raises(workflow.Failure, match="inventory"):
            workflow.check_readiness_inventory(ROOT, config, {**ready, "contracts": bad_rows})
    with pytest.raises(workflow.Failure, match="stale admission catalog"):
        workflow.check_readiness_inventory(ROOT, config, {**ready, "catalog_sha256": "0" * 64})


def test_adversarial_actual_template_registry(tmp_path):
    bridge = ROOT / "scripts/local/producer_bridge.py"
    if not (ROOT / "data-pipeline/pipeline/registry.py").is_file():
        config = json.loads((ROOT / "scripts/local/workflow.json").read_text())
        assert all("template-validate" not in row.get("args", []) for row in config["validators"])
        return
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import json;from pipeline import registry;print(json.dumps([c.id for c in registry.list_cases()]))",
        ],
        cwd=ROOT / "data-pipeline",
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    ids = json.loads(result.stdout)
    assert ids
    index = tmp_path / "data/derived/manifests/index.json"
    for cases, expected in ((ids, 0), (ids[:-1], 1), (ids + [ids[0]], 1)):
        write(index, json.dumps({"cases": [{"case_id": name} for name in cases]}))
        checked = subprocess.run(
            [sys.executable, bridge, "template-validate", tmp_path],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert checked.returncode == expected, checked.stderr
        if expected:
            assert "Partial case inventory" in checked.stderr


def test_adversarial_rollback_continues_and_preserves_recovery(workflow, fixture_repo, monkeypatch):
    root, config, env = fixture_repo
    present(root, config, workflow)
    originals = {name: (root / name).read_bytes() for name in config["required"]}
    stage = workflow.generate(root, config, env)
    real_replace = os.replace
    restores = []

    def replace(source, target):
        source, target = Path(source), Path(target)
        if ".bootstrap-incoming-" in source.name and target == root / "models":
            raise OSError("original install failure")
        if ".bootstrap-restore-" in source.name:
            restores.append(target)
            if target == root / "models":
                raise OSError("second restore failure")
        return real_replace(source, target)

    monkeypatch.setattr(workflow.os, "replace", replace)
    with pytest.raises(workflow.Failure, match="Rollback incomplete") as raised:
        workflow.promote(root, config, stage, sys.executable, env)
    message = str(raised.value)
    assert "original install failure" in message and "second restore failure" in message
    assert restores == [root / "models", root / "data/derived"]
    assert not (root / "models").exists()
    assert (root / "data/derived/cases/a.json").read_bytes() == originals["data/derived/cases/a.json"]
    for prefix, parent, child in (("models", root, "model.json"), ("derived", root / "data", "cases/a.json")):
        backups = list(parent.glob(f".{prefix}.bootstrap-backup-*"))
        assert len(backups) == 1 and backups[0].name in message
        key = f"models/{child}" if prefix == "models" else f"data/derived/{child}"
        assert (backups[0] / child).read_bytes() == originals[key]


def test_adversarial_dev_python_initialization_admission(workflow, fixture_repo, monkeypatch):
    root, config, env = fixture_repo
    present(root, config, workflow)
    config["frontend_command"] = [sys.executable, "-c", "pass"]
    config["web_port"] = free_port()
    monkeypatch.setattr(workflow, "environment", lambda *_: env)
    prepared = []
    actual_run = workflow.run
    config["frontend_prepare"] = [[sys.executable, "-c", "pass"]]

    def run(*args, **kwargs):
        prepared.append(args)
        return actual_run(*args, **kwargs)

    monkeypatch.setattr(workflow, "run", run)
    with pytest.raises(workflow.Failure, match="initialization fingerprint"):
        workflow.development(root, config)
    assert not prepared
    stamp(root, config, workflow)
    workflow.development(root, config)
    assert len(prepared) == 1
    write(root / "requirements.txt", "example==2\n")
    with pytest.raises(workflow.Failure, match="initialization fingerprint"):
        workflow.development(root, config)
    assert len(prepared) == 1
    stamp(root, config, workflow)
    config["api"].update(active=True, environment=".venv-api")
    config["environments"].append({"path": ".venv-api", "requirements": ["requirements-api.txt"]})
    write(root / "requirements-api.txt", "-r requirements.txt\n")
    write(root / "scripts/local/workflow.json", json.dumps(config))
    with pytest.raises(workflow.Failure, match=r"\.venv-api"):
        workflow.development(root, config)
    assert len(prepared) == 1
    stamp(root, config, workflow, ".venv-api")
    port = free_port()
    config["api"].update(
        port=port, health="/", command=[sys.executable, "-m", "http.server", "{port}", "--bind", "127.0.0.1"]
    )
    workflow.development(root, config)
    assert len(prepared) == 2
    write(root / "requirements-api.txt", "-r requirements.txt\napi-example==2\n")
    with pytest.raises(workflow.Failure, match=r"\.venv-api"):
        workflow.development(root, config)
    assert len(prepared) == 2


def reachable(port, token="owned-child"):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}", timeout=0.2) as reply:
            return reply.read().decode() == token
    except OSError:
        return False


def wait_until(predicate, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(0.05)
    assert predicate(), "bounded fixture condition did not become true"


def test_adversarial_exited_parent_descendant_ownership(workflow, tmp_path):
    child = tmp_path / "http_child.py"
    write(
        child,
        """from http.server import BaseHTTPRequestHandler,HTTPServer
import sys
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  self.send_response(200);self.end_headers();self.wfile.write(sys.argv[2].encode())
 def log_message(self,*args): pass
HTTPServer(("127.0.0.1",int(sys.argv[1])),Handler).serve_forever()
""",
    )
    parent = tmp_path / "launcher.py"
    write(
        parent,
        """import socket,subprocess,sys,time
from pathlib import Path
p=subprocess.Popen([sys.executable,sys.argv[1],sys.argv[2],sys.argv[3]],stdin=subprocess.DEVNULL)
Path("owned-child.pid").write_text(str(p.pid))
for unused in range(100):
 try:
  with socket.create_connection(("127.0.0.1",int(sys.argv[2])),timeout=.1): break
 except OSError: time.sleep(.05)
else: raise SystemExit(7)
""",
    )
    # Hold both reservations together; Windows can reuse a just-released ephemeral port.
    with socket.socket() as first, socket.socket() as second:
        first.bind(("127.0.0.1", 0))
        second.bind(("127.0.0.1", 0))
        port, control_port = first.getsockname()[1], second.getsockname()[1]
    assert port != control_port
    control = subprocess.Popen(
        [sys.executable, child, str(control_port), "control-child"],
        cwd=tmp_path,
        env=os.environ.copy(),
        **workflow.process_group_options(),
    )
    owned = None
    try:
        wait_until(lambda: reachable(control_port, "control-child"))
        owned = subprocess.Popen(
            [sys.executable, parent, child, str(port), "owned-child"],
            cwd=tmp_path,
            env=os.environ.copy(),
            **workflow.process_group_options(),
        )
        wait_until(lambda: owned.poll() is not None)
        assert owned.returncode == 0 and reachable(port), "prove descendant outlived exited parent"
        workflow.stop(owned)
        wait_until(lambda: not reachable(port))
        assert reachable(control_port, "control-child"), "unowned service must survive cleanup"
    finally:
        if owned:
            workflow.stop(owned)
        workflow.stop(control)
        # Failure cleanup uses only this fixture's independently recorded child PID.
        record = tmp_path / "owned-child.pid"
        if record.is_file() and os.name == "nt":
            subprocess.run(
                ["taskkill", "/PID", record.read_text(), "/T", "/F"], capture_output=True, check=False
            )


def directory_alias(alias, destination):
    alias.parent.mkdir(parents=True, exist_ok=True)
    if os.name == "nt":
        result = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(alias), str(destination)],
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, result.stderr
    else:
        alias.symlink_to(destination, target_is_directory=True)


def test_adversarial_external_runtime_alias_and_cleanup(workflow, tmp_path, monkeypatch):
    root, outside = tmp_path / "repo", tmp_path / "outside-runtime"
    outside.mkdir()
    name = ".venv"
    config = {
        "environments": [{"path": name, "requirements": ["requirements.txt"]}],
        "generation_environments": [name],
    }
    write(root / "scripts/local/workflow.json", json.dumps(config))
    interpreter = outside / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    write(interpreter, "interpreter placeholder; never executed")
    write(root / "requirements.txt", "example==1\n")
    directory_alias(root / name, outside)
    try:
        assert workflow.venv_python(root, name).resolve() == interpreter.resolve()
        assert workflow.generation_python(root, config).resolve() == interpreter.resolve()
        # Initialization uses the declared alias too; fake pip never executes the placeholder.
        config.update(required=[], api={"active": False})
        write(root / ".env.example", "MODE=literal\n")
        calls = []
        monkeypatch.setattr(workflow, "prerequisites", lambda *_: None)
        monkeypatch.setattr(workflow, "install_frontend", lambda *_: None)
        monkeypatch.setattr(workflow, "check_shipped", lambda *_: None)
        monkeypatch.setattr(workflow, "run", lambda command, *args, **kw: calls.append(command))
        workflow.initialize(root, config)
        assert len(calls) == 1 and "pip" in calls[0]
        assert Path(calls[0][0]).resolve() == interpreter.resolve()
        assert (
            outside / ".bootstrap-requirements.sha256"
        ).read_text().strip() == workflow.requirements_digest(root, ["requirements.txt"])
        workflow.initialize(root, config)
        assert len(calls) == 1
        with pytest.raises(workflow.Failure, match="escapes"):
            workflow.relative(root, name)
        with pytest.raises(workflow.Failure, match="Undeclared"):
            workflow.environment_directory(root, "../outside-runtime")
        interpreter.unlink()
        with pytest.raises(workflow.Failure, match="Missing interpreter.*declared environment"):
            workflow.generation_python(root, config)
    finally:
        if os.name == "nt":
            os.rmdir(root / name)
        else:
            (root / name).unlink()
    reserved = root / ".models.bootstrap-backup-owned"
    write(outside / "sentinel", "keep")
    directory_alias(reserved, outside)
    calls = []
    original = shutil.rmtree
    monkeypatch.setattr(workflow.shutil, "rmtree", lambda *args: calls.append(args))
    try:
        with pytest.raises(workflow.Failure, match="symlink/junction"):
            workflow.remove_owned(reserved, root)
        assert not calls and (outside / "sentinel").read_text() == "keep"
    finally:
        if os.name == "nt":
            os.rmdir(reserved)
        else:
            reserved.unlink()
    monkeypatch.setattr(workflow.shutil, "rmtree", original)
    ordinary = root / ".models.bootstrap-incoming-owned"
    write(ordinary / "file", "remove only this")
    workflow.remove_owned(ordinary, root)
    assert not ordinary.exists() and (outside / "sentinel").exists()
    with pytest.raises(workflow.Failure, match="reserved"):
        workflow.remove_owned(outside, root)


def test_adversarial_tracked_shell_modes(tmp_path, monkeypatch):
    if not (ROOT / "scripts/check_base_integrity.py").is_file():
        pytest.skip("Template base-integrity checker is not part of this product.")
    spec = importlib.util.spec_from_file_location(
        "bootstrap_integrity", ROOT / "scripts/check_base_integrity.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # NUL-delimited actual Git index syntax, including spaces in paths.
    def index(mode):
        return SimpleNamespace(
            stdout=f"{mode} abc 0\tscripts/local/00 install.sh\x00100644 def 0\tREADME.md\0".encode()
        )

    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kw: index("100755"))
    assert module.nonexecutable_shells(tmp_path) == []
    monkeypatch.setattr(module.subprocess, "run", lambda *args, **kw: index("100644"))
    assert module.nonexecutable_shells(tmp_path) == ["scripts/local/00 install.sh"]
    for mode, expected in (("100755", 0), ("100644", 1)):

        def git(command, **kwargs):
            if "--stage" in command:
                return index(mode)
            if "grep" in command:
                return SimpleNamespace(returncode=1, stdout=b"")
            return SimpleNamespace(stdout=b"scripts/local/00 install.sh\x00README.md\x00")

        monkeypatch.setattr(module.subprocess, "run", git)
        assert module.main(["check_base_integrity.py", str(tmp_path)]) == expected


def test_adversarial_locked_node_engines(workflow, tmp_path, monkeypatch, capsys):
    for name in ("package.json", "package-lock.json"):
        write(tmp_path / "frontend" / name, (ROOT / "frontend" / name).read_text())
    declared = json.loads((ROOT / "frontend/package.json").read_text())["engines"]["node"]
    assert declared == "^22.12.0 || ^24.0.0 || >=26.0.0"
    for version, accepted in (
        ((22, 0, 0), False),
        ((22, 11, 9), False),
        ((22, 12, 0), True),
        ((23, 0, 0), False),
        ((24, 14, 1), True),
        ((25, 0, 0), False),
        ((26, 0, 0), True),
        ((28, 1, 0), True),
    ):
        assert workflow.compatible_node(tmp_path, version) is accepted
        calls = []

        def run(command, *args, **kwargs):
            calls.append(command)
            return (
                "v" + ".".join(map(str, version))
                if command[0] == "node"
                else "git version 2.50.0"
                if command[0] == "git"
                else "Python 3.12.10"
            )

        monkeypatch.setattr(workflow, "run", run)
        if accepted:
            workflow.prerequisites(tmp_path)
        else:
            with pytest.raises(workflow.Failure, match="Repair with"):
                workflow.prerequisites(tmp_path)
            assert declared in capsys.readouterr().err
        assert len(calls) == 3 and all(command[-1] == "--version" for command in calls)
    lock = json.loads((tmp_path / "frontend/package-lock.json").read_text())
    lock["packages"][""]["engines"]["node"] = ">=22"
    write(tmp_path / "frontend/package-lock.json", json.dumps(lock))
    with pytest.raises(workflow.Failure, match="package and lock"):
        workflow.compatible_node(tmp_path, (24, 14, 1))


def test_adversarial_real_product_generation_admission(workflow):
    if (ROOT / ".template-source").is_file():
        pytest.skip("The template example has a separate actual five-case generation control")
    config = workflow.settings(ROOT)
    ready = json.loads((ROOT / "data/derived/readiness.json").read_text(encoding="utf-8"))
    workflow.check_readiness_inventory(ROOT, config, ready)
    workflow.check_readiness_states(ROOT, config, ready, ROOT)
    if config.get("readiness_provider"):
        catalog = json.loads((ROOT / "data/derived/v2/catalog.json").read_text(encoding="utf-8"))
        methods = sum(len(variant.get("methods", {}))
                      for case in catalog["cases"] for variant in case["variants"])
        assert ready["schema"] == "inverse-earth.readiness/v1"
        assert ready["counts"] == {"cases": 20, "variants": 120, "method_results": methods}
        assert ready["artifacts"]["present"] == 120 and not ready["artifacts"]["missing"]
        assert workflow.payload_hashes(ROOT, config)
        return
    available = next(row["id"] for row in ready["contracts"] if row["state"] == "available")
    for state in ("missing", None, "dormant", "partial"):
        bad = json.loads(json.dumps(ready))
        next(row for row in bad["contracts"] if row["id"] == available)["state"] = state
        with pytest.raises(workflow.Failure, match="Partial readiness"):
            workflow.check_readiness_states(ROOT, config, bad, ROOT)
    declared = config.get("readiness_exceptions", {})
    assert all(any(row["id"] == name and row["state"] == state for row in ready["contracts"])
               for name, state in declared.items())
    assert all((ROOT / name).is_file() for name in config.get("stage_inputs", []))


TEMPLATE_ONLY = pytest.mark.skipif(not (ROOT / ".template-source").is_file(),
                                   reason="This integration control requires the template's actual five-case sources")


@TEMPLATE_ONLY
def test_adversarial_real_template_generation_admission(workflow, tmp_path, monkeypatch):
    config = workflow.settings(ROOT)
    runtime = (ROOT / config["primary_environment"]).resolve(strict=True)
    # Keep this real-template integration test independent of the developer's
    # shell/.env while preserving the same external-runtime containment policy.
    # The declared alias resolves to <CAOS_VENVS_ROOT>/<namespace>/<runtime>.
    monkeypatch.setenv("CAOS_VENVS_ROOT", str(runtime.parents[1]))
    python = workflow.venv_python(ROOT, config["primary_environment"])
    root = tmp_path / "real template sources with spaces"
    # Production sources and authored inputs, unchanged; no fixture producer/validator substitutes.
    for directory in ("data-pipeline", "docs/contracts", "scripts/local", "tests/contracts"):
        shutil.copytree(
            ROOT / directory, root / directory, ignore=shutil.ignore_patterns("__pycache__", "*.pyc")
        )
    for source in [
        ROOT / "VERSION",
        ROOT / "product.json",
        *ROOT.glob("requirements*.txt"),
        *ROOT.glob("scripts/check_*.py"),
        ROOT / "data/examples/params.csv",
    ]:
        if source.is_file():
            target = root / source.relative_to(ROOT)
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
    # Reuse the already pinned installed environment; no new venv or install.
    monkeypatch.setattr(workflow, "generation_python", lambda *_: python)

    def forbidden(*args, **kwargs):
        raise AssertionError("sandbox regression must never promote")

    monkeypatch.setattr(workflow, "promote", forbidden)
    env = {
        **os.environ,
        "CAOS_TEMP_ROOT": str(tmp_path / "external generation"),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    stage = workflow.generate(root, config, env)
    assert not (root / "data/derived").exists() and not (root / "models").exists()
    source = root / "data/examples/params.csv"
    original = source.read_bytes()
    assert original == (ROOT / "data/examples/params.csv").read_bytes()
    assert (stage / "data/examples/params.csv").read_bytes() == original
    ready_path = stage / "data/derived/readiness.json"
    ready_bytes = ready_path.read_bytes()
    ready = json.loads(ready_bytes)
    rows = {row["id"]: row for row in ready["contracts"]}
    assert len(rows) == 6
    assert rows["params-record"]["state"] == "partial"
    assert rows["params-record"]["missing"] == ["bad_i0_gt_N", "bad_negbeta"]
    assert "2 of 4" in rows["params-record"]["reason"]["en"]
    assert rows["api"]["state"] == "missing" and "dormant" in rows["api"]["reason"]["en"]
    assert all(
        rows[name]["state"] == "available"
        for name in ("case-index", "case-manifest", "trace", "surrogate-model")
    )
    index = json.loads((stage / "data/derived/manifests/index.json").read_text())
    assert len(index["cases"]) == 5
    workflow.validate_stage(root, config, stage, python, env, receipt=True)

    assert ready_path.read_bytes() == ready_bytes, "admission must never rewrite the generated states"
    with pytest.raises(workflow.Failure, match="require the actual"):
        workflow.check_readiness_states(root, {**config, "readiness_check": None}, ready, stage)

    # Exercise the same policy on the shipped-data path in an external checkout, never promotion.
    for name in config["promote"]:
        shutil.copytree(stage / name, root / name)
    blocked = subprocess.run(
        [python, root / "scripts/local/producer_bridge.py", "template-finalize", root],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert blocked.returncode != 0 and "external prepared stage" in blocked.stderr
    workflow.check_shipped(root, config)
    assert ready_path.read_bytes() == ready_bytes

    def finalize(view):
        workflow.run(
            [python, root / "scripts/local/producer_bridge.py", "template-finalize", view], root, env
        )

    # A producer-computed partial artifact/model state is still incomplete, even though params may be partial.
    index = workflow.json_read(stage / "data/derived/manifests/index.json")
    manifest_name = "data/derived/" + index["cases"][0]["manifest_path"]
    trace_name = next(
        path.relative_to(stage).as_posix() for path in (stage / "data/derived").rglob("trace.json")
    )
    for name in ("models/surrogate.json", manifest_name, trace_name):
        path = stage / name
        saved = path.read_bytes()
        path.unlink()
        finalize(stage)
        with pytest.raises(workflow.Failure):
            workflow.validate_stage(root, config, stage, python, env)
        path.write_bytes(saved)
        ready_path.write_bytes(ready_bytes)

    # Fresh matching readiness cannot hide a missing registry case in either admission path.
    for view in (stage, root):
        path = view / "data/derived/manifests/index.json"
        saved = path.read_bytes()
        changed = json.loads(saved)
        changed["cases"].pop()
        write(path, json.dumps(changed))
        if view == stage:
            finalize(view)
            with pytest.raises(workflow.Failure):
                workflow.validate_stage(root, config, stage, python, env)
        else:
            # The actual existing guard's compute/write API; no source or canonical data changes.
            code = (
                "import sys;from pathlib import Path;from pipeline.core import readiness;"
                "r=Path(sys.argv[1]);readiness.write(r/'data/derived',readiness.compute("
                "repo_root=r,derived_root=r/'data/derived',models_dir=r/'models'))"
            )
            workflow.run([python, "-B", "-c", code, view], root / "data-pipeline", env)
            with pytest.raises(workflow.Failure):
                workflow.check_shipped(root, config)
        path.write_bytes(saved)
        (view / "data/derived/readiness.json").write_bytes(ready_bytes)

    for rid, key, value in (
        ("api", "state", "available"),
        ("params-record", "missing", []),
        ("params-record", "state", "missing"),
        ("trace", "state", "missing"),
    ):
        changed = json.loads(ready_bytes)
        next(row for row in changed["contracts"] if row["id"] == rid)[key] = value
        write(ready_path, json.dumps(changed))
        with pytest.raises(workflow.Failure):
            workflow.validate_stage(root, config, stage, python, env)
        write(root / "data/derived/readiness.json", json.dumps(changed))
        with pytest.raises(workflow.Failure):
            workflow.check_shipped(root, config)
        ready_path.write_bytes(ready_bytes)
        (root / "data/derived/readiness.json").write_bytes(ready_bytes)

    staged_source = stage / "data/examples/params.csv"
    staged_source.write_bytes(original + b"\n")
    with pytest.raises(workflow.Failure, match="authored|metadata"):
        workflow.validate_stage(root, config, stage, python, env)
    staged_source.write_bytes(original)
    original_identity = workflow.source_identity(root, config)
    source.write_bytes(original + b"\n")
    assert workflow.source_identity(root, config) != original_identity
    with pytest.raises(workflow.Failure, match="fingerprint"):
        workflow.validate_stage(root, config, stage, python, env, receipt=True)
    source.write_bytes(original)
    source.unlink()
    with pytest.raises(workflow.Failure, match="authored"):
        workflow.generate(root, config, env)
    source.write_bytes(original)
    workflow.validate_stage(root, config, stage, python, env, receipt=True)


def test_adversarial_frontend_environment_isolation(workflow, fixture_repo, monkeypatch):
    root, config, _ = fixture_repo
    present(root, config, workflow)
    stamp(root, config, workflow)
    version = (root / "VERSION").read_text().strip()
    write(
        root / "data/derived/manifests/index.json",
        json.dumps(
            {"engine_version": version, "cases": [{"case_id": "a", "manifest_path": "manifests/a.json"}]}
        ),
    )
    write(root / "data/derived/manifests/a.json", json.dumps({"artifact": {"path": "cases/a.json"}}))
    for name in ("copy-data.mjs", "declared.mjs"):
        target = root / "frontend/scripts" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / "frontend/scripts" / name, target)
    raw = root.parent / "global raw store"
    raw.mkdir()
    stores = {
        "CAOS_DATA_ROOT": str(raw),
        "CAOS_MODELS_ROOT": str(root.parent / "global models"),
        "CAOS_TEMP_ROOT": str(root.parent / "global scratch"),
    }
    for key, value in stores.items():
        monkeypatch.setenv(key, value)
    baseline = workflow.environment(root)
    producer = root / "producer.py"
    capture = (
        "import os,json\nfrom pathlib import Path\n"
        "(Path(os.environ['CAOS_MODELS_ROOT']).parent/'generation-env.json').write_text("
        "json.dumps({k:os.environ.get(k) for k in "
        "('CAOS_DATA_ROOT','CAOS_MODELS_ROOT','CAOS_TEMP_ROOT')}))\n"
    )
    write(producer, capture + producer.read_text())
    with socket.socket() as api_reservation, socket.socket() as web_reservation:
        api_reservation.bind(("127.0.0.1", 0))
        web_reservation.bind(("127.0.0.1", 0))
        api_port = api_reservation.getsockname()[1]
        config["web_port"] = web_reservation.getsockname()[1]
    write(
        root / "api.py",
        """import json,os,sys
from http.server import BaseHTTPRequestHandler,HTTPServer
class Handler(BaseHTTPRequestHandler):
 def do_GET(self):
  body=json.dumps({k:os.environ.get(k) for k in
   ('CAOS_DATA_ROOT','CAOS_MODELS_ROOT','CAOS_TEMP_ROOT')}).encode()
  self.send_response(200);self.end_headers();self.wfile.write(body)
 def log_message(self,*args): pass
HTTPServer(('127.0.0.1',int(sys.argv[1])),Handler).serve_forever()
""",
    )
    write(
        root / "frontend/frontend-env.py",
        """import json,os,sys,urllib.request
from pathlib import Path
api=json.loads(urllib.request.urlopen('http://127.0.0.1:'+sys.argv[1]+'/health').read())
front={k:os.environ.get(k) for k in ('CAOS_DATA_ROOT','CAOS_MODELS_ROOT','CAOS_TEMP_ROOT')}
Path('frontend-env.json').write_text(json.dumps({'frontend':front,'api':api}))
""",
    )
    overlay = {"CAOS_DATA_ROOT": "{root}/data/derived"}
    config.update(
        frontend_environment=overlay,
        frontend_prepare=[["node", "scripts/copy-data.mjs"]],
        frontend_command=["{python}", "frontend-env.py", "{port}"],
    )
    config["api"].update(
        active=True, port=api_port, health="/health", command=["{python}", "api.py", "{port}"]
    )
    write(root / "scripts/local/workflow.json", json.dumps(config))
    stage = workflow.generate(root, config, baseline)
    generated = json.loads((stage / "generation-env.json").read_text())
    assert generated["CAOS_DATA_ROOT"] == stores["CAOS_DATA_ROOT"]
    assert generated["CAOS_TEMP_ROOT"] == stores["CAOS_TEMP_ROOT"]
    assert Path(generated["CAOS_MODELS_ROOT"]) == stage / "checkpoints"
    assert baseline == workflow.environment(root), "generation must not mutate caller storage settings"

    workflow.development(root, config)
    recorded = root / "frontend/frontend-env.json"
    observed = json.loads(recorded.read_text())
    assert Path(observed["frontend"]["CAOS_DATA_ROOT"]).resolve() == (root / "data/derived").resolve()
    assert observed["api"] == stores
    assert all(observed["frontend"][key] == stores[key] for key in ("CAOS_MODELS_ROOT", "CAOS_TEMP_ROOT"))
    assert (root / "frontend/public/data/cases/a.json").read_bytes() == (
        root / "data/derived/cases/a.json"
    ).read_bytes()
    assert baseline == workflow.environment(root)
    # a product that declares the overlay declares this one; a product without it is still tested on the fixture's (#89)
    declared = workflow.settings(ROOT).get("frontend_environment")
    assert declared is None or declared == overlay, declared

    # Without the opt-in, the actual consumer keeps its own behavior: one that reads the global selector fails on the empty
    # global store; one that reads only its own bake (CAOS_Contraste's copy-data.mjs) is untouched by the selector (#89).
    config.pop("frontend_environment")
    recorded.unlink()
    if reads_data_selector(root / "frontend/scripts/copy-data.mjs"):
        with pytest.raises(workflow.Failure, match="Command failed"):
            workflow.development(root, config)
        assert not recorded.exists()
        with pytest.raises(OSError):
            urllib.request.urlopen(f"http://127.0.0.1:{api_port}/health", timeout=0.2)
    else:
        workflow.development(root, config)
        assert (root / "frontend/public/data/cases/a.json").read_bytes() == (root / "data/derived/cases/a.json").read_bytes()
    assert baseline == workflow.environment(root)

    # With no explicit global selector and no overlay, copy-data's existing local default still works.
    monkeypatch.delenv("CAOS_DATA_ROOT")
    workflow.development(root, config)
    observed = json.loads(recorded.read_text())
    assert observed["frontend"]["CAOS_DATA_ROOT"] is None and observed["api"]["CAOS_DATA_ROOT"] is None
    for key in ("CAOS_MODELS_ROOT", "CAOS_TEMP_ROOT"):
        assert observed["frontend"][key] == observed["api"][key] == stores[key]


# ---- #89 / #102: the three regression tests above, run against a planted product (no template identity, its own counts)

def planted_product(base, extra_rows=6, copy_data=None):
    """A product made from this base: its pipeline, contracts and workflow, no .template-source, and a catalog with
    ``extra_rows`` more rows than this repository's (ChancaDEM: a registry and 12 readiness rows)."""
    product = base / "planted product"
    for directory in ("data-pipeline", "docs/contracts", "scripts/local", "frontend/scripts"):
        shutil.copytree(ROOT / directory, product / directory,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "node_modules"))
    shutil.copyfile(ROOT / "VERSION", product / "VERSION")
    catalog = product / "docs/contracts/catalog.md"
    lines = catalog.read_text(encoding="utf-8").splitlines()
    first = next(i for i, line in enumerate(lines) if line.startswith("|") and len(line.strip("|").split("|")) >= 13
                 and line.split("|")[1].strip() not in ("id", "") and set(line.split("|")[1].strip()) - {"-", ":"})
    cells = lines[first].split("|")
    for n in range(extra_rows):
        row = list(cells)
        row[1] = f" planted-{n} "
        lines.insert(first + 1 + n, "|".join(row))
    catalog.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if copy_data is not None:
        (product / "frontend/scripts/copy-data.mjs").write_text(copy_data, encoding="utf-8")
    config = json.loads((product / "scripts/local/workflow.json").read_text(encoding="utf-8"))
    config.pop("frontend_environment", None)
    (product / "scripts/local/workflow.json").write_text(json.dumps(config), encoding="utf-8")
    assert not (product / ".template-source").exists()
    return product


def test_adversarial_inventory_count_comes_from_the_products_catalog(workflow, tmp_path, monkeypatch):
    if workflow.settings(ROOT).get("readiness_provider"):
        pytest.skip("The product readiness document is catalog-backed, not a template contract inventory.")
    product = planted_product(tmp_path)
    expected = catalog_ids(product) - set(workflow.settings(product).get("readiness_excludes", []))
    assert len(expected) == len(catalog_ids(ROOT) - set(workflow.settings(ROOT).get("readiness_excludes", []))) + 6
    monkeypatch.setattr(sys.modules[__name__], "ROOT", product)
    test_adversarial_actual_readiness_inventory(workflow, tmp_path / "derived")


def test_adversarial_receipt_follows_the_number_of_required_paths(workflow, fixture_repo):
    root, config, env = fixture_repo
    config["required"] = [*config["required"], "data/derived/cases/b.json"]
    test_adversarial_receipt_current_contract_and_recursive_pins(workflow, (root, config, env))
    for schema in sorted((root / "docs/contracts/schemas").glob("*.schema.json")):
        doc = json.loads(schema.read_text(encoding="utf-8"))
        assert doc.get("$id") == schema.name and doc.get("$schema") == DIALECT, (schema.name, doc)


COPY_OWN_BAKE = """// a consumer that reads only its own bake, as CAOS_Contraste's does
import { cpSync, mkdirSync, rmSync } from 'node:fs';
rmSync('public/data', { recursive: true, force: true });
mkdirSync('public', { recursive: true });
cpSync('../data/derived', 'public/data', { recursive: true });
"""


def test_adversarial_frontend_isolation_for_a_consumer_of_its_own_bake(workflow, fixture_repo, monkeypatch, tmp_path):
    product = planted_product(tmp_path, extra_rows=0, copy_data=COPY_OWN_BAKE)
    assert not reads_data_selector(product / "frontend/scripts/copy-data.mjs")
    assert reads_data_selector(ROOT / "frontend/scripts/copy-data.mjs") or "CAOS_DATA_ROOT" not in (
        ROOT / "frontend/scripts/copy-data.mjs").read_text(encoding="utf-8")
    monkeypatch.setattr(sys.modules[__name__], "ROOT", product)
    test_adversarial_frontend_environment_isolation(workflow, fixture_repo, monkeypatch)


# ---- BD-10: the readiness checker runs in the generation environment, not in the bootstrap interpreter

def generation_only_environment(base):
    """A real, empty venv (no pip) whose site-packages holds one module the interpreter running the tests lacks: a stand-in
    for a generation environment with numpy or jsonschema that the bootstrap interpreter does not have."""
    import venv

    env = base / "generation env"
    venv.EnvBuilder(with_pip=False).create(env)
    python = next(p for p in (env / "Scripts" / "python.exe", env / "bin" / "python") if p.is_file())
    site = subprocess.run([str(python), "-c", "import sysconfig;print(sysconfig.get_paths()['purelib'])"],
                          capture_output=True, text=True, check=True).stdout.strip()
    write(Path(site) / "generation_only_dependency.py", "VALUE = 1\n")
    return python


def provider_product(root):
    """A product whose declared provider imports a package of its generation environment only."""
    write(root / "scripts/check_readiness.py", (ROOT / "scripts/check_readiness.py").read_text(encoding="utf-8"))
    write(root / "scripts/local/provider.py",
          "import generation_only_dependency\n\ndef validate(root):\n    return generation_only_dependency.VALUE == 1\n")
    return {"readiness_provider": "scripts/local/provider.py", "readiness_check": "scripts/check_readiness.py",
            "generation_environments": [".venv-pipeline"]}


def test_adversarial_a_provider_with_generation_packages_is_admitted_by_the_bootstrap(workflow, tmp_path, monkeypatch):
    import importlib.util as util

    assert util.find_spec("generation_only_dependency") is None, "the bootstrap interpreter must lack the planted module"
    root = tmp_path / "product"
    config = provider_product(root)
    write(root / "scripts/local/workflow.json", json.dumps(config))
    python = generation_only_environment(tmp_path)
    monkeypatch.setattr(workflow, "venv_python", lambda *_: python)
    ready = {"contracts": [{"id": "a", "state": "available"}]}
    workflow.check_readiness_states(root, config, ready, root)          # the generation interpreter resolved by the helper
    workflow.check_readiness_states(root, config, ready, root, python)  # the interpreter a stage admission passes
    # the bootstrap interpreter alone cannot run this provider: the guard is not stdlib-only
    bootstrap = subprocess.run([sys.executable, "-B", str(root / "scripts/check_readiness.py"), str(root)], capture_output=True,
                               text=True, cwd=root)
    assert bootstrap.returncode == 1 and "generation_only_dependency" in bootstrap.stdout, bootstrap.stdout
    # and a provider that fails in the generation environment still refuses
    write(root / "scripts/local/provider.py", "import generation_only_dependency\n\ndef validate(root):\n    return False\n")
    with pytest.raises(workflow.Failure, match="Command failed"):
        workflow.check_readiness_states(root, config, ready, root)
