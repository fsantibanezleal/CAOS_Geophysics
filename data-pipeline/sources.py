"""Reviewed source ledger and immutable, ignored local raw-asset acquisition.

This is local build tooling, not a package or an arbitrary-URL downloader.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]
LEDGER = ROOT / "data/source-ledger.json"
FORMATS = {"simpeg-obs-tar-gz", "edi-transfer-function", "pygimli-ert-ohm", "research-zip", "fgdc-metadata-xml",
           "pygimli-traveltime-sgt", "stead-metadata-csv", "generated-case"}
RIGHTS = {"mirror", "provider-link-only", "derivative-only", "forbidden"}
FETCH_HOSTS = {"storage.googleapis.com", "raw.githubusercontent.com", "data.earthscope.org", "data.usgs.gov", "zenodo.org"}
MIME = {"simpeg-obs-tar-gz": "application/gzip", "edi-transfer-function": "text/plain",
        "pygimli-ert-ohm": "text/plain", "pygimli-traveltime-sgt": "text/plain",
        "research-zip": "application/zip", "fgdc-metadata-xml": "application/xml"}
MAX_SOURCE_BYTES = 200_000_000
CHUNK_BYTES = 128 * 1024
ARCHIVE_LIMITS = {"max_entries": 512, "max_expanded_bytes": 500_000_000,
                  "max_member_bytes": MAX_SOURCE_BYTES, "max_expansion_ratio": 1000}


class SourceError(ValueError):
    """A source could not pass its declared acquisition contract."""


def archive_member_key(name: str) -> PurePosixPath:
    """Portable, canonical file/directory name; no Windows aliases or devices."""
    if not isinstance(name, str) or not re.fullmatch(r"[A-Za-z0-9_. /-]+", name):
        raise SourceError("Unsafe ZIP path: require a portable relative name")
    path = PurePosixPath(name)
    devices = {"con", "prn", "aux", "nul", *(f"com{i}" for i in range(10)), *(f"lpt{i}" for i in range(10))}
    if (not path.parts or path.is_absolute() or path.as_posix() != name
            or any(part in {".", ".."} or part.endswith((".", " "))
                   or part.split(".")[0].rstrip(" ").lower() in devices for part in path.parts)):
        raise SourceError("Unsafe ZIP path: noncanonical path or Windows alias")
    return path


def validate_archive_contract(contract: dict) -> None:
    """Validate reviewed limits and selected pins before reading an archive."""
    required = {*ARCHIVE_LIMITS, "selected_members"}
    if not isinstance(contract, dict) or set(contract) != required:
        raise SourceError("Research ZIP archive_contract needs exact limits and selected_members")
    for field, ceiling in ARCHIVE_LIMITS.items():
        value = contract[field]
        numeric = type(value) in (int, float) if field == "max_expansion_ratio" else type(value) is int
        if not numeric or not 0 < value <= ceiling or not math.isfinite(value):
            raise SourceError(f"Archive {field} limit must be positive, finite and at most {ceiling}")
    selected = contract["selected_members"]
    if not isinstance(selected, dict) or not 0 < len(selected) <= contract["max_entries"]:
        raise SourceError("Archive selected_members count limit")
    names = set()
    total = 0
    for name, pin in selected.items():
        key = archive_member_key(name)
        if key.suffix.lower() not in {".csv", ".pdf"} or name.casefold() in names:
            raise SourceError("Archive selection must contain distinct portable CSV/PDF members")
        names.add(name.casefold())
        if (not isinstance(pin, dict) or set(pin) != {"bytes", "sha256"}
                or type(pin["bytes"]) is not int or not 0 < pin["bytes"] <= contract["max_member_bytes"]
                or not isinstance(pin["sha256"], str) or not re.fullmatch(r"[0-9a-f]{64}", pin["sha256"])):
            raise SourceError(f"Selected member needs bounded byte limit and lowercase SHA-256: {name}")
        total += pin["bytes"]
    if total > contract["max_expanded_bytes"]:
        raise SourceError("Selected member total expansion limit")
    for name in names:
        if any(parent.as_posix() in names for parent in PurePosixPath(name).parents if parent.as_posix() != "."):
            raise SourceError("Archive selection has a file/parent collision")


def _https(url: str, *, fetch: bool = False) -> None:
    parsed = urlsplit(url)
    try:
        port = parsed.port
    except ValueError as error:
        raise SourceError(f"Invalid HTTPS provider port in {url}") from error
    if (parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password
            or port not in (None, 443) or parsed.fragment):
        raise SourceError(f"Require an HTTPS provider URL without credentials, port override or fragment: {url}")
    if fetch and parsed.hostname not in FETCH_HOSTS:
        raise SourceError(f"Fetch host {parsed.hostname} is not in the reviewed provider allowlist")


def _raw_key(value: str) -> PurePosixPath:
    if not isinstance(value, str) or "\\" in value:
        raise SourceError(f"Raw storage key must use a relative POSIX path under data/downloads/: {value!r}")
    path = PurePosixPath(value)
    if (path.is_absolute() or len(path.parts) < 3 or path.parts[:2] != ("data", "downloads")
            or any(part in ("", ".", "..") for part in path.parts)):
        raise SourceError(f"Raw storage key must stay under data/downloads/: {value!r}")
    return path


def _verified_metadata_evidence(record: dict) -> None:
    evidence = record.get("verification_evidence")
    if (record["format"] != "stead-metadata-csv" or not isinstance(evidence, dict)
            or set(evidence) != {"path", "sha256"}
            or not isinstance(evidence["sha256"], str)
            or not re.fullmatch(r"[0-9a-f]{64}", evidence["sha256"])):
        raise SourceError("Verified metadata requires a pinned aggregate profile")
    key = archive_member_key(evidence["path"])
    if len(key.parts) != 4 or key.parts[:3] != ("data", "derived", "phase") or key.suffix != ".json":
        raise SourceError("Metadata evidence must be a profile under data/derived/phase")
    profile = ROOT.joinpath(*key.parts)
    for item in (profile, *profile.parents):
        if item.is_symlink() or getattr(item, "is_junction", lambda: False)():
            raise SourceError("Metadata evidence cannot traverse a symlink or junction")
        if item == ROOT:
            break
    try:
        with profile.open("rb") as handle:
            raw = handle.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024 or hashlib.sha256(raw).hexdigest() != evidence["sha256"]:
            raise SourceError("Metadata profile byte/hash mismatch")
        def pairs(items):
            result = {}
            for name, item in items:
                if name in result:
                    raise SourceError("Metadata profile contains duplicate keys")
                result[name] = item
            return result

        def constant(_value):
            raise SourceError("Metadata profile contains a nonfinite constant")

        value = json.loads(raw, object_pairs_hook=pairs, parse_constant=constant)
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError) as error:
        raise SourceError("Metadata aggregate profile unavailable or invalid") from error
    source = value.get("source") if isinstance(value, dict) else None
    rows = value.get("rows") if isinstance(value, dict) else None
    if (not isinstance(value, dict) or value.get("schema") != "caos.stead-metadata-profile.v1" or not isinstance(source, dict)
            or not isinstance(rows, dict) or type(rows.get("total")) is not int or rows["total"] <= 0
            or type(source.get("bytes")) is not int or source["bytes"] != record["expected_bytes"]
            or source.get("sha256") != record["sha256"] or source.get("url") != record["object_url"]
            or source.get("waveforms_downloaded_by_this_receipt") is not False):
        raise SourceError("Metadata profile source identity mismatch")


def load_ledger(path: Path = LEDGER) -> dict[str, dict]:
    try:
        ledger = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise SourceError(f"Cannot read source ledger {path}: {error}") from error
    if ledger.get("schema") != "inverse-earth.sources/v2" or not isinstance(ledger.get("sources"), list):
        raise SourceError("Source ledger must declare inverse-earth.sources/v2 and a sources list")
    records: dict[str, dict] = {}
    raw_keys: set[str] = set()
    required = {"source_id", "name", "provider", "provider_url", "object_url", "acquisition", "format",
                "expected_bytes", "sha256", "raw_path", "rights_decision", "rights_statement", "citation", "use"}
    for record in ledger["sources"]:
        if not isinstance(record, dict) or not required.issubset(record):
            raise SourceError(f"Every source needs {', '.join(sorted(required))}")
        source_id = record["source_id"]
        if not isinstance(source_id, str) or not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", source_id):
            raise SourceError(f"Invalid stable source_id {source_id!r}")
        if source_id in records:
            raise SourceError(f"Duplicate source_id {source_id}")
        if record["format"] not in FORMATS or record["rights_decision"] not in RIGHTS:
            raise SourceError(f"{source_id}: unsupported format or rights decision")
        for field in ("name", "provider", "rights_statement", "citation", "use"):
            if not isinstance(record[field], str) or not record[field].strip():
                raise SourceError(f"{source_id}: missing {field}")
        if not isinstance(record["provider_url"], str):
            raise SourceError(f"{source_id}: missing provider URL")
        _https(record["provider_url"])
        mode = record["acquisition"]
        if mode == "generated":
            if (record["format"] != "generated-case" or any(record[key] is not None for key in
                    ("object_url", "expected_bytes", "sha256", "raw_path"))):
                raise SourceError(f"{source_id}: generated source must have no external raw asset")
        elif mode == "provider-link":
            if (record["rights_decision"] != "provider-link-only" or
                    record.get("verification_status") not in ("user-reported-unverified", "locally-verified-metadata") or
                    record["raw_path"] is not None or not record["object_url"]):
                raise SourceError(f"{source_id}: provider-link entry needs an explicit verification status and no raw storage key")
            if (type(record["expected_bytes"]) is not int or record["expected_bytes"] <= 0 or
                    not isinstance(record["sha256"], str) or
                    not re.fullmatch(r"[0-9a-f]{64}", record["sha256"])):
                raise SourceError(f"{source_id}: provider-reported bytes and SHA-256 must be well formed")
            if record["verification_status"] == "locally-verified-metadata":
                _verified_metadata_evidence(record)
            elif "verification_evidence" in record:
                raise SourceError(f"{source_id}: unverified metadata cannot claim a verified profile")
        elif mode in {"fetch", "manual"}:
            if record["format"] == "generated-case" or record["rights_decision"] == "forbidden":
                raise SourceError(f"{source_id}: acquisition conflicts with format or rights")
            size = record["expected_bytes"]
            digest = record["sha256"]
            if (type(size) is not int or not 0 < size <= MAX_SOURCE_BYTES
                    or not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest)):
                raise SourceError(f"{source_id}: external asset needs positive bounded bytes and lowercase SHA-256")
            key = _raw_key(record["raw_path"]).as_posix()
            if key in raw_keys:
                raise SourceError(f"{source_id}: duplicate raw storage key {key}")
            raw_keys.add(key)
            if mode == "fetch" and not record["object_url"]:
                raise SourceError(f"{source_id}: fetch source needs an exact object URL")
        else:
            raise SourceError(f"{source_id}: unsupported acquisition mode {mode!r}")
        if record["object_url"] is not None:
            if not isinstance(record["object_url"], str):
                raise SourceError(f"{source_id}: object_url must be HTTPS or null")
            _https(record["object_url"], fetch=mode == "fetch")
        if record["format"] == "simpeg-obs-tar-gz":
            if any(not isinstance(record.get(field), str) or not record[field].strip()
                   for field in ("quantity", "value_unit", "coordinate_convention")):
                raise SourceError(f"{source_id}: observation archive needs quantity, value_unit and coordinates")
        if record["format"] == "research-zip":
            validate_archive_contract(record.get("archive_contract"))
        elif "archive_contract" in record:
            raise SourceError(f"{source_id}: archive_contract requires research-zip format")
        records[source_id] = record
    if not records:
        raise SourceError("Source ledger is empty")
    return records


def _inside(root: Path, key: PurePosixPath, expected_parent: str) -> Path:
    base = (root / "data" / expected_parent).resolve()
    target = root.joinpath(*key.parts)
    if not base.is_relative_to(root) or not target.resolve().is_relative_to(base) or target.is_symlink():
        raise SourceError(f"Storage key escapes ignored data/{expected_parent}/: {key}")
    return target


def _digest_file(path: Path) -> tuple[int, str]:
    size = 0
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(CHUNK_BYTES), b""):
            size += len(chunk)
            digest.update(chunk)
    return size, digest.hexdigest()


def _verify(path: Path, record: dict) -> None:
    if path.is_symlink() or not path.is_file():
        raise SourceError(f"{record['source_id']}: raw asset is missing or is a symlink: {path}")
    size, digest = _digest_file(path)
    if size != record["expected_bytes"] or digest != record["sha256"]:
        raise SourceError(f"{record['source_id']}: byte/hash mismatch at {path}; expected "
                          f"{record['expected_bytes']} bytes and SHA-256 {record['sha256']}; "
                          "preserve this file for review and use the pinned provider object")


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, new_url):
        raise SourceError(f"Unapproved redirect while fetching {request.full_url}: {new_url}; "
                          "update the reviewed source ledger after verifying the new object")


def _copy_bounded(source, target, expected_bytes: int) -> None:
    size = 0
    with target.open("wb") as output:
        while chunk := source.read(CHUNK_BYTES):
            size += len(chunk)
            if size > expected_bytes:
                raise SourceError(f"Download/import exceeds the pinned {expected_bytes} bytes")
            output.write(chunk)


def _receipt(record: dict, target: Path, root: Path, method: str, original_filename: str) -> dict:
    return {
        "schema": "inverse-earth.raw-asset/v1",
        "asset_id": f"sha256:{record['sha256']}",
        "owner_scope": "local-workspace",
        "source_id": record["source_id"],
        "provider_url": record["provider_url"],
        "object_url": record["object_url"],
        "original_filename": original_filename,
        "mime": MIME[record["format"]],
        "detected_format": record["format"],
        "bytes": record["expected_bytes"],
        "sha256": record["sha256"],
        "storage_key": target.relative_to(root).as_posix(),
        "rights_decision": record["rights_decision"],
        "rights_statement": record["rights_statement"],
        "citation": record["citation"],
        "acquisition_method": method,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "validation_status": "hash-verified",
    }


def acquire_source(source_id: str, *, local_file: Path | None = None, root: Path = ROOT,
                   ledger_path: Path = LEDGER) -> tuple[dict, Path, dict]:
    """Acquire exactly one ledger source; never replace a raw asset or its receipt."""
    records = load_ledger(ledger_path)
    if source_id not in records:
        raise SourceError(f"Unknown source_id {source_id!r}; run acquire.py --list for the reviewed allowlist")
    record = records[source_id]
    mode = record["acquisition"]
    if mode == "generated":
        raise SourceError(f"{source_id}: generated cases use the geological constructor, not raw acquisition")
    if mode == "provider-link":
        raise SourceError(f"{source_id}: provider-link metadata is not an acquirable raw asset; "
                          f"consult {record['object_url']} and review a separate acquisition contract first")
    root = Path(root).resolve()
    target = _inside(root, _raw_key(record["raw_path"]), "downloads")
    receipt_path = _inside(root, PurePosixPath("data/raw/acquisition") / f"{source_id}.json", "raw")
    if local_file is not None:
        local_file = Path(local_file)
        if not local_file.is_file():
            raise SourceError(f"{source_id}: supplied local file does not exist: {local_file}")
        _verify(local_file, record)
    if target.exists() or target.is_symlink():
        _verify(target, record)
        method = "existing-verified"
        original_filename = target.name
    else:
        if local_file is None and mode != "fetch":
            raise SourceError(f"{source_id}: automatic fetch is not approved; obtain the pinned object at "
                              f"{record['object_url'] or record['provider_url']} and pass --file <local-path>")
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.parent.resolve().is_relative_to((root / "data/downloads").resolve()):
            raise SourceError(f"{source_id}: raw storage parent escapes data/downloads")
        staged = None
        try:
            with tempfile.NamedTemporaryFile(prefix=".acquire-", dir=target.parent, delete=False) as temporary:
                staged = Path(temporary.name)
            if local_file is not None:
                with local_file.open("rb") as stream:
                    _copy_bounded(stream, staged, record["expected_bytes"])
                method = "local-import"
                original_filename = local_file.name
            else:
                _https(record["object_url"], fetch=True)
                opener = build_opener(_NoRedirect())
                try:
                    with opener.open(Request(record["object_url"], headers={"User-Agent": "CAOS-Geophysics-source-acquisition/1"}), timeout=30) as stream:
                        _copy_bounded(stream, staged, record["expected_bytes"])
                except (HTTPError, URLError, TimeoutError) as error:
                    raise SourceError(f"{source_id}: provider fetch failed for {record['object_url']}: {error}; "
                                      "check the provider or import a verified local copy with --file") from error
                method = "provider-fetch"
                original_filename = Path(urlsplit(record["object_url"]).path).name
            _verify(staged, record)
            try:
                os.link(staged, target)
            except FileExistsError:
                _verify(target, record)
            _verify(target, record)
        finally:
            if staged is not None:
                staged.unlink(missing_ok=True)
    if receipt_path.exists() or receipt_path.is_symlink():
        if receipt_path.is_symlink():
            raise SourceError(f"{source_id}: raw receipt is a symlink: {receipt_path}")
        try:
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise SourceError(f"{source_id}: unreadable immutable receipt {receipt_path}: {error}") from error
        expected = _receipt(record, target, root, method, original_filename)
        # A provider's human-facing documentation link may be corrected without changing
        # the byte-level object, rights or immutable retrieval-time receipt.
        for field in ("schema", "asset_id", "owner_scope", "source_id", "object_url", "mime",
                      "detected_format", "bytes", "sha256", "storage_key", "rights_decision",
                      "rights_statement", "citation", "validation_status"):
            if receipt.get(field) != expected[field]:
                raise SourceError(f"{source_id}: immutable receipt drift in {field}; inspect {receipt_path}")
        if (receipt.get("acquisition_method") not in {"provider-fetch", "local-import"} or
                not isinstance(receipt.get("original_filename"), str) or
                not receipt["original_filename"].strip() or
                Path(receipt["original_filename"]).name != receipt["original_filename"]):
            raise SourceError(f"{source_id}: immutable receipt has invalid acquisition provenance; inspect {receipt_path}")
        try:
            retrieved_at = datetime.fromisoformat(receipt["retrieved_at_utc"])
        except (KeyError, TypeError, ValueError) as error:
            raise SourceError(f"{source_id}: immutable receipt has invalid retrieval time; inspect {receipt_path}") from error
        if retrieved_at.tzinfo is None:
            raise SourceError(f"{source_id}: immutable receipt has timezone-free retrieval time; inspect {receipt_path}")
    else:
        receipt_path.parent.mkdir(parents=True, exist_ok=True)
        receipt = _receipt(record, target, root, method, original_filename)
        staged_receipt = None
        try:
            with tempfile.NamedTemporaryFile(prefix=".receipt-", dir=receipt_path.parent, delete=False) as temporary:
                staged_receipt = Path(temporary.name)
            staged_receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
            os.link(staged_receipt, receipt_path)
        except FileExistsError as error:
            raise SourceError(f"{source_id}: another acquisition created {receipt_path}; rerun to verify it") from error
        finally:
            if staged_receipt is not None:
                staged_receipt.unlink(missing_ok=True)
    return record, target, receipt
