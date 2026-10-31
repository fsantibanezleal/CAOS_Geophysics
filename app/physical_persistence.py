"""Unused pure SQL dictionary for the isolated physical candidate, not ORM wiring."""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType


M = 1048576
J = 9007199254740991
CORRECTION = "gravity.station-corrections/v1"
TRANSFORM = "gravity.equivalent-source-transform/v1"


@dataclass(frozen=True)
class Column:
    name: str
    declaration: str
    predicate: str
    nullable: bool = False
    domain: object = None


@dataclass(frozen=True)
class Table:
    name: str
    columns: tuple[Column, ...]
    primary_key: tuple[str, ...]
    checks: tuple[tuple[str, str], ...] = ()
    uniques: tuple[tuple[str, tuple[str, ...]], ...] = ()
    foreign_keys: tuple[tuple[str, tuple[str, ...], str, tuple[str, ...]], ...] = ()
    indexes: tuple[tuple[str, tuple[str, ...], bool, str | None], ...] = ()

    def ddl(self) -> str:
        parts = [column_sql(self.name, c) for c in self.columns]
        parts.append("PRIMARY KEY (" + ",".join(self.primary_key) + ")")
        parts += [f"CONSTRAINT {n} CHECK (({p}) IS TRUE)" for n, p in self.checks]
        parts += [f"CONSTRAINT {n} UNIQUE ({','.join(cols)})" for n, cols in self.uniques]
        parts += [foreign_key(n, cols, target, refs) for n, cols, target, refs in self.foreign_keys]
        return f"CREATE TABLE {self.name} (" + ",\n".join(parts) + ")"

    def index_ddl(self) -> tuple[str, ...]:
        return tuple(index_sql(n, self.name, cols, unique, where) for n, cols, unique, where in self.indexes)


def foreign_key(name, columns, target, references):
    return (f"CONSTRAINT {name} FOREIGN KEY ({','.join(columns)}) REFERENCES {target} "
            f"({','.join(references)}) ON UPDATE RESTRICT ON DELETE RESTRICT NOT DEFERRABLE")


def index_sql(name, table, columns, unique=False, where=None):
    return f"CREATE {'UNIQUE ' if unique else ''}INDEX {name} ON {table} ({','.join(columns)})" + (f" WHERE {where}" if where else "")


def column(name, domain, nullable=False):
    c = name
    if domain in {"U", "O"}:
        declaration = "CHAR(36)" if domain == "O" else "VARCHAR(36)"
        predicate = (f"typeof({c})='text' AND length({c})=36 AND {c}=lower({c}) AND "
                     f"substr({c},9,1)='-' AND substr({c},14,1)='-' AND substr({c},19,1)='-' AND "
                     f"substr({c},24,1)='-' AND length(replace({c},'-',''))=32 AND "
                     f"replace({c},'-','') NOT GLOB '*[^0-9a-f]*'")
    elif domain == "H":
        declaration, predicate = "VARCHAR(64)", f"typeof({c})='text' AND length({c})=64 AND {c} NOT GLOB '*[^0-9a-f]*'"
    elif domain[0] == "I":
        declaration, predicate = "INTEGER", f"typeof({c})='integer' AND {c} BETWEEN {domain[1]} AND {domain[2]}"
    elif domain[0] == "B":
        declaration, predicate = "BLOB", f"typeof({c})='blob' AND length({c}) BETWEEN 1 AND {domain[1]}"
    elif domain[0] == "T":
        declaration = f"VARCHAR({domain[1]})"
        predicate = f"typeof({c})='text' AND length({c}) BETWEEN 1 AND {domain[1]} AND instr({c},char(0))=0"
    else:
        assert domain[0] == "E"
        declaration = "VARCHAR(80)"
        predicate = f"typeof({c})='text' AND {c} IN (" + ",".join("'" + v + "'" for v in domain[1:]) + ")"
    return Column(name, declaration, predicate, nullable, domain)


