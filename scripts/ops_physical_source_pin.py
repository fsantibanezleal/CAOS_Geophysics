"""Pure selected-byte verification. No Git, CLI, archive or filesystem operations."""

from __future__ import annotations

import hashlib
import re

from app.physical_contract import (
    LEGACY_DDL, LEGACY_REVISION, PHYSICAL_REVISION, M, decode_source,
    fields, integer, require, sha,
)

CANDIDATE_PATHS = frozenset("""
app/__init__.py app/alembic.ini app/auth.py app/bundle.py app/compute.py app/config.py
app/database.py app/errors.py app/formats.py app/main.py app/migrations/env.py
app/migrations/versions/0001_api_foundation.py app/migrations/versions/0002_private_storage_permission.py
app/migrations/versions/0003_processing_jobs.py app/models.py app/mt_bundle.py app/mt_compute.py
app/mt_contract.py app/processing.py app/processing_contract.py app/processing_storage.py
app/projects.py app/schemas.py app/security.py app/server.py app/views.py app/worker.py
data-pipeline/edi.py data-pipeline/electromagnetics.py data-pipeline/geology.py
data/fixtures/edi/halfspace-100-native.edi data/fixtures/edi/two-layer-noisy-rotated.edi
tests/api/conftest.py tests/api/test_online_mt.py app/migrations/candidates/0004_physical_persistence.py
app/physical_contract.py app/physical_persistence.py app/physical_leases.py app/physical_recovery.py
app/physical_compute.py data-pipeline/gravity_processing.py data-pipeline/gravity_station_adapter.py
data-pipeline/gravity_transforms.py tests/api/test_physical_persistence_schema.py
tests/api/test_physical_leases.py tests/api/test_physical_processing.py tests/ops/test_physical_recovery_contracts.py
""".split())
OPS_PATHS = frozenset("""
scripts/ops_recovery.py scripts/ops_source_pin.py scripts/ops_host_fixture.py tests/ops/mt_drill.py
scripts/ops_physical_recovery.py scripts/ops_physical_source_pin.py tests/ops/test_physical_native.py tests/ops/physical_drill.py
""".split())

SCIENTIFIC_SOURCES = {
    "data-pipeline/gravity_processing.py": "7863699269b491c2895bcf030d3fb65cf27ac32a652fce91112bc2c7c9c73321",
    "data-pipeline/gravity_station_adapter.py": "b770b16ef87e83dd92f65a90472145ef93a525a9cedf7f55ee3e6f20f8a10cf8",
    "data-pipeline/gravity_transforms.py": "d11d0f207c89c308c9f8711da2a31b84b8adaeb0c12597a5ecc89ce527fdecf0",
}
SCIENTIFIC_PACKAGES = dict(boule="0.5.0", harmonica="0.7.0", numpy="2.2.6", scipy="1.15.2")


def git_blob(body):
    return hashlib.sha1(b"blob " + str(len(body)).encode("ascii") + b"\0" + body).hexdigest()


def _git(value):
    require(type(value) is str and re.fullmatch(r"[0-9a-f]{40}", value), "git_identity")


