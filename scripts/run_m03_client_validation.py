"""Shared-dispatcher-only owner client component gates, not browser acceptance."""
import argparse
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import xml.etree.ElementTree as ET

from run_m03_qr_reproduction import dispatcher_ancestry,base,core,io,read,require

PRODUCT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('scope','node','dependencies','config','output','dispatcher-lock','retained-result'):
        parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    require(args.scope in ('static','contracts'))
    lock=base.strict_json(read(args.dispatcher_lock,65536));require(set(lock)=={'pid','token'})
    occupancy=dispatcher_ancestry(lock['pid'])
    node=Path(args.node).resolve(strict=True)
    require(sha256(node.read_bytes()).hexdigest()=='58e74bf02fc5bbacc41dcb8bef089961cd5bddd37830b87784e4fc624d145d1f')
    dependencies=io.external_path(args.dependencies)
    shell=json.loads((dependencies/'@fasl-work/caos-app-shell/package.json').read_bytes())
    require(shell['name']=='@fasl-work/caos-app-shell' and shell['version']=='0.8.0')
    # The capsule is an explicit component compatibility input. It cannot
    # establish the parent's current shell0.8.1 integration/browser acceptance.
    output=Path(args.output);require(not output.exists());io.external_path(output.parent)
    config=io.external_path(args.config,directory=False)
    output.mkdir();system=output/'system-temp';system.mkdir()
    retained=io.external_path(args.retained_result,directory=False)
    require(sha256(read(retained)).hexdigest()=='275ae3a46c287f4d44db95608bff0fb674e7f4bf752a47e75c56be768f0d4c76')
    environment=dict(os.environ,TEMP=str(system),TMP=str(system),TMPDIR=str(system),
        GEOPHYSICS_M03_QR_RESULT=str(retained))
    if args.scope=='static':
        command=[str(node),str(dependencies/'typescript/bin/tsc'),'--project',str(config),'--noEmit']
    else:
        command=[str(node),str(dependencies/'vitest/vitest.mjs'),'run','--config',str(config)]
    core._write_member(output,'client-seal.json',base.canonical_bytes(dict(schema='m03-client-controls-seal/1',
        scope=args.scope,dispatcher_lock=lock,occupancy=occupancy,argv=command,
        config_sha256=sha256(config.read_bytes()).hexdigest(),dependency_shell='0.8.0',
        production_browser_acceptance='not_established',field8201='not_verified')))
    completed=subprocess.run(command,cwd=PRODUCT/'frontend',env=environment,check=False)
    if completed.returncode:return completed.returncode
    receipt=dict(schema='m03-client-controls/1',scope=args.scope,verdict='component_pass',
        dependency_shell='0.8.0',production_browser_acceptance='not_established',field8201='not_verified')
    if args.scope=='contracts':
        xml=output/'tests.xml';suites=ET.parse(xml).getroot().findall('testsuite')
        # Literal source-qualified inventory:18 contract +6 intake +5 QR
        # +4 action custody. Preserve every case and zero-SKIP checks.
        require(sum(int(item.get('tests','0')) for item in suites)==33 and
            not any(int(item.get(key,'0')) for item in suites for key in ('errors','failures','skipped')))
        receipt.update(tests=33,xml_sha256=sha256(xml.read_bytes()).hexdigest())
    core._write_member(output,'client-result.json',base.canonical_bytes(receipt))
    return 0


if __name__=='__main__':raise SystemExit(main())
