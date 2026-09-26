"""Build the public Clear Lake station screening record from a local, ignored EDI."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'data-pipeline'))
from edi import screen_edi

STATION='USGS-GMEG.2022.cl061.edi'
SOURCE_SHA256='90c5c96cd69d6d29c866a768097cb3b38bc20e8b9c143e24bf10b2d253261e83'
RELEASE_DOI='10.5066/P14KAQ3M'
TRANSFER_FUNCTION_DOI='10.17611/DP/EMTF/GMEG/Clearlake'
STATION_URL='https://data.earthscope.org/app/products/portal/emtf/emtf_item.html?p=2022%2FMT_TF_USGS-GMEG.2022.cl061'


def build(source,output_root):
    source=Path(source);output_root=Path(output_root)
    if output_root.resolve()==(ROOT/'data/derived/v2').resolve():
        raise ValueError('Build and validate an ignored candidate before updating canonical artifacts')
    raw=source.read_bytes()
    assert source.name==STATION and hashlib.sha256(raw).hexdigest()==SOURCE_SHA256,'Unexpected station source bytes'
    destination=output_root/'edi/clear-lake-cl061-screen.json'
    run=screen_edi(source,output=destination,units='mt',variance_convention='complex',rotation='preserve')
    assert run['id']=='cl061' and len(run['frequencies_hz'])==42
    assert run['metadata']['info']['CONDITIONSOFUSE']=='Data Citation Required'
    assert run['metadata']['info']['SURVEYDOI']==TRANSFER_FUNCTION_DOI
    assert not run['one_d_inversion_eligible'] and not run['methods']
    assert all(run['compatibility'][name]>run['compatibility']['threshold'] for name in
               ('xx_component_wrms','yy_component_wrms','antisymmetry_conservative_wrms'))
    run['source_release']=dict(doi=RELEASE_DOI,transfer_function_doi=TRANSFER_FUNCTION_DOI,
        station_url=STATION_URL,rights='USGS data release marked CC0; station EDI requests data citation',
        citation='Peacock, J. R., Mitchell, M. A., and Burgess, S. D. (2025), Magnetotelluric data from the Clear Lake Region, Northern California, USGS data release, doi:10.5066/P14KAQ3M. EarthScope EMTF transfer functions doi:10.17611/DP/EMTF/GMEG/Clearlake.',
        note='Impedance units mt and complex EDI variance are explicit interpretation arguments, not declared by this EDI file.')
    destination.write_text(json.dumps(run,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    manifest_path=output_root/'edi/manifest.json'
    manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    manifest['field_screens']=[dict(id='CLEAR_LAKE_CL061',artifact=destination.name,
        artifact_sha256=hashlib.sha256(destination.read_bytes()).hexdigest(),artifact_bytes=destination.stat().st_size,
        source_sha256=SOURCE_SHA256,source_bytes=len(raw),source_file=STATION,
        station_url=STATION_URL,release_doi=RELEASE_DOI,
        transfer_function_doi=TRANSFER_FUNCTION_DOI,
        parser_source_sha256=hashlib.sha256((ROOT/'data-pipeline/edi.py').read_bytes()).hexdigest(),
        one_d_inversion_eligible=False,observed_frequencies=42,
        citation_condition='Data Citation Required; see artifact source_release and original station INFO')]
    manifest_path.write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n',encoding='utf-8',newline='\n')
    print(f'Built {destination} from SHA-256 {SOURCE_SHA256}; 1D inversion rejected')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source',type=Path,default=ROOT/'data/downloads/clear-lake'/STATION)
    parser.add_argument('--output-root',type=Path,required=True)
    args=parser.parse_args();build(args.source,args.output_root)