def column_sql(table, c):
    predicate = f"{c.name} IS NULL OR ({c.predicate})" if c.nullable else c.predicate
    collation = " COLLATE BINARY" if c.declaration.startswith(("VARCHAR", "CHAR")) else ""
    return f"{c.name} {c.declaration}{collation}{'' if c.nullable else ' NOT NULL'} CONSTRAINT ck_{table}_{c.name} CHECK ({predicate})"


def cols(ids=(), owners=(), hashes=(), extra=()):
    return tuple([column(n, "U") for n in ids] + [column(n, "O") for n in owners] +
                 [column(n, "H") for n in hashes] + [column(*item) for item in extra])


FAMILY = ("root_dataset_id", "owner_id", "project_id", "raw_asset_id", "parser_version")
DATASET = ("id", "owner_id", "project_id", "raw_asset_id", "root_dataset_id", "sha256")
INPUT = ("dataset_id", "owner_id", "project_id", "raw_asset_id", "root_dataset_id", "dataset_sha256")
JOB = ("id", "owner_id", "project_id", "dataset_id", "dataset_sha256", "method_id", "request_sha256")
CONTROL = ("job_id", "owner_id", "project_id", "dataset_id", "dataset_sha256", "method_id", "request_sha256")
EDGE = ("child_dataset_id", "parent_dataset_id", "parent_dataset_sha256", "owner_id", "project_id", "raw_asset_id", "root_dataset_id")

