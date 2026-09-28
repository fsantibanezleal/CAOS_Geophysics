"""Validated local observation ingestion; raw external bytes stay ignored."""
from pathlib import Path, PurePosixPath
import argparse
import csv
import hashlib
import io
import json
import os
import tarfile
import tempfile
import numpy as np

from sources import LEDGER, ROOT, SourceError, acquire_source, load_ledger


class IngestError(ValueError):
    """The selected format could not produce a valid local observation record."""


def validate_table(table):
    table=np.asarray(table,dtype=float)
    if table.ndim!=2 or table.shape[1]!=5 or len(table)<4:raise ValueError('Require >=4 rows: east_m,north_m,up_m,value,sigma')
    if not np.isfinite(table).all():raise ValueError('Non-finite observation rejected')
    if np.any(table[:,4]<=0):raise ValueError('Nonpositive uncertainty rejected')
    if len(np.unique(table[:,:3],axis=0))!=len(table):raise ValueError('Duplicate station coordinates rejected')
    # Stable station order is independent of source line order.
    return table[np.lexsort((table[:,0],table[:,1]))]


def read_csv(path):
    with Path(path).open(newline='',encoding='utf-8-sig') as stream:
        reader=csv.DictReader(stream)
        expected=['east_m','north_m','up_m','value','sigma']
        if reader.fieldnames!=expected:raise ValueError('CSV headers must be '+','.join(expected))
        return validate_table([[float(row[k]) for k in expected] for row in reader])


def _archive_observations(record: dict, path: Path) -> tuple[np.ndarray, str]:
    source_id = record["source_id"]
    if path.suffixes[-2:] != [".tar", ".gz"]:
        raise IngestError(f"{source_id}: expected a .tar.gz observation archive, received {path.name}")
    with path.open("rb") as header:
        signature = header.read(2)
    if signature != b"\x1f\x8b":
        raise IngestError(f"{source_id}: archive lacks gzip signature; check the pinned provider object")
    try:
        with tarfile.open(path, "r:gz") as archive:
            total = 0
            count = 0
            matches = []
            for member in archive:
                count += 1
                if count > 128:
                    raise IngestError(f"{source_id}: archive entry count exceeds 128")
                name = PurePosixPath(member.name)
                if ("\\" in member.name or name.is_absolute() or ".." in name.parts
                        or member.issym() or member.islnk() or not (member.isfile() or member.isdir())):
                    raise IngestError(f"{source_id}: unsafe archive entry {member.name!r}")
                if member.size < 0 or member.size > 10_000_000:
                    raise IngestError(f"{source_id}: oversized archive entry {member.name!r}")
                total += member.size
                if total > 20_000_000 or total > path.stat().st_size * 1000:
                    raise IngestError(f"{source_id}: archive expansion exceeds 20 MB or 1000:1")
                if member.isfile() and member.name.endswith("_data.obs"):
                    matches.append(member)
            if count == 0:
                raise IngestError(f"{source_id}: archive is empty")
            if len(matches) != 1:
                raise IngestError(f"{source_id}: expected exactly one _data.obs member, found {len(matches)}")
            stream = archive.extractfile(matches[0])
            if stream is None:
                raise IngestError(f"{source_id}: cannot read {matches[0].name}")
            with stream:
                observations = np.loadtxt(io.BytesIO(stream.read()), dtype=float)
    except (tarfile.TarError, EOFError, OSError, ValueError) as error:
        raise IngestError(f"{source_id}: malformed tar archive: {error}") from error
    if observations.ndim != 2 or observations.shape[1] != 4 or len(observations) < 4:
        raise IngestError(f"{source_id}: _data.obs needs at least four XYZ/value rows and exactly four columns")
    if not np.isfinite(observations).all():
        raise IngestError(f"{source_id}: non-finite tutorial observation rejected; no zero replacement")
    return observations, matches[0].name


