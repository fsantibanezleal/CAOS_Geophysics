"""Restricted maintenance snapshots and tombstone-aware NEW-target recovery.

Standalone stdlib ops tooling. See docs/operations/01_backup_restore.md before use.
Never controls services, creates keys, overwrites state or erases backups.
"""

from __future__ import annotations

import argparse
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import sqlite3
import stat
import subprocess
import sys
import tarfile
import tempfile
import threading
import time
from uuid import UUID, uuid4


REVISION = "0003_processing_jobs"
# Exact sqlite_master DDL from committed Alembic migrations, not ORM create_all.
DDL_SHA256 = "33a96998cd77c595a0d983461f84e1367a813e460b9c13222d07490fd9b86709"
SNAPSHOT_SCHEMA = "geophysics.restricted-snapshot/v1"
AUTHORITY_SCHEMA = "geophysics.recovery-authority/v1"
PROOF_SCHEMA = "geophysics.maintenance-proof/v1"
RECEIPT_SCHEMA = "geophysics.ops-receipt/v1"
JSON_CAP = 16 * 1024 * 1024
HASH_RE = re.compile(r"[0-9a-f]{64}")


class RecoveryError(Exception):
    """Only a stable non-sensitive code is exposed by the CLI."""


def require(condition, code: str) -> None:
    if not condition:
        raise RecoveryError(code)


def canonical(value) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()


def parse_json(raw: bytes):
    require(len(raw) <= JSON_CAP, "json_limit")

    def pairs(items):
        result = {}
        for key, value in items:
            require(key not in result, "duplicate_json_key")
            result[key] = value
        return result

    def invalid(_):
        raise RecoveryError("nonfinite_json")

    try:
        return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise RecoveryError("invalid_json") from exc


def fields(value, keys: str) -> None:
    require(isinstance(value, dict) and set(value) == set(keys.split()), "unknown_contract_fields")


def uuid(value) -> str:
    require(isinstance(value, str), "invalid_uuid")
    try:
        require(str(UUID(value)) == value, "noncanonical_uuid")
    except ValueError as exc:
        raise RecoveryError("invalid_uuid") from exc
    return value


def digest(value) -> str:
    require(isinstance(value, str) and HASH_RE.fullmatch(value), "invalid_sha256")
    return value


def instant(value) -> datetime:
    require(isinstance(value, str), "invalid_time")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        require(parsed.tzinfo is not None, "timezone_required")
        return parsed.astimezone(timezone.utc)
    except ValueError as exc:
        raise RecoveryError("invalid_time") from exc


def now() -> datetime:
    return datetime.now(timezone.utc)


def stamp() -> str:
    return now().isoformat().replace("+00:00", "Z")


def safe_path(value, *, exists=True, directory=False, private=False, outside_repo=True) -> Path:
    path = Path(value)
    require(path.is_absolute() and ".." not in path.parts and path != Path(path.anchor), "explicit_absolute_path_required")
    # Resolve only AFTER inspecting every component, including Windows junctions.
    for part in reversed((path, *path.parents)):
        if os.path.lexists(part):
            info = part.lstat()
            require(not stat.S_ISLNK(info.st_mode)
                    and not getattr(info, "st_file_attributes", 0) & 0x400, "linked_path")
            require(stat.S_ISDIR(info.st_mode) or stat.S_ISREG(info.st_mode), "special_path")
            if stat.S_ISREG(info.st_mode):
                require(info.st_nlink == 1, "hardlinked_path")
        if outside_repo and part.is_dir():
            require(not os.path.lexists(part / ".git"), "private_path_inside_repository")
    require(path.resolve(strict=False) == path, "noncanonical_absolute_path")
    if exists:
        require(path.is_dir() if directory else path.is_file(), "required_path_missing")
    else:
        require(not os.path.lexists(path), "new_target_required")
        require(path.parent.is_dir(), "new_target_parent_missing")
    if private and os.name == "posix":
        require(path.stat().st_mode & 0o077 == 0, "private_permissions_required")
    return path


def separate(left: Path, right: Path) -> None:
    require(not left.is_relative_to(right) and not right.is_relative_to(left), "overlapping_paths")


def member_name(name: str) -> str:
    require(isinstance(name, str) and len(name) <= 220 and "\\" not in name and ":" not in name
            and re.fullmatch(r"[A-Za-z0-9_./-]+", name), "unsafe_archive_path")
    parts = name.split("/")
    require(all(part not in {"", ".", ".."} for part in parts) and not PurePosixPath(name).is_absolute(),
            "unsafe_archive_path")
    return name


@dataclass(frozen=True)
class Limits:
    total: int = 4 * 1024**3
    file: int = 1024**3
    count: int = 100_000
    seconds: int = 600

    def __post_init__(self):
        require(0 < self.file <= self.total and 0 < self.count <= 1_000_000 and 0 < self.seconds <= 3600,
                "invalid_limits")

    @property
    def archive(self):
        return self.total + JSON_CAP + self.count * 2048 + 10240


def sha_file(path: Path, cap: int) -> str:
    safe_path(path, outside_repo=False)
    require(path.stat().st_size <= cap, "file_limit")
    result = hashlib.sha256()
    size = 0
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(block)
            require(size <= cap, "file_limit")
            result.update(block)
    return result.hexdigest()


def read_json(path: Path):
    safe_path(path, outside_repo=False)
    require(path.stat().st_size <= JSON_CAP, "json_limit")
    return parse_json(path.read_bytes())


def new_file(path: Path):
    # os.open does not get pathlib's Windows long-path handling on every host.
    native = "\\\\?\\" + str(path) if os.name == "nt" and path.is_absolute() else str(path)
    return os.fdopen(os.open(native, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), "wb")


def write_new(path: Path, data: bytes) -> None:
    with new_file(path) as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())


