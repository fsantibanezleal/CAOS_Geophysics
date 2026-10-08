"""Fingerprint-bound fail-first local prerequisites, never full-method admission."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import xml.etree.ElementTree as ET

PUBLIC = ("physical_original_optimizer", "physical_original_terminal", "physical_original_quadratic",
          "physical_owned_spd", "physical_reduced_optimizer", "magnetic_original_optimizer")
JOBS = (("firstfold", "tests/numerics/test_magnetic_original_firstfold.py"),
        ("complete-firstfit", "tests/numerics/test_magnetic_original_sparse_firstfit.py"))


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def inventory(scientific_root, public_root, line_root):
    snapshots = {}
    for label, root in (("science", scientific_root), ("public", public_root), ("lines", line_root)):
        for path in sorted((root / "data-pipeline").glob("*.py")):
            if path.is_symlink() or path.is_junction():
                raise ValueError("No linked source inventory")
            snapshots[f"{label}/{path.name}"] = sha(path.read_bytes())
    for _, name in JOBS:
        snapshots["test/" + name] = sha((scientific_root / name).read_bytes())
    for name in ("full_request.py", "generate.py"):
        snapshots["input/" + name] = sha((scientific_root / "tests/fixtures/magnetic_survey" / name).read_bytes())
    if any("public/" + name + ".py" not in snapshots for name in PUBLIC):
        raise ValueError("Complete public original-source closure required")
    return snapshots


def run_gate(*, scientific_root, public_root, line_root, python, output,
             failed_receipt, failed_sha, public_qualification=None, qualification_sha=None, execute=subprocess.run):
    # Explicit external output. No files/engines or subprocess before refusal.
    sys.path.insert(0, str(scientific_root / "data-pipeline"))
    from magnetic_local_paths import external_path
    output = external_path(output)
    predecessor = external_path(failed_receipt).read_bytes()
    if sha(predecessor) != failed_sha:
        raise ValueError("Original failed prerequisite receipt SHA differs")
    failed = json.loads(predecessor)
    if (failed.get("schema") != "magnetic-original-sparse-firstfit-prerequisite-1"
            or failed.get("status") != "failed" or failed.get("reason") != "wall_cap"
            or failed.get("full_matrix_run") is not False):
        raise ValueError("Exact failed original complete-firstfit predecessor required")
    snapshots = inventory(scientific_root, public_root, line_root)
    if all(snapshots["public/" + name + ".py"] == failed["sources"][name] for name in PUBLIC):
        return {"status": "blocked_unchanged_public_failure", "launched": [], "full_matrix_unlocked": False}
    if public_qualification is None or qualification_sha is None:
        return {"status": "blocked_unqualified_nonzero_corrector", "launched": [], "full_matrix_unlocked": False}
    qualified_raw = external_path(public_qualification).read_bytes()
    if sha(qualified_raw) != qualification_sha:
        raise ValueError("Changed public qualification SHA differs")
    qualified = json.loads(qualified_raw)
    expected = dict(schema="magnetic-public-original-nonzero-qualification-1", case="S2-A", quantity="secondary_enu_nT",
        active_cells=528, source_components=864, fit_components=432, epsilon_stages=8,
        caps=dict(wall_s=120, accepted=200, cg_per_direction=200, line_search=20, admitted_bytes=805306368),
        sources={name: snapshots["public/"+name+".py"] for name in PUBLIC}, status="passed")
    if set(qualified) != set(expected) | {"fit_wall_s", "independent_precision"} or any(qualified[k] != v for k,v in expected.items()):
        raise ValueError("Applicable original nonzero complete-firstfit qualification required")
    limits = dict(model_inf_q=1e-6, objective_relative=1e-8, prediction_rms_nT=1e-6, normalized_kkt_inf=1e-7)
    precision = qualified["independent_precision"]
    if (type(qualified["fit_wall_s"]) not in (int,float) or not 0 < qualified["fit_wall_s"] <= 120
            or type(precision) is not dict or set(precision) != set(limits)
            or any(type(precision[k]) not in (int,float) or not math.isfinite(precision[k]) or not 0 <= precision[k] <= limit for k,limit in limits.items())):
        raise ValueError("Original independent precision or same-clock fit cap failed")
    fingerprint = sha(canonical(dict(sources=snapshots, interpreter=str(python.resolve()),
        predecessor_sha256=failed_sha, qualification_sha256=qualification_sha)))
    cache = output / fingerprint
    receipt_path = cache / "receipt.json"
    if cache.exists():
        if not receipt_path.is_file():
            raise ValueError("Incomplete prerequisite cache, no automatic retry")
        stored = json.loads(receipt_path.read_bytes())
        if stored.get("fingerprint") != fingerprint or stored.get("sources") != snapshots:
            raise ValueError("Cached source fingerprint differs")
        for name, digest in stored["outputs"].items():
            path = cache / name
            if ("\\" in name or name.startswith("/") or ".." in name.split("/") or ":" in name
                    or path.is_symlink() or path.is_junction() or not path.is_file()
                    or sha(path.read_bytes()) != digest):
                raise ValueError("Cached prerequisite output differs")
        return stored
    cache.mkdir(mode=0o700, parents=False)
    record = dict(schema="magnetic-original-prerequisite-dag-1", fingerprint=fingerprint,
        sources=snapshots, predecessor_sha256=failed_sha, status="running", launched=[], outputs={},
        full_matrix_unlocked=False, local_prerequisites_passed=False, science_admitted=False)
    env = os.environ.copy()
    env.update(PYTHONPATH=os.pathsep.join(map(str, (scientific_root / "data-pipeline", public_root / "data-pipeline", line_root / "data-pipeline"))),
        PYTHONDONTWRITEBYTECODE="1", TEMP=str(cache), TMP=str(cache), TMPDIR=str(cache),
        NUMBA_CACHE_DIR=str(cache / "numba"), OMP_NUM_THREADS="1", OPENBLAS_NUM_THREADS="1",
        MKL_NUM_THREADS="1", NUMBA_NUM_THREADS="1", BLIS_NUM_THREADS="1")
    try:
        for name, test in JOBS:
            if inventory(scientific_root, public_root, line_root) != snapshots:
                raise ValueError("Source changed after prerequisite planning")
            xml, log = cache / (name + ".xml"), cache / (name + ".log")
            record["launched"].append(name)
            with log.open("xb") as stream:
                result = execute([str(python), "-B", "-m", "pytest", test, "-x", "-q", "-p", "no:cacheprovider",
                    "--basetemp", str(cache / (name + "-files")), "--junitxml", str(xml)],
                    cwd=scientific_root, env=env, stdout=stream, stderr=subprocess.STDOUT, timeout=400., check=False)
            for p in (xml, log):
                if p.is_file(): record["outputs"][p.name] = sha(p.read_bytes())
            for p in sorted((cache / (name + "-files")).rglob("*")):
                if p.is_symlink() or p.is_junction():
                    raise ValueError("Linked prerequisite output is not retained evidence")
                if p.is_file(): record["outputs"][p.relative_to(cache).as_posix()] = sha(p.read_bytes())
            if inventory(scientific_root, public_root, line_root) != snapshots:
                raise ValueError("Source changed during prerequisite execution")
            suites = ET.parse(xml).getroot().iter("testsuite") if xml.is_file() else ()
            counts = {key: 0 for key in ("tests", "failures", "errors", "skipped")}
            for suite in suites:
                for key in counts: counts[key] += int(suite.get(key, "0"))
            if result.returncode != 0 or counts != dict(tests=1, failures=0, errors=0, skipped=0):
                record["status"] = "failed_" + name
                break
        else:
            record.update(status="local_prerequisites_passed", local_prerequisites_passed=True)
    except (OSError, ValueError, subprocess.TimeoutExpired, ET.ParseError) as error:
        record.update(status="failed_gate", error=type(error).__name__)
    finally:
        with receipt_path.open("xb") as stream:
            stream.write(canonical(record)); stream.flush(); os.fsync(stream.fileno())
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("scientific-root", "public-root", "line-root", "python", "output", "failed-receipt"):
        parser.add_argument("--" + name, required=True, type=Path)
    parser.add_argument("--failed-sha", required=True)
    parser.add_argument("--public-qualification", type=Path)
    parser.add_argument("--qualification-sha")
    args = parser.parse_args()
    result = run_gate(**vars(args))
    print(canonical(result).decode())
    return 0 if result.get("local_prerequisites_passed") is True else 2


if __name__ == "__main__":
    raise SystemExit(main())