def verify_selected_sources(source, bodies, *, reviewed_runtime_commit=None, reviewed_ops_commit=None, reviewed_schema_registry=None):
    """Check complete supplied byte maps; never registers/activates the policy.

    bodies has two explicit maps runtime/ops, not arbitrary caller paths. This
    does not verify commit ancestry: the reviewed commits must independently
    select these blobs. Nor does it emit a source archive or checkpoint ACK.
    """
    value = decode_source([source], max_bytes=M, depth=12, nodes=20000)
    fields(value, "schema policy_id runtime_commit ops_commit database_schemas files module_manifests")
    require(value["schema"] == "geophysics.ops-physical-source-policy/v2" and value["policy_id"] == "m01-physical-persistence-v2", "schema")
    _git(value["runtime_commit"])
    _git(value["ops_commit"])
    require(reviewed_runtime_commit is not None and reviewed_ops_commit is not None and
            value["runtime_commit"] == reviewed_runtime_commit and value["ops_commit"] == reviewed_ops_commit and
            type(reviewed_schema_registry) is dict, "independent_source_review")
    fields(value["files"], "runtime ops")
    fields(bodies, "runtime ops")
    total = 0
    for lane, paths in (("runtime", CANDIDATE_PATHS), ("ops", OPS_PATHS)):
        require(type(value["files"][lane]) is dict and type(bodies[lane]) is dict and
                set(value["files"][lane]) == set(bodies[lane]) == paths, "selected_source_paths")
        for path in sorted(paths):
            entry, body = value["files"][lane][path], bodies[lane][path]
            fields(entry, "bytes sha256 git_blob")
            integer(entry["bytes"], 0, 8*M)
            sha(entry["sha256"])
            _git(entry["git_blob"])
            require(type(body) is bytes and len(body) == entry["bytes"] and
                    hashlib.sha256(body).hexdigest() == entry["sha256"] and git_blob(body) == entry["git_blob"], "selected_source_bytes")
            if lane == "runtime" and path in SCIENTIFIC_SOURCES:
                require(entry["sha256"] == SCIENTIFIC_SOURCES[path], "scientific_source_changed")
            require(not body.startswith((b"version https://git-lfs.github.com/spec/", b"MZ", b"\x7fELF")) and b"\0" not in body, "not_source")
            try:
                body.decode("utf-8", "strict")
            except UnicodeError:
                require(False, "source_encoding")
            total += len(body)
            require(total <= 64*M, "source_total")
    registry = value["database_schemas"]
    require(type(registry) is dict and set(registry) == {LEGACY_REVISION, PHYSICAL_REVISION}, "schema_registry")
    require(registry == reviewed_schema_registry, "independent_schema_review")
    for revision, down, path in (
        (LEGACY_REVISION, "0002_private_storage_permission", "app/migrations/versions/0003_processing_jobs.py"),
        (PHYSICAL_REVISION, LEGACY_REVISION, "app/migrations/candidates/0004_physical_persistence.py"),
    ):
        record = registry[revision]
        fields(record, "schema revision down_revision ddl_sha256 migration_sha256 migration_git_blob")
        require(record["schema"] == "geophysics.physical-schema-registration/v1" and record["revision"] == revision and record["down_revision"] == down, "revision")
        sha(record["ddl_sha256"])
        if revision == LEGACY_REVISION:
            require(record["ddl_sha256"] == LEGACY_DDL, "legacy_ddl")
        entry = value["files"]["runtime"][path]
        require(record["migration_sha256"] == entry["sha256"] and record["migration_git_blob"] == entry["git_blob"], "migration_source")
    fields(value["module_manifests"], "correction transform")
    for lane, manifest in value["module_manifests"].items():
        fields(manifest, "schema parser_sha256 wrapper_sha256 adapter_sha256 core_sha256 transform_sha256 runtime_manifest")
        require(manifest["schema"] == "geophysics.physical-modules/v1", "module_schema")
        mapping = dict(parser_sha256="app/physical_contract.py", wrapper_sha256="app/physical_compute.py",
                       core_sha256="data-pipeline/gravity_processing.py")
        mapping["adapter_sha256" if lane == "correction" else "transform_sha256"] = "data-pipeline/gravity_station_adapter.py" if lane == "correction" else "data-pipeline/gravity_transforms.py"
        for key, path in mapping.items():
            require(manifest[key] == value["files"]["runtime"][path]["sha256"], "module_source")
        require(manifest["transform_sha256" if lane == "correction" else "adapter_sha256"] is None, "module_lane")
        fields(manifest["runtime_manifest"], "python python_implementation packages")
        require(manifest["runtime_manifest"]["python_implementation"] == "CPython" and type(manifest["runtime_manifest"]["python"]) is str and re.fullmatch(r"3\.12\.\d+", manifest["runtime_manifest"]["python"]), "module_runtime")
        packages = dict(SCIENTIFIC_PACKAGES)
        if lane == "transform":
            packages.update(verde="1.9.0", **{"scikit-learn": "1.9.1", "matplotlib": "3.10.8"})
        require(manifest["runtime_manifest"]["packages"] == packages, "module_packages")
    return dict(fixture_only=True, runtime=False, registration="UNREGISTERED", status="CANDIDATE_ONLY",
                selected_bytes=total, policy_sha256=hashlib.sha256(source).hexdigest())
