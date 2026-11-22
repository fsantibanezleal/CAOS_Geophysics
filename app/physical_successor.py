"""Exact post-waveform schema extension; no application startup activation."""

import hashlib
import json
import re

from app.physical_persistence import DATASET_REGISTRY, candidate_dataset_sql

PREDECESSOR = "0004_waveform_artifacts"
REVISION = "0005_physical_forest"
PREDECESSOR_DDL = "f2a1a28305e8115d42549bc64508afe8de76f42b8b2e32b516ff753f6f45851f"
PROFILE_ROOTS = (
    ("root", "supplied-profile-original/v1", "ert_profile", "geophysics.observation-dataset/v1"),
    ("root", "supplied-profile-original/v1", "traveltime_profile", "geophysics.observation-dataset/v1"),
)
METHODS = frozenset((
    "gravity.station-outlier-flags/v1", "mt.edi-full-tensor-qc/v1",
    "mt.edi-fixed-thickness-trf/v1", "ert.topographic-profile/v1",
    "traveltime.first-arrival-profile/v1", "seismic.waveform-qc-classical/v1",
))
FORMATS = frozenset((
    "gravity_csv", "magnetic_csv", "traveltime_csv", "ert_csv", "geotiff", "edi",
    "miniseed", "stationxml", "segy", "mth5", "ert_ohm", "traveltime_sgt",
))


def ddl_sha256(connection):
    sql = "SELECT type,name,tbl_name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type,name"
    rows = (connection.exec_driver_sql(sql).fetchall() if hasattr(connection, "exec_driver_sql")
            else connection.execute(sql).fetchall())
    return hashlib.sha256(json.dumps([tuple(r) for r in rows], separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def predecessor_payload(parser, modality):
    """Only existing root tuples; no physical historical producer backfill."""
    for kind, registered, variant, payload in (*DATASET_REGISTRY[:2], *PROFILE_ROOTS):
        if kind == "root" and (parser, modality) == (registered, variant):
            return payload
    if (type(parser) is str and re.fullmatch(r"m08/v1/[0-9a-f]{64}", parser)
            and modality == "waveform_counts_response"):
        return "geophysics.waveform-dataset/v1"
    raise ValueError("unsupported_predecessor_dataset")


def successor_dataset_sql(original):
    sql = candidate_dataset_sql(original)
    old = " OR ".join("(" + " AND ".join(f"{n}='{v}'" for n, v in zip(
        ("kind", "parser_version", "modality", "payload_schema"), values)) + ")" for values in DATASET_REGISTRY)
    extra = ["(" + " AND ".join(f"{n}='{v}'" for n, v in zip(
        ("kind", "parser_version", "modality", "payload_schema"), values)) + ")" for values in PROFILE_ROOTS]
    extra.append("(kind='root' AND modality='waveform_counts_response' AND payload_schema='geophysics.waveform-dataset/v1' "
                 "AND substr(parser_version,1,7)='m08/v1/' AND length(parser_version)=71 "
                 "AND substr(parser_version,8) NOT GLOB '*[^0-9a-f]*')")
    if sql.count(old) != 1:
        raise ValueError("physical_dictionary_binding")
    return sql.replace(old, old + " OR " + " OR ".join(extra), 1)