def _process_archive(record: dict, raw_path: Path, root: Path) -> dict:
    observations, member_name = _archive_observations(record, raw_path)
    # The tutorials supply no instrument uncertainty. This assumption is local only.
    sigma = max(float(np.std(observations[:, 3])) * 0.03, 1e-12)
    table = validate_table(np.c_[observations, np.full(len(observations), sigma)])
    median = float(np.median(table[:, 3]))
    mad = float(np.median(np.abs(table[:, 3] - median)))
    flags = np.flatnonzero(np.abs(table[:, 3] - median) > 6 * 1.4826 * mad).tolist()
    source_id = record["source_id"]
    raw_sha = record["sha256"]
    folder = root / "data/raw/processed" / source_id
    if (not (root / "data/raw").resolve().is_relative_to(root)
            or not folder.resolve().is_relative_to((root / "data/raw").resolve())):
        raise IngestError(f"{source_id}: derivative path escapes ignored data/raw")
    folder.mkdir(parents=True, exist_ok=True)
    output = folder / f"{raw_sha}.npz"
    receipt_path = folder / f"{raw_sha}.json"
    if output.exists() or receipt_path.exists():
        if output.is_symlink() or receipt_path.is_symlink() or not output.is_file() or not receipt_path.is_file():
            raise IngestError(f"{source_id}: derivative/receipt pair is incomplete or a symlink; inspect {folder}")
        try:
            report = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise IngestError(f"{source_id}: cannot read preprocessing receipt {receipt_path}: {error}") from error
        if (report.get("source_sha256") != raw_sha or report.get("member") != member_name
                or report.get("preprocessed_sha256") != hashlib.sha256(output.read_bytes()).hexdigest()):
            raise IngestError(f"{source_id}: immutable preprocessing receipt or derivative drift; inspect {folder}")
        return report
    staged = None
    staged_receipt = None
    try:
        with tempfile.NamedTemporaryFile(prefix=".observations-", dir=folder, delete=False) as temporary:
            staged = Path(temporary.name)
            np.savez_compressed(temporary, locations_xyz_m=table[:, :3], observed=table[:, 3],
                                sigma_assumed=table[:, 4], outlier_flag=np.isin(np.arange(len(table)), flags))
        derivative_sha = hashlib.sha256(staged.read_bytes()).hexdigest()
        report = {
            "schema": "inverse-earth.local-preprocessing/v2",
            "source_id": source_id,
            "source_sha256": raw_sha,
            "source_bytes": record["expected_bytes"],
            "source_rights_decision": record["rights_decision"],
            "member": member_name,
            "rows": len(table),
            "columns": ["x_m", "y_m", "z_m", "value", "sigma_assumed"],
            "quantity": record["quantity"],
            "value_unit": record["value_unit"],
            "coordinate_convention": record["coordinate_convention"],
            "uncertainty_policy": "3% observation SD assigned for local experimentation, floor 1e-12; not instrument uncertainty",
            "outlier_policy": "flag only at >6 scaled MAD; no deletion or reweighting",
            "outlier_rows_sorted": flags,
            "preprocessed_path": output.relative_to(root).as_posix(),
            "preprocessed_sha256": derivative_sha,
            "redistribution": "raw and preprocessed values remain ignored; upstream redistribution terms not assumed",
        }
        with tempfile.NamedTemporaryFile(prefix=".preprocessing-receipt-", dir=folder, delete=False) as temporary:
            staged_receipt = Path(temporary.name)
        staged_receipt.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
        os.link(staged, output)
        os.link(staged_receipt, receipt_path)
    except FileExistsError as error:
        raise IngestError(f"{source_id}: another run created the derivative; rerun to verify it") from error
    finally:
        if staged is not None:
            staged.unlink(missing_ok=True)
        if staged_receipt is not None:
            staged_receipt.unlink(missing_ok=True)
    return report


def _process_edi(record: dict, raw_path: Path) -> dict:
    source_id = record["source_id"]
    with raw_path.open("rb") as header:
        signature = header.read(128).lstrip()
    if raw_path.suffix.lower() != ".edi" or not signature.startswith(b">HEAD"):
        raise IngestError(f"{source_id}: expected EDI >HEAD text, not an archive or HTML provider page")
    try:
        from edi import screen_edi
        screen = screen_edi(raw_path, units="mt", variance_convention="complex", rotation="preserve")
    except ImportError as error:
        raise IngestError(f"{source_id}: EDI QC needs the pinned offline dependencies; run scripts/setup.ps1 -Gpu "
                          f"or scripts/setup.sh --gpu ({error})") from error
    except (ValueError, RuntimeError, OSError) as error:
        raise IngestError(f"{source_id}: EDI transfer-function QC rejected the file: {error}") from error
    if screen["provenance"]["source_sha256"] != record["sha256"]:
        raise IngestError(f"{source_id}: EDI parser source hash disagrees with the raw asset")
    if source_id == "clear-lake-cl061" and (screen["id"] != "cl061" or len(screen["frequencies_hz"]) != 42
                                              or screen["one_d_inversion_eligible"]):
        raise IngestError(f"{source_id}: pinned station must be cl061 with 42 frequencies and QC-only verdict")
    return {
        "schema": "inverse-earth.local-edi-qc/v1", "source_id": source_id,
        "source_sha256": record["sha256"], "format": "edi-transfer-function",
        "station_id": screen["id"], "frequencies": len(screen["frequencies_hz"]),
        "one_d_inversion_eligible": screen["one_d_inversion_eligible"],
        "inversion_performed": screen["inversion_performed"],
        "rights_decision": record["rights_decision"],
        "interpretation_arguments": {"units": "mt", "variance_convention": "complex", "rotation": "preserve"},
        "note": "EDI transfer functions are not raw EM time series; QC is not a field inversion.",
    }