def sync_dir(path: Path) -> None:
    if os.name == "posix":
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def copy_new(source: Path, destination: Path) -> None:
    private_parents(destination.parent)
    with source.open("rb") as incoming:
        with new_file(destination) as outgoing:
            shutil.copyfileobj(incoming, outgoing, 1024 * 1024)
            outgoing.flush()
            os.fsync(outgoing.fileno())


def private_parents(path: Path):
    missing = []
    while not path.exists():
        missing.append(path)
        path = path.parent
    for directory in reversed(missing):
        directory.mkdir(mode=0o700)


class Age:
    def __init__(self, binary: Path, identity: Path | None, recipient: str | None, limits: Limits):
        self.binary = safe_path(binary, outside_repo=False)
        self.identity = safe_path(identity, private=True) if identity else None
        self.recipient = recipient
        self.limits = limits
        if recipient:
            require(re.fullmatch(r"age1[023456789acdefghjklmnpqrstuvwxyz]{58}", recipient), "native_recipient_required")
        if self.identity:
            require(self.identity.stat().st_size <= 4096, "identity_limit")
            lines = self.identity.read_text(encoding="ascii").splitlines()
            keys = [line for line in lines if line and not line.startswith("#")]
            require(len(keys) == 1 and re.fullmatch(r"AGE-SECRET-KEY-1[0-9A-Z]{58}", keys[0]),
                    "native_identity_required")
        version = subprocess.run([str(self.binary), "--version"], capture_output=True, timeout=10, check=False)
        require(version.returncode == 0 and len(version.stdout) <= 100, "age_unavailable")
        self.version = version.stdout.decode("ascii").strip()
        match = re.fullmatch(r"v?(\d+)\.(\d+)\.(\d+)", self.version)
        require(match and tuple(map(int, match.groups())) >= (1, 3, 1), "maintained_age_required")

    def encrypt(self, source: Path, destination: Path):
        require(self.recipient, "recipient_required")
        with source.open("rb") as incoming:
            with new_file(destination) as outgoing:
                try:
                    result = subprocess.run([str(self.binary), "--encrypt", "--recipient", self.recipient],
                                            stdin=incoming, stdout=outgoing, stderr=subprocess.DEVNULL,
                                            timeout=self.limits.seconds, check=False)
                    require(result.returncode == 0, "age_encryption_failed")
                    outgoing.flush()
                    os.fsync(outgoing.fileno())
                except subprocess.TimeoutExpired as exc:
                    raise RecoveryError("age_timeout") from exc
        require(0 < destination.stat().st_size <= self.limits.archive + 1024 * 1024, "ciphertext_limit")

    def decrypt(self, source: Path, destination: Path, cap: int):
        require(self.identity, "identity_required")
        require(source.stat().st_size <= cap + 1024 * 1024, "ciphertext_limit")
        process = subprocess.Popen([str(self.binary), "--decrypt", "--identity", str(self.identity), str(source)],
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        timer = threading.Timer(self.limits.seconds, process.kill)
        timer.start()
        try:
            with new_file(destination) as outgoing:
                size = 0
                while block := process.stdout.read(1024 * 1024):
                    size += len(block)
                    require(size <= cap, "decryption_limit")
                    outgoing.write(block)
                require(process.wait() == 0, "age_decryption_failed")
                outgoing.flush()
                os.fsync(outgoing.fileno())
        finally:
            timer.cancel()
            if process.poll() is None:
                process.kill()
            process.wait()
            process.stdout.close()


class Maintenance:
    def __init__(self, proof: Path, source: Path, database: Path, deployment: str, fixture_root: Path | None):
        self.path = safe_path(proof, private=True)
        self.source = source
        self.database = database
        self.deployment = uuid(deployment)
        self.fixture_root = fixture_root
        self.hash = sha_file(self.path, JSON_CAP)
        self.check()

    def check(self):
        require(sha_file(self.path, JSON_CAP) == self.hash, "maintenance_proof_changed")
        proof = read_json(self.path)
        fields(proof, "schema source database deployment_id mode issued_at expires_at ingress_blocked all_writers_accounted units")
        require(proof["schema"] == PROOF_SCHEMA and proof["source"] == str(self.source)
                and proof["database"] == str(self.database) and proof["deployment_id"] == self.deployment,
                "maintenance_proof_mismatch")
        start, expiry = instant(proof["issued_at"]), instant(proof["expires_at"])
        require(start <= now() < expiry and 0 < (expiry - start).total_seconds() <= 3600, "maintenance_proof_stale")
        require(proof["ingress_blocked"] is True and proof["all_writers_accounted"] is True,
                "maintenance_attestation_required")
        if self.fixture_root:
            require(proof["mode"] == "fixture" and proof["units"] == [], "fixture_proof_required")
            for path in (self.source, self.database, self.path):
                require(path.is_relative_to(self.fixture_root), "fixture_boundary")
        else:
            require(sys.platform == "linux" and proof["mode"] == "systemd", "systemd_host_required")
            units = proof["units"]
            require(isinstance(units, list) and 2 <= len(units) <= 32 and all(isinstance(unit, str) for unit in units)
                    and len(set(units)) == len(units)
                    and sum(unit.endswith(".service") for unit in units) >= 2, "writer_units_required")
            for unit in units:
                require(re.fullmatch(r"[A-Za-z0-9_@.-]+\.(service|timer|socket|path)", unit), "invalid_unit")
                self.check_unit(unit)

    @staticmethod
    def check_unit(unit: str):
        result = subprocess.run(["/usr/bin/systemctl", "show", "--no-pager",
                                 "--property=LoadState,ActiveState,SubState,UnitFileState,MainPID,ControlGroup", unit],
                                capture_output=True, timeout=10, check=False)
        require(result.returncode == 0 and len(result.stdout) < 8192, "systemd_observation_failed")
        props = dict(line.split("=", 1) for line in result.stdout.decode("ascii").splitlines() if "=" in line)
        require(props.get("LoadState") == "masked" and props.get("ActiveState") == "inactive"
                and props.get("SubState") == "dead" and props.get("UnitFileState") in {"masked", "masked-runtime"},
                "writer_not_stopped_masked")
        if unit.endswith(".service"):
            require(props.get("MainPID") == "0", "writer_process_alive")
            group = props.get("ControlGroup")
            require(group is not None, "cgroup_evidence_missing")
            if group:
                require(group.startswith("/") and ".." not in group.split("/"), "invalid_cgroup")
                events = Path("/sys/fs/cgroup") / group.lstrip("/") / "cgroup.events"
                if events.parent.exists():
                    require(events.is_file() and "populated 0" in events.read_text().splitlines(),
                            "writer_cgroup_populated")


def clean_database(path: Path):
    for suffix in ("-wal", "-shm", "-journal"):
        sidecar = Path(str(path) + suffix)
        if os.path.lexists(sidecar):
            safe_path(sidecar, outside_repo=False)
            require(sidecar.stat().st_size == 0, "sqlite_sidecar_requires_maintenance_checkpoint")


def open_database(path: Path):
    clean_database(path)
    connection = sqlite3.connect(path.as_uri() + "?mode=ro&immutable=1", uri=True)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA trusted_schema=OFF")
    connection.execute("PRAGMA foreign_keys=ON")
    deadline = time.monotonic() + 60
    connection.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
    return connection


def validate_database(connection):
    require(connection.execute("SELECT COUNT(*) FROM sqlite_master WHERE sql IS NOT NULL").fetchone()[0] <= 64,
            "sqlite_schema_object_limit")
    ddl = [tuple(row) for row in connection.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type,name")]
    require(hashlib.sha256(json.dumps(ddl, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
            == DDL_SHA256, "unknown_sqlite_schema")
    require([tuple(row) for row in connection.execute("SELECT version_num FROM alembic_version")] == [(REVISION,)],
            "unknown_sqlite_revision")
    require([tuple(row) for row in connection.execute("PRAGMA integrity_check")] == [("ok",)], "sqlite_integrity")
    require(not connection.execute("PRAGMA foreign_key_check").fetchall(), "sqlite_foreign_keys")
    require(not connection.execute("SELECT 1 FROM processing_jobs WHERE state IN ('queued','running') LIMIT 1").fetchone(),
            "active_jobs_require_recovery")
    require(not connection.execute("SELECT 1 FROM processing_jobs WHERE state NOT IN ('succeeded','failed','cancelled') LIMIT 1")
            .fetchone(), "unknown_job_state")


def tombstones(connection) -> list[dict]:
    result = []
    for row in connection.execute("SELECT * FROM deletion_receipts ORDER BY project_id"):
        value = dict(row)
        for column in ("asset_hashes", "asset_manifest", "derived_manifest"):
            value[column] = parse_json(value[column].encode()) if value[column] is not None else None
        validate_tombstone(value)
        result.append(value)
    return result


def validate_tombstone(value):
    fields(value, "id project_id owner_id deleted_at asset_hashes asset_manifest derived_manifest backup_purge_status")
    for field in ("id", "project_id", "owner_id"):
        uuid(value[field])
    # SQLite's stored UTC times may be naive; retain the original timestamp exactly.
    require(isinstance(value["deleted_at"], str) and len(value["deleted_at"]) <= 40, "invalid_deletion_time")
    instant(value["deleted_at"] if "+" in value["deleted_at"] or value["deleted_at"].endswith("Z")
            else value["deleted_at"] + "Z")
    require(value["backup_purge_status"] == "not_attempted", "unsupported_purge_status")
    require(isinstance(value["asset_hashes"], list), "invalid_tombstone")
    for item in value["asset_hashes"]:
        digest(item)
    for field in ("asset_manifest", "derived_manifest"):
        items = value[field]
        require(isinstance(items, list), "incomplete_tombstone_manifest")
        identities = set()
        for item in items:
            fields(item, "asset_id sha256 byte_count" if field == "asset_manifest" else "kind id sha256 byte_count")
            identifier = uuid(item["asset_id" if field == "asset_manifest" else "id"])
            require(identifier not in identities, "duplicate_tombstone_asset")
            identities.add(identifier)
            digest(item["sha256"])
            require(type(item["byte_count"]) is int and item["byte_count"] >= 0, "invalid_tombstone_size")
            if field == "derived_manifest":
                require(item["kind"] in {"dataset", "result"}, "unknown_tombstone_kind")
    require(sorted(value["asset_hashes"]) == sorted(item["sha256"] for item in value["asset_manifest"]),
            "inconsistent_tombstone_hashes")


def merge_tombstones(previous: list, current: list) -> list:
    merged = {}
    ids = set()
    for entry in previous + current:
        validate_tombstone(entry)
        key = entry["project_id"]
        if key in merged:
            require(canonical(merged[key]) == canonical(entry), "tombstone_conflict")
        else:
            require(entry["id"] not in ids, "tombstone_id_conflict")
            merged[key] = entry
            ids.add(entry["id"])
    return [merged[key] for key in sorted(merged)]


def validate_registration(record):
    fields(record, "snapshot_id sha256 created_at expires_at policy_id")
    uuid(record["snapshot_id"])
    digest(record["sha256"])
    require(instant(record["expires_at"]) > instant(record["created_at"]), "invalid_retention")
    require(isinstance(record["policy_id"], str) and re.fullmatch(r"[a-z0-9-]{1,64}", record["policy_id"]),
            "invalid_retention_policy")


def validate_authority(value, deployment, fixture):
    fields(value, "schema deployment_id fixture_only sequence predecessor_sha256 observed_at tombstones snapshots")
    require(value["schema"] == AUTHORITY_SCHEMA and value["deployment_id"] == deployment
            and value["fixture_only"] is fixture, "authority_identity_mismatch")
    require(type(value["sequence"]) is int and value["sequence"] >= 1, "invalid_authority_sequence")
    if value["sequence"] == 1:
        require(value["predecessor_sha256"] is None, "invalid_authority_predecessor")
    else:
        digest(value["predecessor_sha256"])
    require(instant(value["observed_at"]) <= now(), "authority_from_future")
    require(isinstance(value["tombstones"], list) and isinstance(value["snapshots"], list), "invalid_authority_lists")
    require(len(merge_tombstones([], value["tombstones"])) == len(value["tombstones"]), "duplicate_tombstone")
    ids, hashes = set(), set()
    for record in value["snapshots"]:
        validate_registration(record)
        require(record["snapshot_id"] not in ids and record["sha256"] not in hashes, "duplicate_snapshot")
        ids.add(record["snapshot_id"])
        hashes.add(record["sha256"])


def load_authority(age: Age, path: Path, expected_hash: str, scratch: Path, deployment: str, fixture: bool):
    require(sha_file(path, JSON_CAP + 1024 * 1024) == digest(expected_hash), "authority_hash_mismatch")
    plain = scratch / "authority.json"
    age.decrypt(path, plain, JSON_CAP)
    value = read_json(plain)
    validate_authority(value, deployment, fixture)
    return value


def inventory(connection, root: Path, limits: Limits) -> dict[str, dict]:
    validate_database(connection)
    for table in ("user", "access_tokens", "rate_windows", "account_usage", "projects", "raw_assets", "source_records",
                  "observation_datasets", "processing_jobs", "deletion_receipts"):
        require(connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] <= limits.count,
                "database_row_limit")
    projects = {row["id"]: row["owner_id"] for row in connection.execute("SELECT id,owner_id FROM projects")}
    deleted = {row["project_id"] for row in tombstones(connection)}
    require(not set(projects) & deleted, "tombstoned_project_present")
    for project, owner in projects.items():
        uuid(project)
        uuid(owner)
    raw_rows = {row["id"]: dict(row) for row in connection.execute("SELECT * FROM raw_assets")}
    sources = {row["id"]: dict(row) for row in connection.execute("SELECT * FROM source_records")}
    datasets = {row["id"]: dict(row) for row in connection.execute("SELECT * FROM observation_datasets")}
    expected = {}

    def add(row, key, kind, hash_field="sha256", bytes_field="byte_count"):
        uuid(row["id"])
        require(projects.get(row["project_id"]) == row["owner_id"], "owner_identity_mismatch")
        require(row["storage_key" if kind != "result" else "result_key"] == key, "storage_identity_mismatch")
        member_name(key)
        require(key not in expected, "duplicate_storage_key")
        require(type(row[bytes_field]) is int and 0 <= row[bytes_field] <= limits.file, "file_limit")
        expected[key] = {"sha256": digest(row[hash_field]), "bytes": row[bytes_field],
                         "project_id": row["project_id"], "owner_id": row["owner_id"], "kind": kind}

    for source in sources.values():
        require(projects.get(source["project_id"]) == source["owner_id"], "source_owner_mismatch")
    for row in raw_rows.values():
        source = sources.get(row["source_id"])
        require(source and source["project_id"] == row["project_id"] and source["owner_id"] == row["owner_id"]
                and source["sha256"] == row["sha256"], "raw_source_mismatch")
        add(row, f"projects/{row['owner_id']}/{row['project_id']}/{row['id']}", "raw")
    for row in datasets.values():
        parent = raw_rows.get(row["raw_asset_id"])
        require(parent and parent["owner_id"] == row["owner_id"] and parent["project_id"] == row["project_id"]
                and parent["sha256"] == row["raw_sha256"], "dataset_parent_mismatch")
        key = f"derived/{row['owner_id']}/{row['project_id']}/datasets/{row['id']}.json"
        add(row, key, "dataset")
        payload = read_json(root / key)
        require(isinstance(payload, dict), "unknown_or_changed_dataset_schema")
        require(payload.get("schema") == "geophysics.observation-dataset/v1"
                and payload.get("dataset_id") == row["id"] and payload.get("owner_id") == row["owner_id"]
                and payload.get("project_id") == row["project_id"] and payload.get("version") == row["version"]
                and payload.get("raw_asset_id") == row["raw_asset_id"]
                and payload.get("parent_raw_sha256") == row["raw_sha256"]
                and payload.get("parser_version") == row["parser_version"] and payload.get("modality") == row["modality"]
                and payload.get("dimensions") == {"station": row["row_count"]}
                and len(payload.get("observed_mgal", [])) == row["row_count"]
                and len(payload.get("sigma_mgal", [])) == row["row_count"], "unknown_or_changed_dataset_schema")
        require(canonical(payload) == (root / key).read_bytes(), "noncanonical_derivative")
    for sql_row in connection.execute("SELECT * FROM processing_jobs"):
        row = dict(sql_row)
        dataset = datasets.get(row["dataset_id"])
        require(dataset and dataset["owner_id"] == row["owner_id"] and dataset["project_id"] == row["project_id"]
                and dataset["sha256"] == row["dataset_sha256"], "job_dataset_mismatch")
        request = parse_json(row["request_json"].encode())
        require(hashlib.sha256(canonical(request)).hexdigest() == row["request_sha256"], "job_request_mismatch")
        if row["state"] == "succeeded":
            key = f"derived/{row['owner_id']}/{row['project_id']}/results/{row['id']}.json"
            add(row, key, "result", "result_sha256", "result_bytes")
            payload = read_json(root / key)
            require(isinstance(payload, dict), "unknown_or_changed_result_schema")
            require(payload.get("schema") == "geophysics.processing-result/v1"
                    and payload.get("job_id") == row["id"] and payload.get("dataset_id") == row["dataset_id"]
                    and payload.get("dataset_sha256") == row["dataset_sha256"]
                    and payload.get("method_id") == row["method_id"]
                    and payload.get("request_sha256") == row["request_sha256"]
                    and payload.get("parameters") == request["parameters"]
                    and not {"predicted", "model", "residual"} & set(payload), "unknown_or_changed_result_schema")
            require(canonical(payload) == (root / key).read_bytes(), "noncanonical_derivative")
        else:
            require(all(row[name] is None for name in ("result_key", "result_sha256", "result_bytes")),
                    "non_success_result")
    totals = {}
    for row in raw_rows.values():
        totals[row["owner_id"]] = totals.get(row["owner_id"], 0) + row["byte_count"]
    usage = {row["user_id"]: row["raw_bytes"] for row in connection.execute("SELECT * FROM account_usage")}
    require(all(usage.get(owner, 0) == total for owner, total in totals.items())
            and all(total == totals.get(owner, 0) for owner, total in usage.items()), "quota_mismatch")
    require(len(expected) + 1 <= limits.count and sum(item["bytes"] for item in expected.values()) <= limits.total,
            "inventory_limit")
    for key, item in expected.items():
        path = safe_path(root / key, outside_repo=False)
        require(path.stat().st_size == item["bytes"] and sha_file(path, limits.file) == item["sha256"],
                "asset_hash_mismatch")
    return expected


def audit_tree(root: Path, database: Path, expected: dict, limits: Limits):
    ignored = {database, *(Path(str(database) + suffix) for suffix in ("-wal", "-shm", "-journal"))}
    lock = root / ".processing-worker.lock"
    if os.path.lexists(lock):
        safe_path(lock, outside_repo=False)
        require(lock.stat().st_size <= 1, "unknown_worker_lock")
        ignored.add(lock)
    allowed_dirs = {root}
    for key in expected:
        parent = (root / key).parent
        while parent != root:
            allowed_dirs.add(parent)
            parent = parent.parent
    for name in (".staging", ".exports", ".deleting", ".job-staging", "projects", "derived", ".backups"):
        directory = root / name
        if directory.exists():
            safe_path(directory, directory=True, outside_repo=False)
            if name.startswith("."):
                require(next(directory.iterdir(), None) is None, "interrupted_or_backup_state")
            allowed_dirs.add(directory)
    count = 0
    for parent, dirs, files in os.walk(root, followlinks=False):
        for name in dirs + files:
            count += 1
            require(count <= limits.count * 6 + 32, "tree_entry_limit")
            path = Path(parent) / name
            safe_path(path, directory=name in dirs, outside_repo=False)
            if name in dirs:
                # Empty project/owner directories left by exact application deletion are harmless.
                require(path in allowed_dirs or (path.relative_to(root).parts[0] in {"projects", "derived"}
                        and next(path.iterdir(), None) is None), "unknown_directory")
            else:
                require(path in ignored or path.relative_to(root).as_posix() in expected, "unknown_private_file")


def validate_manifest(manifest, limits: Limits):
    fields(manifest, "schema deployment_id fixture_only database_revision registration tombstones files")
    require(manifest["schema"] == SNAPSHOT_SCHEMA and manifest["database_revision"] == REVISION,
            "unknown_snapshot_schema")
    uuid(manifest["deployment_id"])
    require(type(manifest["fixture_only"]) is bool, "invalid_fixture_marker")
    validate_registration(manifest["registration"])
    require(isinstance(manifest["files"], dict) and "api.sqlite3" in manifest["files"]
            and 1 <= len(manifest["files"]) <= limits.count, "manifest_file_limit")
    require(isinstance(manifest["tombstones"], list), "invalid_snapshot_tombstones")
    require(len(merge_tombstones([], manifest["tombstones"])) == len(manifest["tombstones"]), "duplicate_tombstone")
    size = 0
    for name, item in manifest["files"].items():
        member_name(name)
        fields(item, "sha256 bytes project_id owner_id kind")
        digest(item["sha256"])
        require(type(item["bytes"]) is int and 0 <= item["bytes"] <= limits.file, "manifest_byte_limit")
        size += item["bytes"]
        if name == "api.sqlite3":
            require(item["kind"] == "database" and item["project_id"] is None and item["owner_id"] is None,
                    "invalid_database_member")
        else:
            owner, project = uuid(item["owner_id"]), uuid(item["project_id"])
            parts = name.split("/")
            if item["kind"] == "raw":
                require(len(parts) == 4 and parts[:3] == ["projects", owner, project], "invalid_raw_member")
                uuid(parts[3])
            else:
                require(item["kind"] in {"dataset", "result"} and len(parts) == 5
                        and parts[:4] == ["derived", owner, project, item["kind"] + "s"]
                        and parts[4].endswith(".json"), "invalid_derived_member")
                uuid(parts[4][:-5])
    require(size <= limits.total, "manifest_total_limit")


def extract_archive(archive_path: Path, target: Path, limits: Limits):
    require(archive_path.stat().st_size <= limits.archive, "archive_size_limit")
    # Inspect raw headers first. tarfile otherwise consumes PAX/GNU extensions before
    # returning a member, which would evade the per-member allocation checks below.
    with archive_path.open("rb") as handle:
        count = 0
        while True:
            header = handle.read(512)
            require(len(header) == 512, "truncated_archive")
            if not any(header):
                require(handle.read(512) == b"\0" * 512, "archive_end_marker")
                break
            info = tarfile.TarInfo.frombuf(header, "utf-8", "strict")
            require(info.type == tarfile.REGTYPE and not info.linkname, "unsupported_archive_member")
            member_name(info.name)
            require(0 <= info.size <= (JSON_CAP if count == 0 else limits.file), "archive_byte_limit")
            count += 1
            require(count <= limits.count + 1, "archive_member_limit")
            handle.seek((info.size + 511) // 512 * 512, 1)
            require(handle.tell() <= archive_path.stat().st_size, "truncated_archive")
    target.mkdir(mode=0o700)
    with tarfile.open(archive_path, mode="r:") as archive:
        seen = set()
        manifest = None
        for index, member in enumerate(archive):
            require(index <= limits.count and member.isfile() and member.type == tarfile.REGTYPE
                    and not member.pax_headers and member.sparse is None and not member.linkname,
                    "unsupported_archive_member")
            name = member_name(member.name)
            require(name not in seen, "duplicate_archive_member")
            seen.add(name)
            if index == 0:
                require(name == "manifest.json" and 0 <= member.size <= JSON_CAP, "manifest_must_be_first")
                with archive.extractfile(member) as handle:
                    manifest = parse_json(handle.read(JSON_CAP + 1))
                validate_manifest(manifest, limits)
                continue
            require(manifest is not None and name in manifest["files"], "unknown_archive_member")
            entry = manifest["files"][name]
            require(member.size == entry["bytes"], "archive_size_mismatch")
            destination = target / name
            private_parents(destination.parent)
            with archive.extractfile(member) as incoming:
                with new_file(destination) as outgoing:
                    result = hashlib.sha256()
                    size = 0
                    while block := incoming.read(1024 * 1024):
                        size += len(block)
                        require(size <= member.size, "archive_size_mismatch")
                        result.update(block)
                        outgoing.write(block)
                    require(size == entry["bytes"] and result.hexdigest() == entry["sha256"], "archive_hash_mismatch")
                    outgoing.flush()
                    os.fsync(outgoing.fileno())
        require(manifest is not None and seen == {"manifest.json", *manifest["files"]}, "archive_missing_members")
        # Reject appended concatenated archives/bytes after the first end marker.
        offset = archive.offset
    with archive_path.open("rb") as handle:
        handle.seek(offset)
        while block := handle.read(1024 * 1024):
            require(not any(block), "archive_trailing_data")
    return manifest


def make_archive(path: Path, manifest: dict, root: Path):
    with tarfile.open(path, "x", format=tarfile.USTAR_FORMAT) as archive:
        raw = canonical(manifest)
        require(len(raw) <= JSON_CAP, "manifest_json_limit")
        header = tarfile.TarInfo("manifest.json")
        header.size, header.mode = len(raw), 0o600
        archive.addfile(header, io.BytesIO(raw))
        for name in sorted(manifest["files"]):
            header = tarfile.TarInfo(name)
            header.size, header.mode = manifest["files"][name]["bytes"], 0o600
            with (root / name).open("rb") as handle:
                archive.addfile(header, handle)
    os.chmod(path, 0o600)


def reconcile(target: Path, manifest: dict, authority: dict):
    deleted = {entry["project_id"]: entry for entry in authority["tombstones"]}
    # An older snapshot must not contradict an independently observed deletion owner.
    with closing(sqlite3.connect(target / "api.sqlite3")) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA journal_mode=DELETE")
        connection.execute("PRAGMA secure_delete=ON")
        connection.execute("PRAGMA synchronous=FULL")
        owners = {row[0] for row in connection.execute('SELECT id FROM "user"')}
        for project, receipt in deleted.items():
            existing = connection.execute("SELECT owner_id FROM projects WHERE id=?", (project,)).fetchone()
            require(existing is None or existing[0] == receipt["owner_id"], "deletion_owner_conflict")
            for table in ("processing_jobs", "observation_datasets", "raw_assets", "source_records", "projects"):
                column = "id" if table == "projects" else "project_id"
                connection.execute(f"DELETE FROM {table} WHERE {column}=?", (project,))
            if receipt["owner_id"] in owners:
                connection.execute("DELETE FROM deletion_receipts WHERE project_id=?", (project,))
                columns = list(receipt)
                values = [canonical(receipt[key]).decode() if key in {
                    "asset_hashes", "asset_manifest", "derived_manifest"} else receipt[key] for key in columns]
                connection.execute(f"INSERT INTO deletion_receipts ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                                   values)
        connection.execute("DELETE FROM access_tokens")
        connection.execute("DELETE FROM rate_windows")
        connection.execute("DELETE FROM account_usage")
        connection.execute("INSERT INTO account_usage (user_id,raw_bytes) SELECT owner_id,SUM(byte_count) FROM raw_assets GROUP BY owner_id")
        connection.commit()
        connection.execute("VACUUM")
        connection.commit()
    removed = 0
    for name, entry in manifest["files"].items():
        if entry["project_id"] in deleted:
            path = target / name
            require(sha_file(path, entry["bytes"]) == entry["sha256"], "reconciliation_hash_mismatch")
            path.unlink()  # Only exact validated files in tooling-owned NEW scratch.
            removed += 1
    for parent, dirs, files in os.walk(target, topdown=False):
        if Path(parent) != target and not list(Path(parent).iterdir()):
            Path(parent).rmdir()
    return removed


def prepare(args):
    limits = Limits(args.max_bytes, args.max_file_bytes, args.max_files, args.timeout_seconds)
    fixture = safe_path(args.fixture_root, directory=True, private=True) if args.fixture_root else None
    require(fixture is not None or sys.platform == "linux", "systemd_host_required")
    output = safe_path(args.new_output if args.command != "restore" else args.new_target, exists=False)
    scratch_parent = safe_path(args.scratch_parent, directory=True, private=True)
    separate(output, scratch_parent)
    if os.name == "posix":
        safe_path(output.parent, directory=True, private=True)
    paths = []
    for name in ("source", "database", "snapshot", "authority", "maintenance_proof", "identity"):
        value = getattr(args, name, None)
        if value:
            path = safe_path(value, directory=name == "source", private=name in {"identity", "maintenance_proof"})
            setattr(args, name, path)
            paths.append(path)
            separate(output, path)
            separate(scratch_parent, path)
    if args.command != "restore":
        require(args.database == args.source / "api.sqlite3" or not args.database.is_relative_to(args.source),
                "database_layout_unsupported")
    if fixture:
        for path in [*paths, output, scratch_parent]:
            require(path.is_relative_to(fixture) and path != fixture, "fixture_boundary")
    age = Age(Path(args.age_binary), getattr(args, "identity", None), getattr(args, "recipient", None), limits)
    return limits, fixture, output, scratch_parent, age


def publish(staging: Path, output: Path, receipt: dict):
    # Exclusive mkdir reserves the path. Failure leaves a private incomplete target, never overwrites.
    output.mkdir(mode=0o700)
    for parent, dirs, files in os.walk(staging):
        relative = Path(parent).relative_to(staging)
        for name in dirs:
            (output / relative / name).mkdir(mode=0o700)
        for name in files:
            source = Path(parent) / name
            destination = output / relative / name
            copy_new(source, destination)
            require(sha_file(source, source.stat().st_size) == sha_file(destination, source.stat().st_size),
                    "publication_hash_mismatch")
    for parent, dirs, files in os.walk(output, topdown=False):
        sync_dir(Path(parent))
    write_new(output / "receipt.json", canonical(receipt))
    sync_dir(output)
    sync_dir(output.parent)


def capture(args):
    limits, fixture, output, scratch_parent, age = prepare(args)
    proof = Maintenance(args.maintenance_proof, args.source, args.database, args.deployment_id, fixture)
    require(bool(args.authority) != bool(args.initialize_authority), "authority_or_explicit_bootstrap_required")
    require(bool(args.authority) == bool(args.authority_sha256), "authority_hash_required")
    with tempfile.TemporaryDirectory(prefix="ops-", dir=scratch_parent) as temporary:
        scratch = Path(temporary)
        staging = scratch / "output"
        staging.mkdir(mode=0o700)
        old = load_authority(age, args.authority, args.authority_sha256, scratch, args.deployment_id, bool(fixture)) if args.authority else None
        with closing(open_database(args.database)) as source_db:
            validate_database(source_db)
            initial = inventory(source_db, args.source, limits)
            audit_tree(args.source, args.database, initial, limits)
            current_tombstones = tombstones(source_db)
            authority = {
                "schema": AUTHORITY_SCHEMA, "deployment_id": args.deployment_id, "fixture_only": bool(fixture),
                "sequence": old["sequence"] + 1 if old else 1,
                "predecessor_sha256": args.authority_sha256 if old else None,
                "observed_at": stamp(), "tombstones": merge_tombstones(old["tombstones"] if old else [], current_tombstones),
                "snapshots": list(old["snapshots"]) if old else [],
            }
            require(not {entry["project_id"] for entry in authority["tombstones"]}
                    & {row[0] for row in source_db.execute("SELECT id FROM projects")}, "authority_deleted_project_in_source")
            before_db = sha_file(args.database, limits.file)
            if args.command == "backup":
                registration = {"snapshot_id": str(uuid4()), "sha256": "0" * 64, "created_at": stamp(),
                                "expires_at": args.expires_at, "policy_id": args.policy_id}
                validate_registration(registration)
                require(instant(args.expires_at) > now(), "snapshot_already_expired")
                private = scratch / "private"
                private.mkdir(mode=0o700)
                with closing(sqlite3.connect(private / "api.sqlite3")) as destination:
                    source_db.backup(destination)
                    destination.execute("PRAGMA journal_mode=DELETE")
                os.chmod(private / "api.sqlite3", 0o600)
                for key in initial:
                    copy_new(args.source / key, private / key)
                with closing(open_database(private / "api.sqlite3")) as copied_db:
                    copied = inventory(copied_db, private, limits)
                    require(copied == initial, "snapshot_inventory_changed")
                    audit_tree(private, private / "api.sqlite3", copied, limits)
                files = dict(copied)
                files["api.sqlite3"] = {"sha256": sha_file(private / "api.sqlite3", limits.file),
                                       "bytes": (private / "api.sqlite3").stat().st_size,
                                       "project_id": None, "owner_id": None, "kind": "database"}
                manifest = {"schema": SNAPSHOT_SCHEMA, "deployment_id": args.deployment_id,
                            "fixture_only": bool(fixture), "database_revision": REVISION,
                            "registration": registration.copy(), "tombstones": current_tombstones, "files": files}
                validate_manifest(manifest, limits)
                archive = scratch / "snapshot.tar"
                make_archive(archive, manifest, private)
                # Validate the actual archive bytes before encryption, including exact member limits.
                extract_archive(archive, scratch / "verified", limits)
                age.encrypt(archive, staging / "snapshot.age")
                registration["sha256"] = sha_file(staging / "snapshot.age", limits.archive + 1024 * 1024)
                authority["snapshots"].append(registration)
            proof.check()
            require(sha_file(args.database, limits.file) == before_db and inventory(source_db, args.source, limits) == initial
                    and tombstones(source_db) == current_tombstones, "source_changed_during_maintenance")
            audit_tree(args.source, args.database, initial, limits)
        validate_authority(authority, args.deployment_id, bool(fixture))
        authority["observed_at"] = stamp()
        authority_json = scratch / "next-authority.json"
        write_new(authority_json, canonical(authority))
        require(authority_json.stat().st_size <= JSON_CAP, "authority_json_limit")
        age.encrypt(authority_json, staging / "authority.age")
        receipt = {"schema": RECEIPT_SCHEMA, "operation": args.command, "validated_at": stamp(),
                   "fixture_only": bool(fixture), "deployment_id": args.deployment_id,
                   "age_version": age.version, "maintenance_proof_sha256": proof.hash,
                   "authority_sha256": sha_file(staging / "authority.age", JSON_CAP + 1024 * 1024),
                   "authority_sequence": authority["sequence"], "tombstone_count": len(authority["tombstones"]),
                   "backup_erasure": "not_attempted", "host_drill": "not_run"}
        if args.command == "backup":
            receipt.update(snapshot_sha256=registration["sha256"], snapshot_id=registration["snapshot_id"],
                           expires_at=registration["expires_at"], policy_id=registration["policy_id"])
        proof.check()
        publish(staging, output, receipt)
    return receipt


def restore(args):
    limits, fixture, output, scratch_parent, age = prepare(args)
    deployment = uuid(args.deployment_id)
    require(args.authority and args.authority_sha256, "latest_authority_required")
    expected_snapshot = digest(args.snapshot_sha256)
    require(sha_file(args.snapshot, limits.archive + 1024 * 1024) == expected_snapshot, "snapshot_hash_mismatch")
    with tempfile.TemporaryDirectory(prefix="ops-", dir=scratch_parent) as temporary:
        scratch = Path(temporary)
        authority = load_authority(age, args.authority, args.authority_sha256, scratch, deployment, bool(fixture))
        records = [item for item in authority["snapshots"] if item["sha256"] == expected_snapshot]
        require(len(records) == 1, "snapshot_not_registered")
        registration = records[0]
        require(now() < instant(registration["expires_at"]), "snapshot_retention_expired")
        archive = scratch / "snapshot.tar"
        age.decrypt(args.snapshot, archive, limits.archive)
        staging = scratch / "output"
        staging.mkdir(mode=0o700)
        private = staging / "private"
        manifest = extract_archive(archive, private, limits)
        require(manifest["deployment_id"] == deployment and manifest["fixture_only"] is bool(fixture),
                "snapshot_identity_mismatch")
        embedded = manifest["registration"]
        require(embedded["sha256"] == "0" * 64 and {key: value for key, value in embedded.items() if key != "sha256"}
                == {key: value for key, value in registration.items() if key != "sha256"}, "snapshot_retention_mismatch")
        merged = merge_tombstones(authority["tombstones"], manifest["tombstones"])
        require(merged == merge_tombstones([], authority["tombstones"]), "authority_missing_snapshot_deletion")
        with closing(open_database(private / "api.sqlite3")) as connection:
            expected = inventory(connection, private, limits)
            require(expected == {key: item for key, item in manifest["files"].items() if key != "api.sqlite3"},
                    "snapshot_database_inventory_mismatch")
            require(tombstones(connection) == manifest["tombstones"], "snapshot_database_tombstone_mismatch")
            audit_tree(private, private / "api.sqlite3", expected, limits)
        removed = reconcile(private, manifest, authority)
        with closing(open_database(private / "api.sqlite3")) as connection:
            surviving = inventory(connection, private, limits)
            audit_tree(private, private / "api.sqlite3", surviving, limits)
        copy_new(args.authority, staging / "authority.age")
        require(sha_file(staging / "authority.age", JSON_CAP + 1024 * 1024) == args.authority_sha256,
                "authority_changed_during_restore")
        require(sha_file(args.snapshot, limits.archive + 1024 * 1024) == expected_snapshot,
                "snapshot_changed_during_restore")
        receipt = {"schema": RECEIPT_SCHEMA, "operation": "restore", "validated_at": stamp(),
                   "fixture_only": bool(fixture), "deployment_id": deployment, "age_version": age.version,
                   "snapshot_sha256": expected_snapshot, "snapshot_id": registration["snapshot_id"],
                   "authority_sha256": args.authority_sha256, "authority_sequence": authority["sequence"],
                   "authority_observed_at": authority["observed_at"], "tombstone_count": len(authority["tombstones"]),
                   "removed_file_count": removed, "surviving_file_count": len(surviving),
                   "database_sha256": sha_file(private / "api.sqlite3", limits.file),
                   "sessions_revoked": True, "backup_erasure": "not_attempted", "production_activated": False,
                   "host_drill": "not_run"}
        publish(staging, output, receipt)
    return receipt


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    commands = result.add_subparsers(dest="command", required=True)
    for command in ("backup", "checkpoint", "restore"):
        sub = commands.add_parser(command)
        for option in ("deployment-id", "age-binary", "scratch-parent"):
            sub.add_argument("--" + option, required=True)
        sub.add_argument("--identity")
        sub.add_argument("--authority")
        sub.add_argument("--authority-sha256")
        sub.add_argument("--fixture-root", help="Temporary fixtures only; never valid host evidence")
        sub.add_argument("--max-bytes", type=int, default=4 * 1024**3)
        sub.add_argument("--max-file-bytes", type=int, default=1024**3)
        sub.add_argument("--max-files", type=int, default=100_000)
        sub.add_argument("--timeout-seconds", type=int, default=600)
        if command == "restore":
            sub.add_argument("--snapshot", required=True)
            sub.add_argument("--snapshot-sha256", required=True)
            sub.add_argument("--new-target", required=True)
        else:
            for option in ("source", "database", "maintenance-proof", "recipient", "new-output"):
                sub.add_argument("--" + option, required=True)
            sub.add_argument("--initialize-authority", action="store_true",
                             help="One-time independently audited deployment bootstrap, never recovery")
            if command == "backup":
                sub.add_argument("--expires-at", required=True)
                sub.add_argument("--policy-id", required=True)
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        receipt = restore(args) if args.command == "restore" else capture(args)
    except RecoveryError as exc:
        print(f"recovery_failed: {exc}", file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError, RecursionError, sqlite3.Error, tarfile.TarError, subprocess.SubprocessError):
        print("recovery_failed: invalid_or_unavailable_private_input", file=sys.stderr)
        return 2
    print(json.dumps({"operation": receipt["operation"], "validated": True, "fixture_only": receipt["fixture_only"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
