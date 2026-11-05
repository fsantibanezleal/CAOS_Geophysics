"""Auditable ingestion and epoch differencing for the USGS Long Valley network.

This is a processing workflow for repeated gravity observations, not a density
inversion.  The archived table has no station elevation column and the published
time differences have not been corrected here for vertical deformation or water
table change.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path
import re
from typing import Any


SOURCE_URL = "https://pubs.usgs.gov/dds/dds-81/MonitoringData/Gravity/SpreadsheetFormatData/GravitySurveys.txt"
METADATA_URL = "https://pubs.usgs.gov/dds/dds-81/Intro/MonitoringData/Gravity/gravitymetadata.htm"
FORMAT_URL = "https://pubs.usgs.gov/dds/dds-81/Intro/MonitoringData/Gravity/DataFormat.html"
EPOCH = re.compile(r"\s*(JUNE|SEPT|JULY)\s+(19\d{2})\s*", re.IGNORECASE)
# Exact-source review flag. The raw observation is retained without correction.
QC_SOURCE_SHA256 = "d7cca18741ef85fa7ea6fe448dabfee40900de6ed45ba5ea3d13b9e9f9ec1424"
QC_OBSERVATION = ("1JD1952", "1982-09", 979255.21, 0.005)
QC_REASON = ("Suspected source transcription/cross-copy: this exact value also appears at 1JCM1952, while nearby 1JD1952 occupations are near 979279.9 mGal. USGS OFR 87-77 reports 979279.87 for 1JD1952 and 979255.21 for 1JCM1952. The 1982-09 source value is preserved and unresolved; no correction is applied.")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def metadata_sha256(path: Path) -> str:
    """Normalize only rotating Cloudflare contact tokens/injected wrapper."""
    text = path.read_text(encoding="iso-8859-1")
    text, scripts = re.subn(r'<script>\(function\(\)\{function c\(\).*?</script>', '<!-- volatile Cloudflare injection removed -->', text, count=1, flags=re.DOTALL)
    if scripts != 1:
        raise ValueError(f"expected one Cloudflare transient wrapper in USGS HTML; found {scripts}")
    canonical, replacements = re.subn(r'data-cfemail="[0-9a-fA-F]{2,}"', 'data-cfemail="[volatile-contact-token]"', text)
    if replacements < 1:
        raise ValueError("USGS metadata has no expected Cloudflare contact tokens")
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _number(value: str, *, field: str, line: int, allow_blank: bool = False) -> float | None:
    value = value.strip()
    if not value and allow_blank:
        return None
    try:
        result = float(value)
    except ValueError as exc:
        raise ValueError(f"line {line}: invalid {field}: {value!r}") from exc
    if not math.isfinite(result):
        raise ValueError(f"line {line}: non-finite {field}")
    return result


def parse_source(path: Path) -> dict[str, Any]:
    """Parse the official wide table without interpolation or value correction."""
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        rows = list(csv.reader(stream, delimiter="\t"))
    if len(rows) < 2:
        raise ValueError("source must contain a header and at least one station")
    header = [cell.strip() for cell in rows[0]]
    if len(header) < 5 or header[0].upper() != "STATION" or header[1].upper() != "X (UTM)" or header[2].upper() != "Y (UTM)":
        raise ValueError("unexpected Long Valley source header; expected STATION, X (UTM), Y (UTM)")
    if (len(header) - 3) % 2:
        raise ValueError("each occupation column must be followed by its StDev column")
    epochs: list[str] = []
    for index in range(3, len(header), 2):
        match = EPOCH.fullmatch(header[index])
        if not match or header[index + 1].strip().casefold() != "stdev":
            raise ValueError(f"unexpected occupation/error column pair at column {index + 1}")
        month, year = match.groups()
        month = {"june": "06", "sept": "09", "july": "07"}[month.casefold()]
        epochs.append(f"{year}-{month}")
    if len(set(epochs)) != len(epochs):
        raise ValueError("duplicate occupation epoch")

    stations: list[dict[str, Any]] = []
    seen: set[str] = set()
    for line, row in enumerate(rows[1:], start=2):
        if not row or not any(cell.strip() for cell in row):
            continue
        if len(row) != len(header):
            raise ValueError(f"line {line}: expected {len(header)} tab-separated fields, got {len(row)}")
        station_id = row[0].strip()
        if not station_id or station_id in seen:
            raise ValueError(f"line {line}: blank or duplicate station ID {station_id!r}")
        seen.add(station_id)
        easting = _number(row[1], field="easting_m", line=line)
        northing = _number(row[2], field="northing_m", line=line)
        if easting is None or northing is None:
            raise ValueError(f"line {line}: station coordinates are required")
        measurements = []
        for offset, epoch in enumerate(epochs):
            value = _number(row[3 + 2 * offset], field=f"gravity_mgal[{epoch}]", line=line, allow_blank=True)
            sigma = _number(row[4 + 2 * offset], field=f"sigma_mgal[{epoch}]", line=line, allow_blank=True)
            if (value is None) != (sigma is None):
                raise ValueError(f"line {line}: gravity and standard deviation must both be present or both blank for {epoch}")
            if sigma is not None and sigma <= 0:
                raise ValueError(f"line {line}: standard deviation must be positive for {epoch}")
            if value is not None:
                measurements.append({"epoch": epoch, "gravity_mgal": value, "sigma_mgal": sigma})
        stations.append({"station_id": station_id, "easting_m": easting, "northing_m": northing, "measurements": measurements})
    if not stations:
        raise ValueError("source contains no station rows")

    source_hash = sha256(path)
    if source_hash == QC_SOURCE_SHA256:
        matches = [m for s in stations if s["station_id"] == QC_OBSERVATION[0] for m in s["measurements"] if (s["station_id"], m["epoch"], m["gravity_mgal"], m["sigma_mgal"]) == QC_OBSERVATION]
        if len(matches) != 1:
            raise ValueError("reviewed source hash matched but its flagged observation changed; inspect the archive update")
        matches[0]["qc"] = {"status": "suspect", "reason": QC_REASON, "review": "unresolved; raw source value retained"}
    return {"epochs": epochs, "stations": stations, "source_sha256": source_hash}


def difference(source: dict[str, Any], earlier: str, later: str, *, include_suspect: bool = False) -> dict[str, Any]:
    """Compute later-minus-earlier differences for station IDs present in both.

    Independent epoch errors are propagated as sqrt(sigma_earlier^2 +
    sigma_later^2).  This is an explicit working assumption: the source does not
    provide cross-epoch covariance, and shared network/systematic errors may be
    correlated.
    """
    epochs = source["epochs"]
    if earlier not in epochs or later not in epochs or earlier == later:
        raise ValueError("choose two distinct epochs present in the source")
    selected: list[dict[str, Any]] = []
    for station in source["stations"]:
        by_epoch = {entry["epoch"]: entry for entry in station["measurements"]}
        if earlier not in by_epoch or later not in by_epoch:
            continue
        a, b = by_epoch[earlier], by_epoch[later]
        if not include_suspect and (a.get("qc", {}).get("status") == "suspect" or b.get("qc", {}).get("status") == "suspect"):
            continue
        delta = b["gravity_mgal"] - a["gravity_mgal"]
        sigma = math.hypot(a["sigma_mgal"], b["sigma_mgal"])
        selected.append({
            "station_id": station["station_id"],
            "easting_m": station["easting_m"],
            "northing_m": station["northing_m"],
            "earlier_gravity_mgal": a["gravity_mgal"],
            "earlier_sigma_mgal": a["sigma_mgal"],
            "later_gravity_mgal": b["gravity_mgal"],
            "later_sigma_mgal": b["sigma_mgal"],
            "delta_gravity_mgal": delta,
            "delta_sigma_independent_mgal": sigma,
            "standardized_delta_independent": delta / sigma,
        })
    if not selected:
        raise ValueError(f"no common stations for {earlier} and {later}")
    return {
        "earlier_epoch": earlier,
        "later_epoch": later,
        "difference_convention": "later-minus-earlier",
        "uncertainty_model": "independent epoch 1-sigma errors; covariance unavailable",
        "stations": selected,
    }


def build_artifact(source_path: Path, metadata_path: Path, earlier: str, later: str) -> dict[str, Any]:
    parsed = parse_source(source_path)
    paired = difference(parsed, earlier, later)
    return {
        "schema": "geophysics.field.gravity-time-lapse/v2",
        "source": {
            "title": "Long Valley Caldera Gravity Surveys, 1980–1999",
            "provider": "U.S. Geological Survey, Digital Data Series DDS-81",
            "data_url": SOURCE_URL,
            "format_metadata_url": FORMAT_URL,
            "fgdc_metadata_url": METADATA_URL,
            "source_sha256": parsed["source_sha256"],
            "metadata_sha256": metadata_sha256(metadata_path),
            "metadata_hash_rule": "SHA-256 over UTF-8 metadata after replacing all rotating Cloudflare data-cfemail values and its single injected transient script; all source-authored metadata remains bound",
            "retrieved_date": "2026-11-02",
            "attribution": "Battaglia, M., Williams, M.J., Venezky, D.Y., Hill, D.P., Langbein, J.O., Farrar, C.D., Howle, J.F., Sneed, M., and Segall, P., 2003, The Long Valley Caldera GIS Database: U.S. Geological Survey Digital Data Series DDS-81, GravitySurveys.txt.",
        },
        "observation_contract": {
            "horizontal_coordinates": "source-reported UTM easting/northing, metres; source datum NAD27; zone not explicitly named here",
            "gravity_unit": "mGal",
            "uncertainty": "source-reported 1 standard deviation, mGal",
            "processing_history": "source describes removal of solid Earth tides and daily instrument drift and least-squares averaging of station occupations",
            "interpretation_limits": [
                "No station elevation is present in this table.",
                "The raw epoch differences are not corrected here for vertical deformation, water-table changes, or inter-epoch covariance.",
                "These values are field observations and derived temporal differences, not a density model or a unique magma-source estimate.",
                "Do not use the pairwise standardization as a calibrated detection probability.",
            ],
            "quality_control": "One exact observation is flagged as suspected source transcription/cross-copy, bound to the retrieved table SHA-256. It remains unchanged and is excluded from default pairwise calculations; callers may explicitly include flagged values.",
        },
        "epochs": parsed["epochs"],
        "station_count": len(parsed["stations"]),
        "measurement_count": sum(len(station["measurements"]) for station in parsed["stations"]),
        "stations": parsed["stations"],
        "difference": paired,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=Path("data/downloads/long-valley/GravitySurveys.txt"))
    parser.add_argument("--metadata", type=Path, default=Path("data/downloads/long-valley/gravitymetadata.htm"))
    parser.add_argument("--earlier", default="1982-06")
    parser.add_argument("--later", default="1999-07")
    parser.add_argument("--output", type=Path, default=Path("data/derived/field/long-valley/1982-06_to_1999-07.json"))
    parser.add_argument("--check", action="store_true", help="fail unless the committed derived artifact is byte-identical to a fresh replay")
    args = parser.parse_args()
    artifact = build_artifact(args.source, args.metadata, args.earlier, args.later)
    encoded = json.dumps(artifact, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    if args.check:
        if not args.output.is_file() or args.output.read_text(encoding="utf-8") != encoded:
            raise SystemExit(f"derived artifact is stale: {args.output}")
        print(f"verified byte-identical derived artifact: {args.output}")
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(encoded, encoding="utf-8", newline="\n")
    print(json.dumps({"output": str(args.output), "station_count": artifact["station_count"], "measurement_count": artifact["measurement_count"], "pair_count": len(artifact["difference"]["stations"]), "source_sha256": artifact["source"]["source_sha256"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