def ingest_source(source_id: str, *, local_file: Path | None = None, root: Path = ROOT,
                  ledger_path: Path = LEDGER) -> dict:
    record, raw_path, receipt = acquire_source(source_id, local_file=local_file,
                                               root=root, ledger_path=ledger_path)
    if record["format"] == "simpeg-obs-tar-gz":
        result = _process_archive(record, raw_path, Path(root).resolve())
    elif record["format"] == "edi-transfer-function":
        result = _process_edi(record, raw_path)
    else:
        raise IngestError(f"{source_id}: verified raw asset {receipt['storage_key']} ({record['format']}) is retained "
                          "locally; no validated observation adapter exists for this format yet. "
                          f"Provider: {record['provider_url']}")
    return result


def external(*, root: Path = ROOT, ledger_path: Path = LEDGER) -> list[dict]:
    """Legacy batch spelling, restricted to reviewed automatic tutorial archives."""
    records = load_ledger(ledger_path)
    ids = [record["source_id"] for record in records.values()
           if record["acquisition"] == "fetch" and record["format"] == "simpeg-obs-tar-gz"]
    if not ids:
        raise IngestError("--external has no reviewed fetchable observation archives")
    return [ingest_source(source_id, root=root, ledger_path=ledger_path) for source_id in ids]


def invert_csv(path,family,out):
    from discretize import TensorMesh
    from simpeg import maps
    from simpeg.potential_fields import gravity,magnetics
    from potential import invert
    a=read_csv(path);xy=a[:,:2]
    width=np.maximum(np.ptp(xy,axis=0)*1.25,100)
    spacing=[width[0]/14,width[1]/12,min(width)/10]
    top=float(np.min(a[:,2])-spacing[2]/2)
    origin=[xy[:,0].mean()-width[0]/2,xy[:,1].mean()-width[1]/2,top-8*spacing[2]]
    mesh=TensorMesh([np.full(14,spacing[0]),np.full(12,spacing[1]),np.full(8,spacing[2])],origin=origin)
    if family=='gravity':
        survey=gravity.Survey(gravity.sources.SourceField([gravity.receivers.Point(a[:,:3],components='gz')]))
        G=gravity.simulation.Simulation3DIntegral(mesh,survey=survey,rhoMap=maps.IdentityMap(nP=mesh.nC),engine='geoana').G
    else:
        survey=magnetics.Survey(magnetics.sources.UniformBackgroundField([magnetics.receivers.Point(a[:,:3],components='tmi')],amplitude=50000,inclination=60,declination=12))
        G=magnetics.simulation.Simulation3DIntegral(mesh,survey=survey,chiMap=maps.IdentityMap(nP=mesh.nC),engine='geoana').G
    results={}
    for name,sparse in [('l2',False),('irls',True)]:
        result=invert(np.asarray(G,dtype=float),a[:,3],a[:,4],.018,sparse,shape=(8,12,14),spacing=tuple(spacing))
        result['predicted']=(G@result['model']).tolist()
        result['residual']=(a[:,3]-result['predicted']).tolist()
        results[name]=result
    record=dict(schema='inverse-earth.user-survey/v2',family=family,input_sha256=hashlib.sha256(Path(path).read_bytes()).hexdigest(),coordinate_convention='ENU; gravity gz positive upward; magnetics fixed 50000 nT / 60 deg inclination / 12 deg declination',mesh=dict(shape=[8,12,14],spacing=spacing,origin=origin),results=results,limitations='No terrain mask, regional removal or automatic field-direction estimation. User must preprocess these explicitly. No known truth or model accuracy claim.')
    Path(out).write_text(json.dumps(record,separators=(',',':')))
    print('Validated and inverted',len(a),'stations ->',out)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    selector=parser.add_mutually_exclusive_group(required=True)
    selector.add_argument('--external',action='store_true',help='Acquire and ingest only the reviewed SimPEG archives')
    selector.add_argument('--source-id',help='Select one source from data/source-ledger.json')
    selector.add_argument('--csv',type=Path,help='Invert a user-supplied five-column gravity/magnetic CSV')
    parser.add_argument('--file',type=Path,help='Pinned local raw file for --source-id')
    parser.add_argument('--family',choices=['gravity','magnetics'],default='gravity')
    parser.add_argument('--output',default='data/raw/user-inversion.json')
    args=parser.parse_args()
    if args.file and not args.source_id:
        parser.error('--file requires --source-id')
    try:
        if args.external:
            print(json.dumps(external(),indent=2))
        elif args.source_id:
            print(json.dumps(ingest_source(args.source_id,local_file=args.file),indent=2))
        else:
            Path(args.output).parent.mkdir(parents=True,exist_ok=True)
            invert_csv(args.csv,args.family,args.output)
    except (SourceError,IngestError,ValueError) as error:
        parser.exit(2,f'Ingestion failed: {error}\n')
