"""Export an existing test-owned native job through the real API for browser QA.

No migration, account provisioning, original replacement or engine execution.
The explicit test database must already match the current migration head.
"""
import argparse
import json
from pathlib import Path
import secrets

from fastapi.testclient import TestClient

from app.config import Settings
from app.server import create_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    parser.add_argument("--job",required=True)
    args = parser.parse_args()
    checkout = Path(__file__).resolve().parents[2]
    root = args.case.resolve(strict=True)
    output = args.output.resolve()
    if root.is_relative_to(checkout) or output.is_relative_to(checkout) or output.exists():
        raise ValueError("existing external case and fresh external output required")
    settings = Settings(data_dir=root,auth_secret=secrets.token_urlsafe(48),cookie_secure=False,
                        public_origin="http://testserver",auth_mode="local")
    with TestClient(create_app(settings)) as client:
        csrf = client.get("/api/auth/csrf").json()["csrf_token"]
        login = client.post("/api/auth/cookie/login",headers={"Origin":"http://testserver","X-CSRF-Token":csrf},
                            data={"username":"local-owner@example.org","password":"test-only-password-872"})
        if login.status_code != 204:
            raise ValueError("existing test owner required")
        projects = client.get("/api/projects").json()
        # Preserve the API's response envelope; do not inspect or alter SQL rows.
        if isinstance(projects,dict):
            projects = projects["projects"]
        matched = []
        for project in projects:
            base = f"/api/projects/{project['id']}"
            response = client.get(base+"/jobs/"+args.job)
            if response.status_code == 200:
                job = response.json()
                if job["state"] != "succeeded":
                    raise ValueError("successful native job required")
                rows = client.get(base+"/datasets").json()
                if isinstance(rows,dict):
                    rows = rows["datasets"]
                receipt = next(row for row in rows if row["dataset_id"] == job["dataset_id"])
                result = client.get(job["result_url"])
                bundle = client.get(base+"/jobs/"+args.job+"/export")
                if result.status_code != 200 or bundle.status_code != 200:
                    raise ValueError("actual native result/export unavailable")
                matched.append((job,receipt,result.content,bundle.content))
        if len(matched) != 1:
            raise ValueError("exact owned job relation required")
        job,receipt,result,bundle = matched[0]
        output.mkdir(parents=False,exist_ok=False)
        for name,body in (("bindings.json",json.dumps({"job":job,"receipt":receipt},sort_keys=True).encode()),
                          ("result.json",result),("export.zip",bundle)):
            with (output/name).open("xb") as stream:
                stream.write(body)
    print("existing native job exported through actual owned API; no new computation")


if __name__ == "__main__":
    main()
