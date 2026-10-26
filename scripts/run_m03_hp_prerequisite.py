"""Deterministic small-oracle -> proof -> ONE cold candidate, never outer/full97.

Run with existing scientific package root on sys.path (no install). Both paths
are private external device directories; output must not exist, including retry.
"""
import argparse
from hashlib import sha256
from pathlib import Path
import os
import subprocess
import sys
import xml.etree.ElementTree as ET

PRODUCT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PRODUCT/'data-pipeline'))


def main():
    import magnetic_line_contract as base
    import magnetic_line_survey as core
    import magnetic_line_survey_hp as hp
    import magnetic_line_survey_io as io
    import magnetic_line_survey_runtime as runtime
    parser = argparse.ArgumentParser()
    parser.add_argument('--retained-root', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    output = Path(args.output)
    if output.exists(): raise core.SurveyError('custody_mismatch', 'seal')
    io.external_path(output.parent)
    output.mkdir()
    retained = io.external_path(args.retained_root)
    sources = ('magnetic_line_survey_hp.py', 'magnetic_line_survey_capacity_hp.py', 'magnetic_line_survey_hp_prerequisite.py')
    hashes = {name: sha256((PRODUCT/'data-pipeline'/name).read_bytes()).hexdigest() for name in sources}
    test = PRODUCT/'tests/data/test_magnetic_line_survey_hp.py'
    test_hash = sha256(test.read_bytes()).hexdigest()
    packages = Path(os.environ['GEOPHYSICS_EXISTING_PACKAGE_ROOT']).resolve(strict=True)
    executable = Path(sys.base_prefix)/'python.exe'
    xml = output/'dense-oracles.xml'
    code = "import sys,runpy;sys.path.insert(0,sys.argv.pop(1));runpy.run_module('pytest',run_name='__main__')"
    environment = dict(os.environ, PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', PYTHONDONTWRITEBYTECODE='1',
        NUMBA_CACHE_DIR=str(output/'oracle-numba'), TEMP=str(output), TMP=str(output))
    completed = subprocess.run([str(executable), '-B', '-S', '-c', code, str(packages), str(test),
        '-q', '-p', 'no:cacheprovider', f'--junitxml={xml}', f'--basetemp={output}/oracle-temp'],
        cwd=PRODUCT, env=environment, check=False)
    if completed.returncode != 0: return completed.returncode
    suites = ET.parse(xml).getroot().findall('testsuite')
    if sum(int(s.get('tests', '0')) for s in suites) != 7 or \
       any(int(s.get(k, '0')) for s in suites for k in ('errors', 'failures', 'skipped')) or \
       sha256(test.read_bytes()).hexdigest() != test_hash or \
       hashes != {name: sha256((PRODUCT/'data-pipeline'/name).read_bytes()).hexdigest() for name in sources}:
        raise core.SurveyError('custody_mismatch', 'seal')
    receipt = dict(schema='m03-hp-dense-oracles/1', policy_epoch=hp.EPOCH, verdict='pass', tests=7,
        source_sha256=hashes, test_source_sha256=test_hash, xml_sha256=sha256(xml.read_bytes()).hexdigest())
    core._write_member(output, 'dense-oracles.json', base.canonical_bytes(receipt))
    worker = output/'worker'; worker.mkdir()
    plan = dict(schema='m03-hp-prerequisite-plan/1', retained_root=str(retained),
        oracle_receipt=str(output/'dense-oracles.json'), oracle_receipt_sha256=base.digest(receipt))
    core._write_member(worker, 'plan.json', base.canonical_bytes(plan))
    lifetime = runtime.run_worker(executable, packages, worker, worker/'plan.json')
    print(base.canonical_bytes(lifetime).decode('ascii'))
    return 0 if lifetime['verdict'] == 'component_pass' else 2


if __name__ == '__main__':
    raise SystemExit(main())
