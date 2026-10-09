"""Export test-owned native receipts for browser gates, never account records.

Run against an explicit external pytest case directory after the native job
test has passed. Reads existing persisted job/dataset rows and exact stored
bytes; does not rerun physics, query users, or alter the SQLite database.
"""
import argparse
import asyncio
import json
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from app.models import ObservationDataset, ProcessingJob
from app.processing import _dataset_view, _job_view
from app.processing_contract import canonical_bytes, sha256
from app.profile_bundle import build_profile_bundle


async def export(root: Path, output: Path, local_output: Path | None = None):
    root, output = root.resolve(), output.resolve()
    checkout = Path(__file__).resolve().parents[2]
    if output.is_relative_to(checkout) or root.is_relative_to(checkout):
        raise ValueError("test inputs and outputs must be external")
    if local_output is not None and local_output.resolve().is_relative_to(checkout):
        raise ValueError("local inspection output must be external")
    database = root / "api.sqlite3"
    if not database.is_file() or database.is_symlink():
        raise ValueError("explicit test database missing")
    engine = create_async_engine(f"sqlite+aiosqlite:///file:{database.as_posix()}?mode=ro&uri=true")
    try:
        async with async_sessionmaker(engine)() as session:
            jobs = (await session.execute(select(ProcessingJob).where(ProcessingJob.state == "succeeded"))).scalars().all()
            if len(jobs) != 1 or jobs[0].method_id not in {"ert.topographic-profile/v1", "traveltime.first-arrival-profile/v1"}:
                raise ValueError("one completed test-owned profile job required")
            job = jobs[0]
            dataset = (await session.execute(select(ObservationDataset).where(ObservationDataset.id == job.dataset_id))).scalar_one()
            dataset_bytes = (root / dataset.storage_key).read_bytes()
            result_bytes = (root / job.result_key).read_bytes()
            if sha256(dataset_bytes) != dataset.sha256 or sha256(result_bytes) != job.result_sha256:
                raise ValueError("test receipt bytes differ from stored hashes")
            bundle = build_profile_bundle(json.loads(dataset_bytes), json.loads(result_bytes), dataset.sha256, job.result_sha256)
            packet = canonical_bytes({"receipt": _dataset_view(dataset), "job": _job_view(job)})
        output.mkdir(parents=True, exist_ok=False)
        for name, encoded in (("bindings.json", packet), ("dataset.json", dataset_bytes), ("result.json", result_bytes), ("export.zip", bundle)):
            with (output / name).open("xb") as stream:
                stream.write(encoded)
        if local_output is not None:
            # Reopen the genuine stored inner contract; never solve again or
            # relabel the original code hashes as a new producer execution.
            import sys
            sys.path.insert(0, str(checkout/"data-pipeline"))
            from supplied_profiles import export_result, import_result
            profile = json.loads(result_bytes)["profile"]
            export_result(profile, local_output.resolve())
            if import_result(local_output.resolve()) != profile:
                raise ValueError("local stored-profile extraction differs")
        print(json.dumps({"method":job.method_id,"result_sha256":job.result_sha256,"raw_bytes_exported":False}))
    finally:
        await engine.dispose()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--local-output", type=Path)
    arguments = parser.parse_args()
    asyncio.run(export(arguments.case, arguments.output, arguments.local_output))
