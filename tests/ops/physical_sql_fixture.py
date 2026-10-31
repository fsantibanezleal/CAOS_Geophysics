"""Native SQL fixture data only; no Alembic registry or collected tests.

Literal predecessor seed/projection extracted from the preserved historical
alternative0004 test. Current successor tests do not import its registry policy.
"""

from uuid import uuid4


def seed(db, *, parser="gravity-station-csv/v1", modality="gravity_station"):
    owner, project, source, raw, dataset, job = [str(uuid4()) for _ in range(6)]
    time = "2026-09-27 12:00:00.123456"
    native = ' {"epsilon":1.0,"label":"Señal", "nested":null} '
    db.execute("INSERT INTO user VALUES (?,?,?,1,0,1)", (owner, owner + "@example.org", "fixture-hash"))
    db.execute("INSERT INTO projects VALUES (?,?,?,?,?,?)", (project, owner, "Survey", "", time, time))
    db.execute(
        "INSERT INTO source_records(id,project_id,owner_id,original_filename,version,provider,retrieved_at,"
        "rights_statement,rights_decision,declared_format,sha256,attribution) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (source, project, owner, "legacy.csv", 1, "fixture", time, "original", "mirror", "gravity_csv", "a"*64, "fixture"),
    )
    db.execute(
        "INSERT INTO raw_assets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (raw, project, owner, source, "legacy.csv", "text/csv", "gravity_csv", 7, "a"*64,
         f"projects/{owner}/{project}/{raw}", native, "valid", time),
    )
    db.execute("INSERT INTO observation_datasets VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", (
        dataset, project, owner, raw, 1, parser, modality, 2, "a"*64, "b"*64, 9,
        f"derived/{owner}/{project}/datasets/{dataset}.json", time,
    ))
    db.execute(
        "INSERT INTO processing_jobs(id,project_id,owner_id,dataset_id,dataset_sha256,method_id,request_json,"
        "request_sha256,preflight,state,cancel_requested,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
        (job, project, owner, dataset, "b"*64, "gravity.station-outlier-flags/v1", native, "c"*64, native, "failed", 0, time),
    )
    db.execute("INSERT INTO account_usage VALUES (?,?)", (owner, 7))
    db.execute("INSERT INTO deletion_receipts VALUES (?,?,?,?,?,?,?,?)", (
        str(uuid4()), str(uuid4()), owner, time, ' ["' + "d"*64 + '"] ', "external_pending", None, None,
    ))
    db.commit()
    return owner, project, raw, dataset, job


def inventory(db):
    tables = [r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name<>'alembic_version'")]
    result = {}
    for table in tables:
        cols = [r[1] for r in db.execute(f'PRAGMA table_info("{table}")')]
        projection = ",".join(f'"{c}",typeof("{c}")' for c in cols)
        result[table] = (cols, list(db.execute(f'SELECT {projection} FROM "{table}" ORDER BY 1')))
    return result


def insert(db, table, row):
    db.execute(f"INSERT INTO {table} ({','.join(row)}) VALUES ({','.join('?' for _ in row)})", tuple(row.values()))
