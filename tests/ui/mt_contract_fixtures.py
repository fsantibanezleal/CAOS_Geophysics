"""Generate TEST-ONLY serialization fixtures from actual reviewed MT compute.
Never bundled by the app. Explicit backend path; original controls read only.
"""
import json
import os
import sys
from pathlib import Path
backend = Path(os.environ["GEOPHYSICS_MT_QA_BACKEND_ROOT"]).resolve(strict=True)
sys.path.insert(0, str(backend))
from app.mt_compute import compute_mt
from app.processing_contract import canonical_bytes, sha256
ROOT = Path(__file__).resolve().parents[2]
def ident(i): return f"00000000-0000-4000-8000-{i:012d}"
source = backend / "data/fixtures/edi/halfspace-100-native.edi"
raw = source.read_bytes()
dataset = dict(schema="geophysics.observation-dataset/v1",dataset_id=ident(1),version=1,owner_id=ident(2),project_id=ident(3),raw_asset_id=ident(4),parent_raw_sha256=sha256(raw),parent_raw_bytes=len(raw),parser_version="edi-strict-envelope/v1",modality="edi_transfer_function",dimensions={"frequency":24},axis_order=["frequency"],qc_verdict="awaiting_full_tensor_qc",
    physical_metadata=dict(coordinate_reference="local",local_crs="source EDI station coordinates",axis_order="xy",horizontal_datum="source EDI frame",vertical_datum="source EDI elevation",vertical_positive="up",horizontal_unit="m",vertical_unit="m",measurement_unit="mV/km/nT",epoch_utc="2026-09-28T00:00:00Z",component_frame="instrument axes",geometry=dict(station_id="HALFSPACE_100_NATIVE",frequency_count=24,tensor_components=["Zxx","Zxy","Zyx","Zyy"],rotation_degrees=0,rotation_reference="unspecified",sign_convention="+",variance_convention="complex")),
    source=dict(provider="Original synthetic test control",exact_url=None,doi=None,citation=None,rights_decision="provider-link-only",rights_statement="Private independent QA control only",attribution="Original synthetic test control"))
dataset["physical_metadata"]["epsg"] = None
ds_sha=sha256(canonical_bytes(dataset))
qc=compute_mt(dataset,source,dataset_sha=ds_sha,job_id=ident(5),request_sha="a"*64,method_id="mt.edi-full-tensor-qc/v1",parameters={})
params=dict(qc_job_id=ident(5),thickness_m=[],initial_ohm_m=[40],beta=.001,bootstrap_samples=20,seed=71401)
inv=compute_mt(dataset,source,dataset_sha=ds_sha,job_id=ident(6),request_sha="b"*64,method_id="mt.edi-fixed-thickness-trf/v1",parameters=params,qc_screen_sha256=sha256(canonical_bytes(qc["screen"])))
dest=ROOT/"frontend/src/test/fixtures/mt-actual.json"
dest.write_text(json.dumps({"dataset":dataset,"m05":qc,"m06":inv},separators=(",",":"),allow_nan=False)+"\n",encoding="utf-8",newline="\n")
print(f"Test-only fixture: {dest}, {dest.stat().st_size} bytes")
