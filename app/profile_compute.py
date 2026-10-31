"""Fixed profile child command over an operator-configured pinned interpreter."""
from pathlib import Path

from app.profile_contract import PROFILE_METHODS, ProfileParameters
from app.processing_contract import canonical_bytes


def profile_command(job, dataset_path: Path, raw_path: Path, output: Path,
                    profile_python: Path) -> list[str]:
    """No caller-controlled executable/import path; settings and release bind this path."""
    if job.method_id not in PROFILE_METHODS:
        raise ValueError("not a profile method")
    ProfileParameters.model_validate(job.request_json["parameters"])
    # A pinned POSIX venv normally uses a symlink for bin/python. This path is
    # supplied by release configuration, never by a job. Preserve the venv path
    # rather than resolving it to a system interpreter and losing its packages.
    if not profile_python.is_absolute() or not profile_python.is_file():
        raise ValueError("profile runtime is not an explicit interpreter")
    script = Path(__file__).resolve().parents[1] / "scripts/process_profile_job.py"
    return [str(profile_python), "-B", str(script), "--input", str(dataset_path),
            "--raw", str(raw_path), "--output", str(output), "--job-id", job.id,
            "--dataset-sha256", job.dataset_sha256, "--request-sha256", job.request_sha256,
            "--method-id", job.method_id, "--parameters",
            canonical_bytes(job.request_json["parameters"]).decode()]
