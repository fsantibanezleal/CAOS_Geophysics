"""Actual file/SQL publication cuts; Windows fixtures are not native barriers."""

from uuid import uuid4

from alembic import command
import pytest

from app.physical_contract import byte_sha, canonical
from app.physical_persistence import M
from app.physical_roots import prepare_root, publish_root
from app.physical_successor import REVISION
from app.physical_wire import make_root_envelope
from tests.api.test_physical_forest import connect
from tests.api.test_physical_persistence_schema import insert
from tests.api.test_physical_successor import successor as successor
from tests.api.test_physical_wire import survey as survey


class FixtureFiles:
    """Real bounded bytes/namespace for SQL tests, NOT Linux durability proof."""
    def __init__(self, root):
        self.root = root

    def read(self, key, *, cap, expected_bytes, expected_sha256):
        path = self.root / key
        assert path.resolve().is_relative_to(self.root.resolve())
        body = path.read_bytes()
        if path.is_symlink() or path.stat().st_nlink != 1 or len(body) > cap or len(body) != expected_bytes or byte_sha(body) != expected_sha256:
            raise ValueError("fixture_file_changed")
        return body

    def verify_directory(self, key, *, expected_files):
        path = self.root / key
        if path.is_symlink() or set(p.name for p in path.iterdir()) != set(expected_files):
            raise ValueError("fixture_namespace_changed")


@pytest.fixture
def root_case(successor, survey):
    config, path = successor
    command.upgrade(config, REVISION)
    root_dir = path.parent / "private"
    root_dir.mkdir()
    files = FixtureFiles(root_dir)
    owner, project, source_id, raw, root, batch, intent = [str(uuid4()) for _ in range(7)]
    original = b" \n" + canonical(survey) + b"\n"
    source = dict(provider="Authored structural control", exact_url=None, doi=None, citation=None,
                  rights_decision="mirror", rights_statement="Original structural test data", attribution="Control author")
    body = make_root_envelope(survey, dataset_id=root, owner_id=owner, project_id=project,
                              raw_asset_id=raw, raw_sha256=byte_sha(original), raw_bytes=len(original), source=source)
    raw_key = f"projects/{owner}/{project}/{raw}"
    stage = root_dir / f".job-staging/{root}"
    stage.mkdir(parents=True)
    for name, data in (("input.json", original), ("dataset.json", body)):
        (stage/name).write_bytes(data)
    raw_path = root_dir / raw_key
    raw_path.parent.mkdir(parents=True)
    raw_path.write_bytes(original)
    slots = [dict(ordinal=i, role=role, location="stage", artifact_id=identifier, leaf=leaf,
                  max_bytes=16*M, actual_bytes=len(data), actual_sha256=byte_sha(data))
             for i, (role, identifier, leaf, data) in enumerate((
                 ("input_spool", None, "input.json", original),
                 ("dataset_copy", root, "dataset.json", body)), 1)]
    inventory = dict(schema="geophysics.physical-custody/v1", batch_id=batch, owner_id=owner, project_id=project,
                     origin_kind="root_stage", origin_id=root, stage_id=root, deletion_receipt_id=None,
                     raw_asset_id=raw, raw_sha256=byte_sha(original), raw_bytes=len(original),
                     parser_version="gravity-stations-json/v1", method_id=None, capacity_bytes=32*M,
                     initial_files=slots, removed_ordinals=[])
    inv_body = canonical(inventory)
    with connect(path) as db:
        db.execute("INSERT INTO user VALUES(?,?,?,1,0,1)", (owner, owner+"@example.org", "fixture-not-a-login"))
        insert(db, "projects", dict(id=project, owner_id=owner, name="Structural control", description="", created_at="2026-10-08 01:00:00", updated_at="2026-10-08 01:00:00"))
        insert(db, "source_records", dict(source, id=source_id, project_id=project, owner_id=owner,
               original_filename="survey.json", version=1, retrieved_at="2026-10-08 01:00:00",
               declared_format="gravity_stations_json", private_storage_permission="attested",
               sha256=byte_sha(original), expected_bytes=len(original)))
        insert(db, "raw_assets", dict(id=raw, owner_id=owner, project_id=project, source_id=source_id,
               filename="survey.json", client_mime="application/json", detected_format="gravity_stations_json",
               byte_count=len(original), sha256=byte_sha(original), storage_key=raw_key,
               physical_metadata='{}', validation_status="raw_metadata_checked", created_at="2026-10-08 01:00:00"))
        insert(db, "account_usage", dict(user_id=owner, raw_bytes=len(original)))
        header = {k:v for k,v in inventory.items() if k not in ("schema", "initial_files", "removed_ordinals")}
        insert(db, "physical_custody_batches", dict(header, state="sealed", charged_bytes=len(original)+len(body),
               inventory_bytes=inv_body, inventory_sha256=byte_sha(inv_body), created_us=1, sealed_us=2, removed_us=None))
        for slot in slots:
            insert(db, "physical_custody_files", dict(slot, batch_id=batch, state="present"))
    return path, files, dict(owner_id=owner, project_id=project, raw_asset_id=raw, root_dataset_id=root,
                            intent_id=intent, created_us=2), body, original


