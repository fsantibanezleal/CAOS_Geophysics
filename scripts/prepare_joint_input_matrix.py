"""Prepare the frozen M11 synthetic input matrix without running inversions.

This creates only native development/sealed inputs for intake, custody, and
transport tests. It does not create fitted models, predictions, metrics, or
scientific acceptance evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "data-pipeline"))

import joint_survey_cases as cases  # noqa: E402
import joint_survey_compiled as compiled  # noqa: E402
import joint_survey_evaluation as evaluation  # noqa: E402
from joint_survey_serialization import _external, write_joint_development  # noqa: E402


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_manifest(path: Path, value: dict) -> str:
    payload = (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()
    with path.open("xb") as stream:
        stream.write(payload)
    return hashlib.sha256(payload).hexdigest()


def _source_hashes() -> dict[str, str]:
    return {
        path.relative_to(ROOT).as_posix(): _sha(path)
        for path in (
            ROOT / "data-pipeline" / "joint_survey_cases.py",
            ROOT / "data-pipeline" / "joint_survey_serialization.py",
            ROOT / "data-pipeline" / "joint_survey_evaluation.py",
            ROOT / "scripts" / "prepare_joint_input_matrix.py",
        )
    }


def prepare(output_root: str) -> dict:
    root = _external(output_root)
    if root.exists():
        raise FileExistsError(f"joint input matrix: destination already exists: {root}")
    root.mkdir(mode=0o700, parents=True)

    records = []
    for index in range(24):
        case = cases.make_joint_control(index)
        cell = root / case["case_id"]
        cell.mkdir(mode=0o700)
        problem = compiled.compile_joint_development({
            "schema": "joint-survey-compile-request-1",
            "survey_request": case["survey_request"],
            "development": case["development"],
        })
        sealed = {
            modality + "_" + label: case["sealed"][modality][source]
            for modality in evaluation.MODALITIES
            for source, label in (("rows", "rows"), ("observed", "observed"), ("noise_values", "noise"))
        }
        sealed_manifest = evaluation.write_joint_sealed(str(cell / "sealed"), problem.plan, sealed)
        write_joint_development(str(cell / "development"), {
            "schema": "joint-survey-write-request-1",
            "survey_request": case["survey_request"],
            "development": case["development"],
            "sealed_manifest": sealed_manifest,
            "originals": None,
        })
        members = []
        for role in ("development", "sealed"):
            for path in sorted((cell / role).iterdir()):
                members.append({
                    "path": path.relative_to(root).as_posix(),
                    "byte_count": path.stat().st_size,
                    "sha256": _sha(path),
                })
        records.append({
            "case_id": case["case_id"],
            "family": case["family"],
            "regime": case["regime"],
            "seed": case["seed"],
            "plan_sha256": problem.plan["plan_sha256"],
            "members": members,
            "inverse_completed": False,
            "field_eligible": False,
            "scientific_precision_accepted": False,
        })

    manifest = {
        "schema": "geophysics.joint-native-input-matrix-fixture/v1",
        "provenance": (
            "Fixed make_joint_control cases written by strict native serializers. "
            "Synthetic intake fixture only; no inversion, accuracy claim, or field-data claim."
        ),
        "source_sha256": _source_hashes(),
        "case_count": len(records),
        "member_count": sum(len(row["members"]) for row in records),
        "cases": records,
    }
    manifest_sha256 = _write_manifest(root / "fixture-manifest.json", manifest)
    verify(str(root))
    return {
        "root": str(root),
        "schema": manifest["schema"],
        "case_count": manifest["case_count"],
        "member_count": manifest["member_count"],
        "manifest_sha256": manifest_sha256,
        "scientific_acceptance": False,
    }


def verify(fixture_root: str) -> dict:
    root = _external(fixture_root, existing=True)
    manifest_path = root / "fixture-manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file() or manifest_path.stat().st_size > 8 * 1024 * 1024:
        raise ValueError("joint input matrix: bounded manifest required")
    raw = manifest_path.read_bytes()

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("joint input matrix: duplicate manifest key")
            result[key] = value
        return result

    value = json.loads(raw, object_pairs_hook=pairs, parse_constant=lambda _value: (_ for _ in ()).throw(
        ValueError("joint input matrix: non-finite manifest number")))
    if (type(value) is not dict or value.get("schema") != "geophysics.joint-native-input-matrix-fixture/v1"
            or value.get("source_sha256") != _source_hashes() or value.get("case_count") != 24
            or type(value.get("cases")) is not list or len(value["cases"]) != 24):
        raise ValueError("joint input matrix: schema, source, or case inventory mismatch")
    expected_files = {"fixture-manifest.json"}
    expected_case_ids = {f"joint-control-{index:02d}" for index in range(24)}
    seen_cases = set()
    member_count = 0
    for row in value["cases"]:
        if type(row) is not dict or row.get("case_id") not in expected_case_ids or row["case_id"] in seen_cases:
            raise ValueError("joint input matrix: case identity mismatch")
        seen_cases.add(row["case_id"])
        if row.get("inverse_completed") is not False or row.get("field_eligible") is not False or row.get("scientific_precision_accepted") is not False:
            raise ValueError("joint input matrix: non-claim flags changed")
        members = row.get("members")
        if type(members) is not list or not members:
            raise ValueError("joint input matrix: empty member inventory")
        roles = set()
        for member in members:
            if type(member) is not dict or set(member) != {"path", "byte_count", "sha256"}:
                raise ValueError("joint input matrix: member schema mismatch")
            name = member["path"]
            parts = name.split("/") if type(name) is str else []
            if (len(parts) != 3 or parts[0] != row["case_id"] or parts[1] not in ("development", "sealed")
                    or not parts[2] or parts[2] in (".", "..") or "\\" in parts[2]
                    or name in expected_files or type(member["byte_count"]) is not int or member["byte_count"] <= 0
                    or type(member["sha256"]) is not str or len(member["sha256"]) != 64
                    or any(character not in "0123456789abcdef" for character in member["sha256"])):
                raise ValueError("joint input matrix: member path or receipt invalid")
            target = root.joinpath(*parts)
            if target.is_symlink() or not target.is_file() or not target.resolve(strict=True).is_relative_to(root):
                raise ValueError("joint input matrix: unsafe or missing member")
            if target.stat().st_size != member["byte_count"] or _sha(target) != member["sha256"]:
                raise ValueError("joint input matrix: member bytes changed")
            expected_files.add(name)
            roles.add(parts[1])
            member_count += 1
        if roles != {"development", "sealed"}:
            raise ValueError("joint input matrix: both native roles are required")
        for role, main in (("development", "request.json"), ("sealed", "sealed.json")):
            if f"{row['case_id']}/{role}/{main}" not in {member["path"] for member in members}:
                raise ValueError("joint input matrix: role entry point missing")
    actual_files = {path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file()}
    if actual_files != expected_files or member_count != value.get("member_count"):
        raise ValueError("joint input matrix: unexpected files or member count")
    return {
        "root": str(root),
        "case_count": len(seen_cases),
        "member_count": member_count,
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
        "scientific_acceptance": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    command = parser.add_mutually_exclusive_group(required=True)
    command.add_argument("--output-root", help="New absolute directory outside the repository for generated inputs")
    command.add_argument("--verify-root", help="Verify a generated external input fixture and all member hashes")
    args = parser.parse_args()
    try:
        receipt = prepare(args.output_root) if args.output_root else verify(args.verify_root)
    except (OSError, TypeError, ValueError, RuntimeError) as error:
        parser.exit(2, f"joint input matrix preparation failed: {type(error).__name__}: {error}\n")
    print(json.dumps(receipt, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
