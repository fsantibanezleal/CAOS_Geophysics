"""Execute the bounded local M04 magnetic-survey workflow.

The request carries explicit physical metadata and observations; --original
binds those values to the caller's unchanged source file. No provider download,
field correction, optimizer substitution, or acceptance claim is performed.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
from pathlib import Path
import re
import stat
import struct
import sys


MAX_REQUEST_BYTES = 8_388_608
MAX_ORIGINAL_BYTES = 134_217_728
_DECIMAL = re.compile(r"-?(?:0|[1-9][0-9]*)(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\Z", re.ASCII)


def _read_regular(path: Path, maximum: int, label: str) -> bytes:
    if not path.is_absolute() or path.is_symlink():
        raise ValueError(f"{label}: expected an absolute regular non-symlink file")
    with path.open("rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            raise ValueError(f"{label}: regular file required")
        if info.st_size < 1 or info.st_size > maximum:
            raise ValueError(f"{label}: byte count outside the declared limit")
        raw = stream.read(maximum + 1)
    if len(raw) != info.st_size or len(raw) > maximum:
        raise ValueError(f"{label}: file changed while being read")
    return raw


def _csv_values(original_raw: bytes, metadata: dict) -> list[float]:
    """Read the exact normalized observation CSV, retaining source row order."""
    if original_raw.startswith(b"\xef\xbb\xbf") or b"\r" in original_raw or not original_raw.endswith(b"\n"):
        raise ValueError("source: expected UTF-8 CSV without BOM, CR line endings, or missing final LF")
    try:
        source_text = original_raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as error:
        raise ValueError("source: malformed UTF-8 CSV") from error
    quantity = metadata["observations"]["quantity"]
    columns = ["E_nT", "N_nT", "U_nT"] if quantity == "secondary_enu_nT" else ["value_nT"]
    expected_header = ["row_id", *columns]
    try:
        rows = csv.reader(io.StringIO(source_text, newline=""), strict=True)
        if next(rows, None) != expected_header:
            raise ValueError("source: CSV header does not match the declared observation quantity")
        expected_ids = metadata["acquisition"]["row_ids"]
        width = len(columns)
        values = []
        for expected_id in expected_ids:
            row = next(rows, None)
            if row is None or len(row) != width + 1 or row[0] != expected_id:
                raise ValueError("source: CSV row IDs or row count do not match the sealed inventory")
            for token in row[1:]:
                if not _DECIMAL.fullmatch(token):
                    raise ValueError("source: CSV measurement must use a finite decimal literal")
                try:
                    value = float(token)
                except ValueError as error:
                    raise ValueError("source: CSV measurement is not a numeric value") from error
                if not math.isfinite(value):
                    raise ValueError("source: CSV measurement is not finite")
                values.append(value)
        if next(rows, None) is not None:
            raise ValueError("source: unexpected rows after the sealed inventory")
    except (csv.Error, StopIteration) as error:
        raise ValueError("source: malformed or incomplete CSV observation table") from error
    return values


def _verify_original(handle, request_raw: bytes, original_raw: bytes) -> None:
    metadata = handle.metadata()
    source = metadata["source"]
    actual = hashlib.sha256(original_raw).hexdigest()
    if source["original_bytes"] != len(original_raw) or source["original_sha256"] != actual:
        raise ValueError("source: supplied original bytes do not match the declared size and SHA-256")
    document = json.loads(request_raw)
    nodes = document["processing"]["nodes"]
    if len(nodes) != 1 or nodes[0]["operation"] != "original" or document["processing"]["final_node"] != nodes[0]["id"]:
        raise ValueError("source: this CSV adapter accepts original measurements only; processed lineage requires its own verifier")
    csv_values = _csv_values(original_raw, metadata)
    raw_values = document["observations"]["values"]["data"]
    if len(raw_values) != len(csv_values) or any(
        value != float(source_value) for value, source_value in zip(raw_values, csv_values, strict=True)
    ):
        raise ValueError("source: CSV measurements do not match the sealed observations")


def _prepare_request(template_raw: bytes, original_raw: bytes, parser) -> bytes:
    """Bind normalized source observations and provenance into a closed request."""
    template = parser.parse_request(template_raw)
    metadata = template.metadata()
    document = json.loads(template_raw)
    nodes = document["processing"]["nodes"]
    if len(nodes) != 1 or nodes[0]["operation"] != "original" or document["processing"]["final_node"] != nodes[0]["id"]:
        raise ValueError("template: prepare accepts one original node; processed lineage requires its own verifier")
    values = _csv_values(original_raw, metadata)
    descriptor = document["observations"]["values"]
    expected_count = math.prod(descriptor["shape"])
    if len(values) != expected_count:
        raise ValueError("source: CSV observation count differs from the closed template shape")

    values_sha256 = hashlib.sha256(b"".join(struct.pack("<d", value) for value in values)).hexdigest()
    source_sha256 = hashlib.sha256(original_raw).hexdigest()
    descriptor["data"] = values
    descriptor["sha256"] = values_sha256
    document["observations"]["values_sha256"] = values_sha256
    document["source"]["original_sha256"] = source_sha256
    document["source"]["original_bytes"] = len(original_raw)
    nodes[0]["input_sha256"] = source_sha256
    nodes[0]["output_sha256"] = values_sha256

    prepared = parser.canonical(document)
    parser.parse_request(prepared)
    return prepared


def _write_new_file(target: Path, raw: bytes) -> None:
    """Exclusive write, fsync, readback, and remove only this new file on failure."""
    created = False
    try:
        with target.open("xb") as stream:
            created = True
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        if target.read_bytes() != raw:
            raise OSError("output: readback differs from the prepared bytes")
    except BaseException:
        if created:
            target.unlink(missing_ok=True)
        raise


def _data_path(path: Path, root: Path, *, must_exist: bool) -> Path:
    if not path.is_absolute() or path.is_symlink():
        raise ValueError("output: expected an absolute non-symlink path")
    ancestor = path.parent
    while ancestor != ancestor.parent:
        if ancestor.exists() and ancestor.is_symlink():
            raise ValueError("output: symlinked parent paths are forbidden")
        ancestor = ancestor.parent
    resolved = path.resolve(strict=must_exist)
    data_root = root.resolve()
    repo = Path(__file__).resolve().parents[1]
    if resolved == data_root or data_root not in resolved.parents:
        raise ValueError("output: path must remain under GEOPHYSICS_LOCAL_DATA_ROOT")
    if resolved == repo or repo in resolved.parents:
        raise ValueError("output: research artifacts cannot be written into the repository")
    return resolved


def _summary(value: dict) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def _main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="operation", required=True)

    prepare = sub.add_parser("prepare", help="bind a normalized measurement CSV to a closed metadata template")
    prepare.add_argument("--template", type=Path, required=True)
    prepare.add_argument("--original", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)

    validate = sub.add_parser("validate", help="validate bytes, rights, geometry, and write a sealed geometry export")
    validate.add_argument("--request", type=Path, required=True)
    validate.add_argument("--original", type=Path, required=True)
    validate.add_argument("--output", type=Path, required=True)

    calibrate = sub.add_parser("calibrate", help="run all frozen development candidates and freeze the selected model")
    calibrate.add_argument("--request", type=Path, required=True)
    calibrate.add_argument("--original", type=Path, required=True)
    calibrate.add_argument("--output-dir", type=Path, required=True)
    calibrate.add_argument("--wall-seconds", type=float, default=120.0)

    evaluate = sub.add_parser("evaluate", help="consume the sealed outer evaluation once for a frozen model")
    evaluate.add_argument("--request", type=Path, required=True)
    evaluate.add_argument("--original", type=Path, required=True)
    evaluate.add_argument("--matrix-dir", type=Path, required=True)
    evaluate.add_argument("--freeze", type=Path, required=True)

    verify = sub.add_parser("verify", help="verify the candidate matrix and immutable final-model receipt")
    verify.add_argument("--request", type=Path, required=True)
    verify.add_argument("--original", type=Path, required=True)
    verify.add_argument("--matrix-dir", type=Path, required=True)
    verify.add_argument("--freeze", type=Path, required=True)

    args = parser.parse_args(argv)

    # Establish the reviewed single-thread policy before importing NumPy,
    # SciPy, SimPEG, or any optimizer module.
    for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        os.environ[name] = "1"
    os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root / "data-pipeline"))

    try:
        from sources import local_data_root
        import magnetic_survey_json as request_parser
    except ImportError as error:
        print(_summary({"schema": "magnetic-local-error-1", "code": "dependency",
                        "message": f"local numerical environment unavailable: {type(error).__name__}"}))
        return 2

    try:
        if args.operation == "prepare":
            template_raw = _read_regular(args.template, MAX_REQUEST_BYTES, "template")
            original_raw = _read_regular(args.original, MAX_ORIGINAL_BYTES, "original")
            prepared = _prepare_request(template_raw, original_raw, request_parser)
            target = _data_path(args.output, local_data_root(), must_exist=False)
            if not target.parent.is_dir():
                raise ValueError("output: parent directory must already exist under GEOPHYSICS_LOCAL_DATA_ROOT")
            _write_new_file(target, prepared)
            sealed = request_parser.parse_request(prepared)
            sealed_metadata = sealed.metadata()
            print(_summary({"status": "prepared", "request_sha256": hashlib.sha256(prepared).hexdigest(),
                            "source_sha256": sealed_metadata["source"]["original_sha256"],
                            "source_bytes": len(original_raw), "observation_rows": len(sealed_metadata["acquisition"]["row_ids"]),
                            "method_accepted": False, "online_admitted": False}))
            return 0

        request_raw = _read_regular(args.request, MAX_REQUEST_BYTES, "request")
        original_raw = _read_regular(args.original, MAX_ORIGINAL_BYTES, "original")
        handle = request_parser.parse_request(request_raw)
        _verify_original(handle, request_raw, original_raw)

        # No numerical geometry or solver module is imported until the complete
        # closed request and the source-to-observation byte match have passed.
        import magnetic_survey

        plan = magnetic_survey.plan_geometry(handle)

        if args.operation == "validate":
            target = _data_path(args.output, local_data_root(), must_exist=False)
            if target.exists():
                raise FileExistsError("output: geometry exports are write-once")
            import magnetic_survey_bundle

            magnetic_survey_bundle.write_geometry(target, request_parser.parse_request(request_raw))
            print(_summary({"status": "validated", "geometry_seal_sha256": plan["identity"]["seal_sha256"],
                            "configuration_sha256": plan["identity"]["configuration_sha256"],
                            "eligible_for_local_processing": plan["eligibility"]["local_processing"],
                            "claims": plan["claims"]}))
            return 0

        if args.operation == "calibrate":
            if type(args.wall_seconds) is not float or not 0.0 < args.wall_seconds <= 120.0:
                raise ValueError("wall-seconds: value must be in (0, 120]")
            if not plan["eligibility"]["local_processing"]:
                raise ValueError("survey: rights or processing lineage does not permit local calibration")
            output_dir = _data_path(args.output_dir, local_data_root(), must_exist=False)
            if output_dir.exists() and not output_dir.is_dir():
                raise ValueError("output-dir: existing path must be a directory for receipt resume")
            if output_dir.is_symlink():
                raise ValueError("output-dir: symlink forbidden")
            import magnetic_candidate_matrix
            import magnetic_final_refit

            matrix = magnetic_candidate_matrix.run_matrix(
                request_raw, output_dir / "matrix", wall_seconds=args.wall_seconds,
            )
            selected = matrix.get("selected")
            if not matrix["claims"]["candidate_matrix_complete"] or selected is None:
                print(_summary({"status": "failed", "stage": "candidate_matrix",
                                "matrix_dir": str(output_dir / "matrix"),
                                "claims": matrix["claims"]}))
                return 3
            freeze_path = output_dir / "matrix" / f"final-refit-{selected}.json"
            if freeze_path.exists():
                frozen = magnetic_final_refit.verify_final_refit(request_raw, output_dir / "matrix", freeze_path)
            else:
                frozen = magnetic_final_refit.run_final_refit(
                    request_raw, output_dir / "matrix", freeze_path,
                    wall_seconds=args.wall_seconds,
                )
            if frozen.get("status") != "converged":
                print(_summary({"status": "failed", "stage": "final_refit",
                                "selected": selected, "freeze": str(freeze_path),
                                "receipt_sha256": frozen.get("receipt_sha256"),
                                "claims": frozen.get("claims")}))
                return 3
            print(_summary({"status": "calibrated", "selected": selected,
                            "matrix_dir": str(output_dir / "matrix"),
                            "freeze": str(freeze_path),
                            "receipt_sha256": frozen["receipt_sha256"],
                            "method_accepted": False, "online_admitted": False}))
            return 0

        matrix_dir = _data_path(args.matrix_dir, local_data_root(), must_exist=True)
        freeze_path = _data_path(args.freeze, local_data_root(), must_exist=True)
        if freeze_path.parent != matrix_dir:
            raise ValueError("freeze: immutable model receipt must be inside its matrix directory")
        import magnetic_final_refit

        frozen = magnetic_final_refit.verify_final_refit(request_raw, matrix_dir, freeze_path)
        if args.operation == "verify":
            print(_summary({"status": "verified", "selected": frozen["identity"]["selected_candidate"],
                            "freeze_sha256": frozen["receipt_sha256"],
                            "method_accepted": False, "online_admitted": False}))
            return 0

        import magnetic_outer_evaluation
        result = magnetic_outer_evaluation.run_outer_evaluation(request_raw, matrix_dir, freeze_path)
        print(_summary({"status": result["status"],
                        "selected": result["selection"]["candidate_id"],
                        "outer_metrics": result["metrics"]["outer"],
                        "receipt_sha256": result["receipt_sha256"],
                        "method_accepted": False, "online_admitted": False}))
        return 0 if result["status"] == "complete" else 3
    except FileExistsError as error:
        print(_summary({"schema": "magnetic-local-error-1", "code": "durability", "message": str(error)}))
        return 5
    except request_parser.InputError as error:
        print(_summary({"schema": "magnetic-local-error-1", "code": error.code,
                        "message": error.message}))
        return 2
    except (OSError, RuntimeError, TypeError, ValueError) as error:
        print(_summary({"schema": "magnetic-local-error-1", "code": "processing", "message": str(error)}))
        return 2


def main(argv=None) -> int:
    return _main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
