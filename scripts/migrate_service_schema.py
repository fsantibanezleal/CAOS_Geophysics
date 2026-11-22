"""Apply the reviewed, additive service-schema migration on the ML VPS."""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import stat
import sys


LEGACY = "0003_processing_jobs"
HEAD = "0004_waveform_artifacts"
MIGRATION = Path("app/migrations/versions/0004_waveform_artifacts.py")
MIGRATION_SHA256 = "c08dde26f55aea87af39e9228013f23a6823de1cf54ba9163d164b0ebfb49bc0"
DDL_SHA256 = {
    LEGACY: "33a96998cd77c595a0d983461f84e1367a813e460b9c13222d07490fd9b86709",
    HEAD: "f2a1a28305e8115d42549bc64508afe8de76f42b8b2e32b516ff753f6f45851f",
}
DATABASE = Path("/var/lib/geophysics/api.sqlite3")


def digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def database_state_digest(database: Path) -> str:
    """Hash SQLite main/WAL/SHM bytes as one quiescent service-state snapshot."""
    digest = hashlib.sha256()
    for path in (database, Path(str(database) + "-wal"), Path(str(database) + "-shm")):
        try:
            info = path.lstat()
        except FileNotFoundError:
            continue
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ValueError("SQLite state contains an unsupported sidecar")
        digest.update(path.name.encode("ascii") + b"\0")
        digest.update(bytes.fromhex(digest_file(path)))
    return digest.hexdigest()