_tables = [
    Table("physical_dataset_families", cols(("root_dataset_id", "raw_asset_id", "project_id"), ("owner_id",), extra=(
        ("parser_version", ("T", 80)), ("state", ("E", "pending", "published")), ("next_ordinal", ("I", 2, J)),
        ("published_count", ("I", 0, 64)), ("reserved_count", ("I", 0, 64)), ("created_us", ("I", 0, J)),
    )), ("root_dataset_id",), (
        ("ck_family_capacity", "published_count+reserved_count<=64"),
        ("ck_family_state", "(state='pending' AND published_count=0 AND reserved_count=1 AND next_ordinal=2) OR (state='published' AND published_count>=1)"),
    ), (("uq_family_raw_parser", ("raw_asset_id", "parser_version")), ("uq_family_identity", FAMILY)), (
        ("fk_family_raw", ("raw_asset_id", "owner_id", "project_id"), "raw_assets", ("id", "owner_id", "project_id")),
    ), (("ix_family_owner", ("owner_id", "project_id"), False, None),)),
    Table("physical_dataset_edges", cols(("child_dataset_id", "parent_dataset_id", "project_id", "raw_asset_id", "root_dataset_id"),
        ("owner_id",), ("parent_dataset_sha256",), (("role", ("E", "scientific_input")), ("child_kind", ("E", "derived")))),
        ("child_dataset_id",), (("ck_edge_distinct", "child_dataset_id<>parent_dataset_id"),), (("uq_edge_binding", EDGE),), (
            ("fk_edge_child", ("child_dataset_id", "owner_id", "project_id", "raw_asset_id", "root_dataset_id", "child_kind"),
             "observation_datasets", ("id", "owner_id", "project_id", "raw_asset_id", "root_dataset_id", "kind")),
            ("fk_edge_parent", ("parent_dataset_id", "owner_id", "project_id", "raw_asset_id", "root_dataset_id", "parent_dataset_sha256"),
             "observation_datasets", DATASET),
        ), (("ix_edge_parent", ("parent_dataset_id",), False, None),)),
    Table("physical_job_controls", cols(("job_id", "project_id", "dataset_id", "root_dataset_id", "raw_asset_id", "stage_id"),
        ("owner_id",), ("dataset_sha256", "request_sha256", "raw_sha256", "submitted_parameters_sha256", "scientific_request_sha256", "module_manifest_sha256", "admission_receipt_sha256"), (
            ("method_id", ("E", CORRECTION, TRANSFORM)), ("raw_bytes", ("I", 1, 16*M)), ("request_bytes", ("B", 34*M)),
            ("module_manifest_bytes", ("B", 65536)), ("parent_production_bytes", ("B", M), True),
            ("permanent_reservation_bytes", ("I", 0, 128*M)), ("created_us", ("I", 0, J)),
        )), ("job_id",), (), (("uq_control_binding", CONTROL), ("uq_control_stage", ("stage_id",))), (
            ("fk_control_job", CONTROL, "processing_jobs", JOB),
            ("fk_control_input", INPUT, "observation_datasets", DATASET),
        ), (("ix_control_owner", ("owner_id",), False, None),)),
    Table("physical_dataset_productions", cols(("child_dataset_id", "job_id", "root_dataset_id", "project_id", "raw_asset_id", "parent_dataset_id"),
        ("owner_id",), ("parent_dataset_sha256", "request_sha256", "submitted_parameters_sha256", "scientific_request_sha256", "scientific_result_sha256", "module_manifest_sha256", "result_sha256"), (
            ("method_id", ("E", CORRECTION, TRANSFORM)), ("result_bytes", ("I", 1, 64*M)), ("scientific_verdict", ("E", "passed", "non_pass")),
            *((n, "H", True) for n in ("adapter_result_sha256", "adapter_receipt_sha256", "core_result_sha256", "submitted_config_sha256", "normalized_config_sha256")),
            ("adapter_receipt_bytes", ("B", 65536), True),
        )), ("child_dataset_id",), (("ck_production_method",
            f"(method_id='{CORRECTION}' AND scientific_verdict='passed' AND adapter_result_sha256=scientific_result_sha256 AND " +
            " AND ".join(n + " IS NOT NULL" for n in ("adapter_result_sha256", "adapter_receipt_sha256", "core_result_sha256", "submitted_config_sha256", "normalized_config_sha256", "adapter_receipt_bytes")) +
            f") OR (method_id='{TRANSFORM}' AND " + " AND ".join(n + " IS NULL" for n in ("adapter_result_sha256", "adapter_receipt_sha256", "core_result_sha256", "submitted_config_sha256", "normalized_config_sha256", "adapter_receipt_bytes")) + ")"),),
        (("uq_production_job", ("job_id",)),), (
            ("fk_production_edge", EDGE, "physical_dataset_edges", EDGE),
            ("fk_production_control", ("job_id", "owner_id", "project_id", "parent_dataset_id", "parent_dataset_sha256", "method_id", "request_sha256"), "physical_job_controls", CONTROL),
        ), (("ix_production_root", ("root_dataset_id",), False, None),)),
    Table("physical_publication_intents", cols(("intent_id", "project_id", "raw_asset_id", "root_dataset_id", "child_dataset_id", "stage_id"),
        ("owner_id",), extra=(
            ("kind", ("E", "root", "job")), ("parser_version", ("T", 80)), ("ordinal", ("I", 1, J)),
            ("job_id", "U", True), ("parent_dataset_id", "U", True), ("parent_dataset_sha256", "H", True), ("request_sha256", "H", True),
            ("permanent_reservation_bytes", ("I", 0, 16*M)), ("phase", ("E", "prepared")), ("created_us", ("I", 0, J)),
        )), ("intent_id",), (("ck_intent_kind", f"(kind='root' AND child_dataset_id=root_dataset_id AND ordinal=1 AND permanent_reservation_bytes={16*M} AND job_id IS NULL AND parent_dataset_id IS NULL AND parent_dataset_sha256 IS NULL AND request_sha256 IS NULL) OR (kind='job' AND child_dataset_id<>root_dataset_id AND ordinal>=2 AND permanent_reservation_bytes=0 AND job_id IS NOT NULL AND parent_dataset_id IS NOT NULL AND parent_dataset_sha256 IS NOT NULL AND request_sha256 IS NOT NULL)"),),
        (("uq_intent_child", ("child_dataset_id",)), ("uq_intent_ordinal", ("root_dataset_id", "ordinal")), ("uq_intent_stage", ("stage_id",))), (
            ("fk_intent_family", FAMILY, "physical_dataset_families", FAMILY),
            ("fk_intent_job", ("job_id", "owner_id", "project_id", "parent_dataset_id", "parent_dataset_sha256"), "processing_jobs", ("id", "owner_id", "project_id", "dataset_id", "dataset_sha256")),
            ("fk_intent_parent", ("parent_dataset_id", "owner_id", "project_id", "raw_asset_id", "root_dataset_id", "parent_dataset_sha256"), "observation_datasets", DATASET),
        ), (("uq_intent_job", ("job_id",), True, "job_id IS NOT NULL"), ("ix_intent_owner", ("owner_id",), False, None))),
    Table("physical_publication_targets", cols(("intent_id", "artifact_id"), hashes=("sha256",), extra=(
        ("kind", ("E", "dataset", "result")), ("storage_key", ("T", 180)), ("bytes", ("I", 1, 64*M)),
    )), ("intent_id", "kind"), (), (("uq_target_key", ("storage_key",)),), (("fk_target_intent", ("intent_id",), "physical_publication_intents", ("intent_id",)),)),
    Table("physical_custody_batches", cols(("batch_id", "project_id", "origin_id"), ("owner_id",), extra=(
        ("origin_kind", ("E", "root_stage", "job_stage", "publication_abandon", "project_deletion")),
        *((n, "U", True) for n in ("stage_id", "deletion_receipt_id", "raw_asset_id")),
        ("raw_sha256", "H", True), ("raw_bytes", ("I", 1, 16*M), True), ("parser_version", ("T", 80), True),
        ("method_id", ("E", CORRECTION, TRANSFORM), True),
        ("state", ("E", "reserved", "active", "sealed", "cleanup_pending", "quarantined", "removed")),
        ("capacity_bytes", ("I", 1, 1073741824*4096)), ("charged_bytes", ("I", 0, J)),
        ("inventory_bytes", ("B", 4*M), True), ("inventory_sha256", "H", True), ("created_us", ("I", 0, J)),
        ("sealed_us", ("I", 0, J), True), ("removed_us", ("I", 0, J), True),
    )), ("batch_id",), (
        ("ck_custody_origin", "((origin_kind IN ('root_stage','job_stage') AND stage_id IS NOT NULL AND deletion_receipt_id IS NULL) OR (origin_kind='publication_abandon' AND stage_id IS NULL AND deletion_receipt_id IS NULL) OR (origin_kind='project_deletion' AND stage_id IS NULL AND deletion_receipt_id IS NOT NULL)) AND ((origin_kind='project_deletion' AND raw_asset_id IS NULL AND raw_sha256 IS NULL AND raw_bytes IS NULL AND parser_version IS NULL) OR (origin_kind<>'project_deletion' AND raw_asset_id IS NOT NULL AND raw_sha256 IS NOT NULL AND raw_bytes IS NOT NULL AND parser_version='gravity-stations-json/v1'))"),
        ("ck_custody_capacity", f"(origin_kind='root_stage' AND method_id IS NULL AND capacity_bytes={32*M}) OR (origin_kind='job_stage' AND ((method_id='{CORRECTION}' AND capacity_bytes={256*M}) OR (method_id='{TRANSFORM}' AND capacity_bytes={512*M}))) OR (origin_kind='publication_abandon' AND ((method_id IS NULL AND capacity_bytes={16*M}) OR (method_id='{CORRECTION}' AND capacity_bytes={80*M}) OR (method_id='{TRANSFORM}' AND capacity_bytes={128*M}))) OR (origin_kind='project_deletion' AND method_id IS NULL)"),
        ("ck_custody_state", "(state IN ('reserved','active') AND inventory_bytes IS NULL AND inventory_sha256 IS NULL AND sealed_us IS NULL AND removed_us IS NULL AND ((origin_kind='project_deletion' AND charged_bytes=0) OR (origin_kind<>'project_deletion' AND charged_bytes=capacity_bytes))) OR (state IN ('sealed','cleanup_pending') AND inventory_bytes IS NOT NULL AND inventory_sha256 IS NOT NULL AND sealed_us IS NOT NULL AND removed_us IS NULL) OR (state='quarantined' AND removed_us IS NULL AND ((inventory_bytes IS NULL AND inventory_sha256 IS NULL AND sealed_us IS NULL) OR (inventory_bytes IS NOT NULL AND inventory_sha256 IS NOT NULL AND sealed_us IS NOT NULL))) OR (state='removed' AND inventory_bytes IS NOT NULL AND inventory_sha256 IS NOT NULL AND sealed_us IS NOT NULL AND removed_us IS NOT NULL AND charged_bytes=0)"),
        ("ck_custody_charge", "(state NOT IN ('sealed','cleanup_pending') OR charged_bytes<=capacity_bytes) AND (state<>'quarantined' OR charged_bytes>=capacity_bytes OR inventory_bytes IS NOT NULL)"),
    ), (("uq_custody_origin", ("origin_kind", "origin_id")),), (("fk_custody_owner", ("owner_id",), "user", ("id",)),), (
        ("uq_custody_stage", ("stage_id",), True, "stage_id IS NOT NULL"),
        ("ix_custody_owner_state", ("owner_id", "state"), False, None), ("ix_custody_project", ("project_id",), False, None),
    )),
    Table("physical_custody_files", cols(("batch_id",), extra=(
        ("ordinal", ("I", 1, 4096)), ("role", ("E", "raw_delete", "dataset_copy", "result_copy", "request_spool", "input_spool", "scientific_output", "stdout_log", "stderr_log", "completion", "cache")),
        ("location", ("E", "stage", "pending_target", "deleting_raw", "deleting_derived")), ("artifact_id", "U", True),
        ("leaf", ("T", 180)), ("max_bytes", ("I", 1, 1073741824)), ("actual_bytes", ("I", 0, 1073741824), True),
        ("actual_sha256", "H", True), ("state", ("E", "reserved", "present", "removed")),
    )), ("batch_id", "ordinal"), (
        ("ck_custody_file_measurement", "(state='reserved' AND actual_bytes IS NULL AND actual_sha256 IS NULL) OR (state IN ('present','removed') AND actual_bytes IS NOT NULL AND actual_sha256 IS NOT NULL)"),
        ("ck_custody_file_role", "(role IN ('raw_delete','dataset_copy','result_copy') AND artifact_id IS NOT NULL) OR (role NOT IN ('raw_delete','dataset_copy','result_copy') AND artifact_id IS NULL)"),
        ("ck_custody_file_capacity", "actual_bytes IS NULL OR actual_bytes<=max_bytes"),
    ), (("uq_custody_leaf", ("batch_id", "location", "leaf")),), (("fk_custody_batch", ("batch_id",), "physical_custody_batches", ("batch_id",)),)),
    Table("physical_deletion_extensions", cols(("receipt_id", "project_id"), ("owner_id",), ("tombstone_sha256",), (
        ("schema_tag", ("E", "geophysics.physical-deletion/v2")), ("tombstone_bytes", ("B", 16*M)),
    )), ("receipt_id",), (), (("uq_deletion_extension_project", ("project_id",)),), (
        ("fk_deletion_extension_receipt", ("receipt_id", "owner_id", "project_id"), "deletion_receipts", ("id", "owner_id", "project_id")),
    )),
    Table("physical_runtime_control", cols(("deployment_id", "storage_generation"), extra=(
        ("singleton", ("I", 1, 1)), ("lease_generation", ("I", 1, J)), ("inventory_state", ("E", "closed", "clean", "quarantined")),
        ("source_policy_sha256", "H", True), ("last_clean_inventory_sha256", "H", True), ("audited_us", ("I", 0, J), True),
    )), ("singleton",), (("ck_runtime_inventory", "(source_policy_sha256 IS NOT NULL AND last_clean_inventory_sha256 IS NOT NULL AND audited_us IS NOT NULL) OR (inventory_state<>'clean' AND source_policy_sha256 IS NULL AND last_clean_inventory_sha256 IS NULL AND audited_us IS NULL)"),)),
]
TABLES = MappingProxyType({t.name: t for t in _tables})


