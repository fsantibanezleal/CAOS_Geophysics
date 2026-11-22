"""Positive data dispatch only. No CLI, files, SQLite, native or provider entry."""

from app.physical_contract import (
    LEGACY_DDL, LEGACY_REVISION, PHYSICAL_REVISION, canonical, decode_source,
    parse_record, require,
)


def dispatch_authority(chunks, *, snapshot_schema, database_revision, ddl_sha256,
                       deployment_id, fixture_only, schema_registry=None):
    """Preserve v1's original cap/validator; never fall back from future schemas.

    This returns a parsed authority, NOT a verified archive/database/restore.
    Input must reach complete EOF; all outputs remain local fixture data.
    """
    require(fixture_only is True, "fixture_only")
    value = decode_source(chunks, max_bytes=16*1048576, depth=16, nodes=250000)
    require(type(value) is dict and type(value.get("schema")) is str, "schema")
    pair = (snapshot_schema, database_revision)
    require(pair in (("geophysics.restricted-snapshot/v1", LEGACY_REVISION),
                     ("geophysics.restricted-snapshot/v2", PHYSICAL_REVISION)), "snapshot_pair")
    if pair[1] == LEGACY_REVISION:
        require(ddl_sha256 == LEGACY_DDL, "legacy_ddl")
    else:
        require(schema_registry is not None and schema_registry.get(PHYSICAL_REVISION) == ddl_sha256, "unregistered_schema")
    if value["schema"] == "geophysics.recovery-authority/v1":
        require(pair[1] == LEGACY_REVISION, "authority_pair")
        from scripts.ops_recovery import RecoveryError, validate_authority
        try:
            validate_authority(value, deployment_id, True)
        except RecoveryError:
            require(False, "legacy_authority")
    elif value["schema"] == "geophysics.recovery-authority/v2":
        value = parse_record([canonical(value)], schema_registry=schema_registry)
        require(value["deployment_id"] == deployment_id and value["fixture_only"] is True, "authority_identity")
        require({x["revision"]: x["ddl_sha256"] for x in value["database_schemas"]}.get(database_revision) == ddl_sha256, "authority_ddl")
    else:
        require(False, "unknown_schema")
    return value
