"""Private bounded profile child. No API libraries, URL fetch or raw publication."""
from pathlib import Path
import argparse
import hashlib
import importlib.metadata
import os
import platform
import re
import sys
from uuid import UUID

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "data-pipeline"))
import supplied_profiles as workflow
from process_supplied_profile import engine_diagnostics


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("input", "raw", "output"):
        parser.add_argument("--"+name, type=Path, required=True)
    for name in ("job-id", "dataset-sha256", "request-sha256", "method-id", "parameters"):
        parser.add_argument("--"+name, required=True)
    args = parser.parse_args(argv)
    try:
        UUID(args.job_id)
        if any(not re.fullmatch(r"[0-9a-f]{64}", value)
               for value in (args.dataset_sha256, args.request_sha256)):
            raise ValueError("invalid digest")
        raw_dataset, _ = workflow._read(args.input, workflow.MAX_RESULT_BYTES)
        if hashlib.sha256(raw_dataset).hexdigest() != args.dataset_sha256:
            raise ValueError("dataset bytes changed")
        dataset = workflow._decode(raw_dataset, workflow.MAX_RESULT_BYTES)
        parameters = workflow._decode(args.parameters.encode(), 65536)
        if parameters != {} or type(parameters) is not dict:
            raise ValueError("only frozen profile settings are admitted")
        meta = workflow.parse_metadata(workflow._encode(dataset["profile_metadata"]))
        if (dataset["schema"] != "geophysics.observation-dataset/v1"
                or dataset["method_id"] != args.method_id or meta["method"] != args.method_id
                or dataset["parent_raw_sha256"] != meta["source"]["sha256"]
                or dataset["parent_raw_bytes"] != meta["source"]["bytes"]):
            raise ValueError("original/method identity changed")
        for name in ("dataset_id", "owner_id", "project_id", "raw_asset_id"):
            UUID(dataset[name])
        with engine_diagnostics():
            profile = workflow.process_profile(args.raw, meta)
        if profile["geometry"] != dataset["geometry"]:
            raise ValueError("admitted geometry changed")
        environment = {"python": platform.python_version(), "packages": {}}
        for package in ("numpy", "scipy", "pygimli", "pgcore"):
            try:
                environment["packages"][package] = importlib.metadata.version(package)
            except importlib.metadata.PackageNotFoundError:
                environment["packages"][package] = None
        result = {"schema": "geophysics.processing-result/v1", "job_id": args.job_id,
                  "dataset_id": dataset["dataset_id"], "dataset_sha256": args.dataset_sha256,
                  "method_id": args.method_id, "request_sha256": args.request_sha256,
                  "parameters": parameters, "raw_asset_id": dataset["raw_asset_id"],
                  "raw_sha256": dataset["parent_raw_sha256"], "raw_bytes": dataset["parent_raw_bytes"],
                  "numerical_verdict": profile["engine_report"]["inverse_status"],
                  "execution_lane": "protected-worker", "profile": profile,
                  "environment": environment,
                  "environment_sha256": hashlib.sha256(workflow._encode(environment)).hexdigest(),
                  "child_code_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                  "truth": None}
        encoded = workflow._encode(result)
        if len(encoded) > 64*1024*1024:
            raise ValueError("profile result exceeds scratch boundary")
        with args.output.open("xb") as output:
            output.write(encoded)
            output.flush()
            os.fsync(output.fileno())
        return 0  # Computation completed; numerical acceptance stays in its own verdict.
    except (KeyError, ValueError, TypeError, OSError, RuntimeError) as exc:
        # Private child stderr is never returned by the profile API. Retain a
        # bounded diagnostic for operators, while the public job stays generic.
        print(f"profile_processing_failed:{type(exc).__name__}:{str(exc)[:300]}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
