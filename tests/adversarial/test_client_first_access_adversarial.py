"""Bounded adversarial entry point for the client-first-access feature.

Every requirement maps to an existing focused backend/UI gate below. The
browser tests use intercepted API responses and make no VPS acceptance claim.
"""
from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile

from tests.adversarial._existing_pytest_gate import run_existing


ROOT = Path(__file__).resolve().parents[2]


def run_frontend(*args: str, env: dict[str, str] | None = None) -> None:
    npm = "npm.cmd" if os.name == "nt" else "npm"
    completed = subprocess.run(
        [npm, *args], cwd=ROOT / "frontend", env=env, check=False,
    )
    if completed.returncode:
        raise AssertionError(f"bounded client-first-access frontend gate failed: {completed.returncode}")


def test_adversarial_client_first_access_contract():
    run_existing(
        "tests/api/test_local_auth.py::test_default_environment_needs_no_smtp",
        "tests/api/test_local_auth.py::test_local_routes_and_session_lifecycle",
        "tests/api/test_local_auth.py::test_operator_provisioning_and_explicit_rotation",
        "tests/api/test_local_auth.py::test_rotation_revokes_only_owner_sessions",
        "tests/api/test_local_auth.py::test_plural_accounts_projects_and_anonymous_boundary",
        "tests/api/test_local_auth.py::test_provisioning_cli_redacts_invalid_secret_input",
        "tests/api/test_local_auth.py::test_local_deletion_profile_and_existing_backup_custody",
    )

    run_frontend("run", "test", "--", "--run", "src/test/local-access.test.ts")

    # Isolate screenshots outside the repository and run only the named local
    # access spec against a strict-port preview of the built frontend.
    with tempfile.TemporaryDirectory(prefix="caos-client-first-access-") as output:
        env = os.environ.copy()
        env["GEOPHYSICS_QA_URL"] = "http://127.0.0.1:8899"
        env["GEOPHYSICS_QA_EVIDENCE"] = output
        npm_exec = "npx.cmd" if os.name == "nt" else "npx"
        completed = subprocess.run(
            [npm_exec, "playwright", "test", "-c", "playwright.client-first-access.config.ts"],
            cwd=ROOT / "frontend", env=env, check=False,
        )
        if completed.returncode:
            raise AssertionError(f"bounded client-first-access browser gate failed: {completed.returncode}")