def schema_fingerprint(connection: sqlite3.Connection) -> tuple[str, str]:
    ddl = [tuple(row) for row in connection.execute(
        "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type,name")]
    revision = connection.execute("SELECT version_num FROM alembic_version").fetchall()
    if len(revision) != 1 or revision[0][0] not in DDL_SHA256:
        raise ValueError("database migration revision is unsupported")
    current = revision[0][0]
    fingerprint = hashlib.sha256(json.dumps(ddl, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()
    if fingerprint != DDL_SHA256[current]:
        raise ValueError("database schema fingerprint differs from reviewed migration")
    if connection.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
        raise ValueError("database integrity check failed")
    if connection.execute("PRAGMA foreign_key_check").fetchall():
        raise ValueError("database foreign-key check failed")
    return current, fingerprint


def recovery_observation(attempt: dict, verification: dict) -> dict:
    """Bind a read-only post-failure observation to its durable attempt marker."""
    if (set(attempt) != {"schema", "status", "preflight_revision", "to"}
            or attempt.get("schema") != "geophysics.service-schema-migration-attempt/v1"
            or attempt.get("status") != "attempted"
            or attempt.get("preflight_revision") not in {LEGACY, HEAD}
            or attempt.get("to") != HEAD):
        raise ValueError("migration attempt marker is invalid")
    if (verification.get("schema") != "geophysics.service-schema-migration/v1"
            or verification.get("verification_only") is not True
            or verification.get("from") != HEAD or verification.get("to") != HEAD
            or verification.get("changed") is not False
            or verification.get("migration_sha256") != MIGRATION_SHA256
            or verification.get("schema_sha256_after") != DDL_SHA256[HEAD]):
        raise ValueError("read-only migration recovery verification is invalid")
    for key in ("database_sha256_after", "schema_sha256_after"):
        value = verification.get(key)
        if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
            raise ValueError("read-only migration recovery digest is invalid")
    return {
        "schema": "geophysics.service-schema-migration-recovery/v1",
        "activation_preflight_revision": attempt["preflight_revision"],
        "observed_revision": HEAD,
        "candidate_migration_sha256": MIGRATION_SHA256,
        "database_sha256_at_recovery": verification["database_sha256_after"],
        "schema_sha256_at_recovery": verification["schema_sha256_after"],
        "observation": ("forward_head_verified_after_lost_receipt" if attempt["preflight_revision"] == LEGACY
                        else "existing_head_verified_after_lost_receipt"),
        "observed_at": datetime.now(timezone.utc).isoformat(),
    }


def migrate(database: Path, source: Path, *, verify_only: bool = False) -> dict:
    """Upgrade only the exact legacy schema; leave data tables and rows untouched."""
    if database.is_symlink():
        raise ValueError("service database cannot be a symlink")
    database = database.resolve(strict=True)
    source = source.resolve(strict=True)
    migration = source / MIGRATION
    if not migration.is_file() or migration.is_symlink() or digest_file(migration) != MIGRATION_SHA256:
        raise ValueError("candidate migration bytes differ from reviewed migration")
    info = database.stat(follow_symlinks=False)
    if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
        raise ValueError("service database must be a single-link regular file")

    before_sha256 = database_state_digest(database)
    with sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True) as connection:
        connection.execute("PRAGMA query_only=ON")
        before_revision, before_schema_sha256 = schema_fingerprint(connection)

    if before_revision == HEAD:
        return {
            "schema": "geophysics.service-schema-migration/v1",
            "database": database.as_posix(), "from": HEAD, "to": HEAD,
            "migration_sha256": MIGRATION_SHA256, "schema_sha256_before": before_schema_sha256,
            "schema_sha256_after": before_schema_sha256, "database_sha256_before": before_sha256,
            "database_sha256_after": before_sha256, "changed": False,
            "verification_only": verify_only,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        }
    if before_revision != LEGACY:
        raise ValueError("database is not at the reviewed migration predecessor")
    if verify_only:
        raise ValueError("verification-only recovery found the database before the migration head")

    sys.path.insert(0, str(source))
    from alembic import command
    from alembic.config import Config

    os.environ["GEOPHYSICS_DB_PATH"] = database.as_posix()
    os.environ["GEOPHYSICS_DATA_DIR"] = database.parent.as_posix()
    config = Config(str(source / "app/alembic.ini"))
    command.upgrade(config, HEAD)

    with sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True) as connection:
        connection.execute("PRAGMA query_only=ON")
        after_revision, after_schema_sha256 = schema_fingerprint(connection)
    if after_revision != HEAD or after_schema_sha256 != DDL_SHA256[HEAD]:
        raise ValueError("database did not reach the reviewed migration head")
    return {
        "schema": "geophysics.service-schema-migration/v1",
        "database": database.as_posix(), "from": before_revision, "to": after_revision,
        "migration_sha256": MIGRATION_SHA256, "schema_sha256_before": before_schema_sha256,
        "schema_sha256_after": after_schema_sha256,
        "database_sha256_before": before_sha256, "database_sha256_after": database_state_digest(database),
        "changed": True, "downgrade": "forbidden; forward migration only",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    if sys.platform != "linux" or os.geteuid() == 0:
        raise ValueError("run as the unprivileged geophysics service account")
    import grp
    import pwd

    identity = pwd.getpwnam("geophysics")
    group = grp.getgrnam("geophysics")
    if os.geteuid() != identity.pw_uid:
        raise ValueError("migration process identity differs from the geophysics service account")
    state = DATABASE.parent.stat(follow_symlinks=False)
    database = DATABASE.stat(follow_symlinks=False)
    if ((state.st_uid, state.st_gid, stat.S_IMODE(state.st_mode)) !=
            (identity.pw_uid, group.gr_gid, 0o700)
            or (database.st_uid, database.st_gid, stat.S_IMODE(database.st_mode)) !=
            (identity.pw_uid, group.gr_gid, 0o600)):
        raise ValueError("service database ownership or permissions differ")
    for sidecar in (Path(str(DATABASE) + "-wal"), Path(str(DATABASE) + "-shm")):
        try:
            info = sidecar.lstat()
        except FileNotFoundError:
            continue
        if ((info.st_uid, info.st_gid, stat.S_IMODE(info.st_mode), info.st_nlink) !=
                (identity.pw_uid, group.gr_gid, 0o600, 1) or not stat.S_ISREG(info.st_mode)):
            raise ValueError("SQLite sidecar ownership or permissions differ")
    source = Path(__file__).resolve().parents[1]
    print(json.dumps(migrate(DATABASE, source, verify_only=args.verify_only),
                     sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, sqlite3.DatabaseError) as error:
        print(type(error).__name__ + ": " + str(error), file=sys.stderr)
        raise SystemExit(1)