def install_fixture(files, values, body):
    key = f"derived/{values['owner_id']}/{values['project_id']}/datasets/{values['root_dataset_id']}.json"
    target = files.root / key
    target.parent.mkdir(parents=True)
    with target.open("xb") as stream:
        stream.write(body)


def publish_values(values):
    return dict(owner_id=values["owner_id"], project_id=values["project_id"], intent_id=values["intent_id"],
                created_at="2026-10-08 01:01:00")


def test_root_publication_retains_exact_original_and_distinct_stage_copies(root_case):
    path, files, values, body, original = root_case
    with connect(path) as db:
        prepare_root(db, files, **values)
        assert db.execute("SELECT count(*) FROM observation_datasets").fetchone() == (0,)
        assert db.execute("SELECT state,published_count,reserved_count FROM physical_dataset_families").fetchone() == ("pending", 0, 1)
        install_fixture(files, values, body)
        assert publish_root(db, files, **publish_values(values)) == values["root_dataset_id"]
        assert db.execute("SELECT kind,version,sha256,byte_count FROM observation_datasets").fetchone() == ("root", 1, byte_sha(body), len(body))
        assert db.execute("SELECT state,published_count,reserved_count FROM physical_dataset_families").fetchone() == ("published", 1, 0)
        assert db.execute("SELECT state,charged_bytes FROM physical_custody_batches").fetchone() == ("cleanup_pending", len(original)+len(body))
        assert db.execute("SELECT count(*) FROM physical_publication_intents").fetchone() == (0,)
        assert db.execute("SELECT count(*) FROM physical_dataset_productions").fetchone() == (0,)
        assert (files.root / f".job-staging/{values['root_dataset_id']}/input.json").read_bytes() == original
        assert db.execute("PRAGMA foreign_key_check").fetchall() == []


@pytest.mark.parametrize("cut", ["prepared", "published"])
def test_root_uncertain_cut_preserves_prepared_files_without_adoption(root_case, cut):
    path, files, values, body, _ = root_case
    def fail(point):
        if point == cut:
            raise RuntimeError("injected_root_cut")
    with connect(path) as db:
        if cut == "prepared":
            with pytest.raises(RuntimeError):
                prepare_root(db, files, **values, failure_cut=fail)
            assert db.execute("SELECT count(*) FROM physical_dataset_families").fetchone() == (0,)
        else:
            prepare_root(db, files, **values)
            install_fixture(files, values, body)
            with pytest.raises(RuntimeError):
                publish_root(db, files, **publish_values(values), failure_cut=fail)
            assert db.execute("SELECT count(*) FROM physical_publication_intents").fetchone() == (1,)
            assert db.execute("SELECT state FROM physical_custody_batches").fetchone() == ("sealed",)
        assert db.execute("SELECT count(*) FROM observation_datasets").fetchone() == (0,)


@pytest.mark.parametrize("change", ["missing_target", "foreign_target", "unknown_stage", "changed_original", "unsealed", "rehashed_source"])
def test_root_unknown_or_rehashed_identity_is_not_publishable(root_case, change):
    path, files, values, body, _ = root_case
    with connect(path) as db:
        prepare_root(db, files, **values)
        if change != "missing_target":
            install_fixture(files, values, body)
        if change == "foreign_target":
            db.execute("UPDATE physical_publication_targets SET sha256=?", ("a"*64,))
        elif change == "unknown_stage":
            (files.root / f".job-staging/{values['root_dataset_id']}/unknown.bin").write_bytes(b"unknown")
        elif change == "changed_original":
            raw_key = db.execute("SELECT storage_key FROM raw_assets").fetchone()[0]
            (files.root / raw_key).write_bytes(b"changed")
        elif change == "unsealed":
            db.execute("UPDATE physical_custody_batches SET state='quarantined'")
        elif change == "rehashed_source":
            db.execute("UPDATE source_records SET citation='changed supplied source'")
        with pytest.raises((ValueError, OSError)):
            publish_root(db, files, **publish_values(values))
        assert db.execute("SELECT count(*) FROM observation_datasets").fetchone() == (0,)
        assert db.execute("SELECT count(*) FROM physical_publication_intents").fetchone() == (1,)


def test_native_publication_fixture_is_external_and_has_actual_successor_schema(root_case):
    """Retain a reproducible input, not a native/OS or scientific PASS receipt."""
    import json
    from app.physical_forest import SUCCESSOR_DDL
    from app.physical_successor import ddl_sha256
    path, files, values, _, _ = root_case
    with connect(path) as db:
        assert ddl_sha256(db) == SUCCESSOR_DDL
    record = dict(schema="geophysics.physical-native-publication-input/v1", fixture_only=True,
                  values=values, database=str(path), private_root=str(files.root),
                  ddl_sha256=SUCCESSOR_DDL)
    (path.parent / "native-publication-input.json").write_text(json.dumps(record, sort_keys=True), encoding="utf-8")