DATASET_COLUMNS = tuple(column(*c) for c in (
    ("kind", ("E", "root", "derived")), ("root_dataset_id", "U"), ("parent_dataset_id", "U", True), ("payload_schema", ("T", 80)),
))
DATASET_REGISTRY = (
    ("root", "gravity-station-csv/v1", "gravity_station", "geophysics.observation-dataset/v1"),
    ("root", "edi-strict-envelope/v1", "edi_transfer_function", "geophysics.observation-dataset/v1"),
    ("root", "gravity-stations-json/v1", "gravity_physical_station", "gravity-stations-1"),
    ("derived", "gravity-stations-json/v1", "gravity_physical_station", "gravity-station-adapter-result-1"),
    ("derived", "gravity-stations-json/v1", "gravity_equivalent_source_transform", "gravity-transform-result-1"),
)
DATASET_CHECKS = (
    ("ck_dataset_kind", "(kind='root' AND version=1 AND root_dataset_id=id AND parent_dataset_id IS NULL) OR (kind='derived' AND typeof(version)='integer' AND version BETWEEN 2 AND 9007199254740991 AND parent_dataset_id IS NOT NULL AND parent_dataset_id<>id AND root_dataset_id<>id)"),
    ("ck_dataset_payload", " OR ".join("(" + " AND ".join(f"{n}='{v}'" for n, v in zip(("kind", "parser_version", "modality", "payload_schema"), values)) + ")" for values in DATASET_REGISTRY)),
)
DATASET_INDEXES = (
    ("uq_dataset_identity", DATASET, True, None),
    ("uq_dataset_kind_identity", ("id", "owner_id", "project_id", "raw_asset_id", "root_dataset_id", "kind"), True, None),
    ("uq_dataset_parent_identity", ("id", "owner_id", "project_id", "raw_asset_id", "root_dataset_id"), True, None),
    ("uq_dataset_ordinal", ("root_dataset_id", "version"), True, None),
    ("uq_dataset_root_parser", ("raw_asset_id", "parser_version"), True, "kind='root'"),
    ("ix_dataset_root", ("root_dataset_id", "version"), False, None),
)


