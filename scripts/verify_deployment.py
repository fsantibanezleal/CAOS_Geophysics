"""Verify public TLS, direct routes, exact build bytes and every catalogue artifact."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import json
from pathlib import Path
import urllib.request

root=Path(__file__).resolve().parents[1]


def fetch(url):
    request=urllib.request.Request(url,headers={'Cache-Control':'no-cache','Accept-Encoding':'gzip','User-Agent':'InverseEarth-ReleaseVerification/2'})
    with urllib.request.urlopen(request,timeout=60) as response:
        data=response.read()
        if response.headers.get('Content-Encoding')=='gzip':data=gzip.decompress(data)
        assert response.status==200
        return data


def verify(origin):
    base=origin.rstrip('/')+'/'
    catalog_raw=fetch(base+'data/v2/catalog.json')
    expected=(root/'data/derived/v2/catalog.json').read_bytes()
    assert catalog_raw==expected,'Catalogue differs from local release: '+base
    catalog=json.loads(catalog_raw)
    variants=[v for c in catalog['cases'] for v in c['variants']]
    def check(v):
        data=fetch(base+'data/v2/'+v['path'])
        assert len(data)==v['bytes'] and hashlib.sha256(data).hexdigest()==v['sha256'],v['path']
        return v['path']
    with ThreadPoolExecutor(max_workers=6) as pool:checked=list(pool.map(check,variants))
    index=(root/'frontend/dist/index.html').read_bytes()
    for route in ['', 'introduction/','methodology/','implementation/','experiments/','benchmark/']:
        assert fetch(base+route)==index,'Direct route build mismatch: '+route
    for name in ['cnn.json','autoencoder.json','training.json']:
        assert fetch(base+'data/v2/models/'+name)==(root/'data/derived/v2/models'/name).read_bytes()
    result=dict(origin=base,https_verified=base.startswith('https://'),cases=len(catalog['cases']),verified_experiments=len(checked),verified_routes=6,verified_model_files=3,catalog_sha256=hashlib.sha256(catalog_raw).hexdigest(),index_sha256=hashlib.sha256(index).hexdigest())
    print(json.dumps(result),flush=True)
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('origins',nargs='+');p.add_argument('--output',type=Path);args=p.parse_args()
    results=[verify(origin) for origin in args.origins]
    if args.output:args.output.write_text(json.dumps(results,indent=2))
