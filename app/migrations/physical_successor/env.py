"""Explicit external rollback-journal candidate with transactional revision/DDL."""

import hashlib
import os
from pathlib import Path

from alembic import context
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

config = context.config
if (config.attributes.get("m01_successor_candidate_only") is not True
        or not config.get_main_option("version_locations") or context.is_offline_mode()):
    raise ValueError("explicit_successor_candidate_registry_required")
raw = os.environ.get("GEOPHYSICS_DB_PATH")
if not raw or not Path(raw).is_absolute():
    raise ValueError("external_candidate_database_required")
path = Path(raw).resolve()
product = Path(__file__).resolve().parents[3]
if path.is_relative_to(product):
    raise ValueError("external_candidate_database_required")
candidate_root = os.environ.get("GEOPHYSICS_CANDIDATE_ROOT")
if not candidate_root or not Path(candidate_root).is_absolute():
    raise ValueError("explicit_external_candidate_root_required")
candidate_root = Path(candidate_root).resolve(strict=True)
if (not path.is_relative_to(candidate_root) or path == candidate_root
        or any((parent / ".git").exists() for parent in (candidate_root, *candidate_root.parents))):
    raise ValueError("explicit_external_candidate_root_required")
if path.is_symlink() or any(path.with_name(path.name + suffix).exists() for suffix in ("-wal", "-shm")):
    raise ValueError("candidate_wal_target_refused_before_open")
if path.exists():
    if not path.is_file() or path.stat().st_nlink != 1:
        raise ValueError("candidate_database_identity_refused")
    with path.open("rb") as source:
        header = source.read(20)
    if header[:16] != b"SQLite format 3\0" or header[18:20] != b"\1\1":
        raise ValueError("candidate_wal_target_refused_before_open")

# Source admission is before SQL target opening, including prior revisions.
locations = Path(config.get_main_option("version_locations")).resolve()
for name, expected in (
    ("0001_api_foundation.py", "f595ce71642f8555c9a7e3e615aeccf1f642eaf2a1be09f8864b25a8797e52ae"),
    ("0002_private_storage_permission.py", "572a55739d70b0fc54f6bfdc3fa19ed3ab514fac2136feb817a3c8c89f2551ca"),
    ("0003_processing_jobs.py", "06a9437a41e6665e1689cb85af0789c741e420dc380888139ed138c2abe4939f"),
    ("0004_waveform_artifacts.py", "82c827b94940d803fae42eb7137fda63f2b4d816e11dddd481f79c5b3cb41ac3"),
):
    migration = locations / name
    if (migration.is_symlink() or not migration.is_file() or migration.stat().st_size > 8 * 1048576
            or hashlib.sha256(migration.read_bytes()).hexdigest() != expected):
        raise ValueError("predecessor_source_binding")
path.parent.mkdir(parents=True, exist_ok=True)
engine = create_engine("sqlite:///" + path.as_posix(), poolclass=NullPool)
try:
    with engine.connect() as connection:
        journal = connection.exec_driver_sql("PRAGMA journal_mode").scalar()
        if journal not in ("delete", "memory"):
            raise ValueError("successor_requires_rollback_journal_or_memory")
        connection.exec_driver_sql("PRAGMA foreign_keys=OFF")
        connection.exec_driver_sql("PRAGMA synchronous=FULL")
        connection.commit()
        context.configure(connection=connection, transactional_ddl=True)
        try:
            with context.begin_transaction():
                connection.exec_driver_sql("BEGIN IMMEDIATE")
                context.run_migrations()
                if connection.exec_driver_sql("PRAGMA foreign_key_check").fetchall():
                    raise ValueError("successor_foreign_key_check_failed")
        finally:
            connection.exec_driver_sql("PRAGMA foreign_keys=ON")
            if connection.exec_driver_sql("PRAGMA foreign_keys").scalar() != 1:
                raise ValueError("successor_foreign_keys_not_restored")
finally:
    engine.dispose()