def candidate_dataset_sql(original: str) -> str:
    """Preserve literal legacy column/FK definitions; remove only raw/parser UNIQUE."""
    import re
    expected = r",?\s*UNIQUE\s*\(raw_asset_id,\s*parser_version\)\s*,?"
    if len(re.findall(expected, original)) != 1:
        raise ValueError("unsupported_legacy_dataset_ddl")
    # Preserve every other literal part, irrespective of constraint ordering.
    original = re.sub(r",\s*UNIQUE\s*\(raw_asset_id,\s*parser_version\)", "", original, count=1)
    original = original.replace("CREATE TABLE observation_datasets", "CREATE TABLE _physical_candidate_datasets", 1)
    added_columns = [column_sql("observation_datasets", c) for c in DATASET_COLUMNS]
    extra = [f"CONSTRAINT {n} CHECK (({p}) IS TRUE)" for n, p in DATASET_CHECKS]
    extra += [foreign_key("fk_dataset_family", FAMILY, "physical_dataset_families", FAMILY), foreign_key(
        "fk_dataset_parent", ("parent_dataset_id", "owner_id", "project_id", "raw_asset_id", "root_dataset_id"),
        "observation_datasets", ("id", "owner_id", "project_id", "raw_asset_id", "root_dataset_id"),
    )]
    body = original.rsplit(")", 1)[0]
    boundary = re.search(r",\s*(?:PRIMARY KEY|UNIQUE|FOREIGN KEY|CHECK|CONSTRAINT)\b", body)
    if boundary is None:
        raise ValueError("unsupported_legacy_dataset_ddl")
    return body[:boundary.start()] + ",\n" + ",\n".join(added_columns) + body[boundary.start():] + ",\n" + ",\n".join(extra) + ")"
