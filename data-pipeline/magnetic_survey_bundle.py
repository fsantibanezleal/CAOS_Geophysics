"""Private local geometry export closure. Not the future fitted NPY result bundle.

Exclusive new-file writes and readback, no replacement of original or prior
successful generations. Filesystem crash/host durability remains unaccepted.
"""

import hashlib
import os
import stat
from pathlib import Path
from magnetic_survey_json import SurveyHandle, _Lexer, canonical, digest, fail, keys, parse_request
from magnetic_survey import plan_geometry

MAX_EXPORT_BYTES = 16777216


def export_geometry(handle):
    if type(handle) is not SurveyHandle:
        fail("type", "$", "Closed parsed byte handle required")
    raw = handle._export_bytes()
    doc = dict(schema="magnetic-geometry-export-1", request_sha256=hashlib.sha256(raw).hexdigest(),
               request_bytes=len(raw), request=raw.decode("utf-8"), plan=plan_geometry(handle))
    doc["generation_sha256"] = digest(doc)
    out = canonical(doc)
    if len(out) > MAX_EXPORT_BYTES:
        fail("resource", "$", "Geometry export byte capacity exceeded")
    return out


def import_geometry(raw):
    # A bounded outer document contains a single bounded request UTF8 string.
    # Root depth includes the plan, whose descriptor data remain bounded lists.
    lexer = _Lexer(raw, max_bytes=MAX_EXPORT_BYTES, max_string=8388608,
                   max_strings=MAX_EXPORT_BYTES, max_tokens=500000, defer=False)
    doc = lexer.document()
    keys(doc, "schema request_sha256 request_bytes request plan generation_sha256", "$")
    if doc["schema"] != "magnetic-geometry-export-1" or type(doc["request"]) is not str:
        fail("type", "$", "Closed geometry export required")
    generation = doc.pop("generation_sha256")
    if generation != digest(doc):
        fail("hash", "$", "Geometry generation identity mismatch")
    request = doc["request"].encode("utf-8")
    if type(doc["request_bytes"]) is not int or doc["request_bytes"] != len(request):
        fail("count", "$", "Request byte count mismatch")
    if doc["request_sha256"] != hashlib.sha256(request).hexdigest():
        fail("hash", "$", "Original request identity mismatch")
    expected = plan_geometry(parse_request(request))
    # Canonical comparison preserves numeric types/negative zero, unlike ==.
    if canonical(doc["plan"]) != canonical(expected):
        fail("hash", "$/plan", "Recomputed geometry plan mismatch")
    return expected


def write_geometry(path, handle):
    """Create only a new explicit local export; no provider reads or overwrite."""
    from magnetic_local_paths import external_path
    target = external_path(path)
    raw = export_geometry(handle)
    created = False
    try:
        with target.open("xb") as stream:
            created = True
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        imported = read_geometry(target)
        if canonical(imported) != canonical(plan_geometry(handle)):
            fail("durability", "$", "Export readback differs")
    except BaseException:
        if created:
            # Only the exact newly created target, never a parent or prior file.
            target.unlink(missing_ok=True)
        raise


def read_geometry(path):
    target = Path(path)
    if target.is_symlink():
        fail("durability", "$", "Symlink export forbidden")
    with target.open("rb") as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode):
            fail("durability", "$", "Regular local export file required")
        if info.st_size > MAX_EXPORT_BYTES:
            fail("resource", "$", "Geometry export byte capacity exceeded")
        raw = stream.read(MAX_EXPORT_BYTES+1)
    return import_geometry(raw)
