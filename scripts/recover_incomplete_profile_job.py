"""Archive exact missing-receipt profile evidence; never accept partial science."""
import argparse
import asyncio
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from app.config import WorkerSettings
from app.profile_incomplete_recovery import recover_incomplete_job
from app.worker import _worker_lock


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("job_id")
    args = parser.parse_args()
    settings = WorkerSettings.from_env()
    with _worker_lock(settings.data_dir):
        manifest = asyncio.run(recover_incomplete_job(settings,args.job_id))
    print(json.dumps(dict(job_id=manifest["job_id"],archived=True,job_state_changed=False,science_admitted=False)))


if __name__ == "__main__":
    main()
