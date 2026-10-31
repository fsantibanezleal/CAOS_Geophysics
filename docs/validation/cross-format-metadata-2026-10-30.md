# Cross-format physical-metadata gate : 2026-10-30

## Result

The new R-003 metadata gate passed **72/72 tests** across the 12 upload formats declared by the API: gravity CSV, magnetic CSV, travel-time CSV, ERT CSV, GeoTIFF, EDI, MiniSEED, StationXML, SEG-Y, MTH5, `.ohm`, and `.sgt`. The matrix verifies valid declared metadata for each format, then rejects an invalid measurement unit, component frame, required geometry field, coordinate reference/CRS, or missing/non-timezone-aware survey epoch with the relevant field path.

The existing authenticated upload metadata suite passed **14/14 tests**. It confirms missing physical metadata is rejected before any raw asset is stored, and checks CRS, units, geometry columns, GeoTIFF georeferencing, malformed nested fields, format byte limits, and the owned MiniSEED/StationXML relationship. One upstream Starlette/httpx deprecation warning was emitted; both test commands exited successfully.

## Reproduction

From the repository root on Windows:

```powershell
.\.venv-api\Scripts\python.exe -m pytest -q tests/data/test_formats.py
.\.venv-api\Scripts\python.exe -m pytest -q tests/api/test_metadata.py
```

Implementation under test: `app/schemas.py` and `app/formats.py`. The API invokes `validate_declared_metadata` before it streams or stores an upload. The SDD's R-003 gate now exists at the path it names: `tests/data/test_formats.py::test_missing_physical_metadata_rejection`.

## Scope

This closes the cross-format **metadata contract** check only. It does not claim that all 12 formats have complete scientific parsers, compatible solver routes, uploaded-data computation, or host admission. Those remain separate method and release gates.
