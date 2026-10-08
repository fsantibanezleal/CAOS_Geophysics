"""Exact current M03 observation closure, no solver/process/field admission."""
import argparse
import ctypes
import hashlib
import importlib
import inspect
import os
from pathlib import Path
import sys


M03_HEAD = '72c10d2521ccf11e281c6c398d2e7d1cfb4b76a0'
DEPENDENCY_SOURCES = {
    'magnetic_line_contract': '33720f8510a273292c45b7554010b90886b707a086168ff5c001ec6ca2e78645',
    'magnetic_line_survey': 'f59c8fde2a3094bf0cb9c06b0bbcff5392a54dbda08a208f986a35365f19f6a0',
    'magnetic_line_survey_contract': '6ffcdbcdda8bdda69791260352fe39ac98032cfa8fc0c599aafec5192d500c71',
    'magnetic_line_survey_io': '70e24716327f8b90fe8b9559eba652f3966e614876b80e6b7a1660ec8209fad2',
    'magnetic_line_survey_runtime': '6128950c8137763d9898cf7db3333e135b496ae4cf9d129d4df9e2ed85f2b01e',
    'magnetic_line_validation': 'ec819740f8d4feddee3b4510ebb00479bdcb9b6eba215923fa8ad39dd0608d04',
    'magnetic_lines': '347556cd6a3be788470a0af5638d113f95d750dfa7be9a263272a2fe15075f66',
}


def dependency_sources(root):
    """Check actual closed code bytes before importing a supplied capsule."""
    from magnetic_result_bundle import _read_regular
    root = Path(root)
    if not root.is_absolute() or not root.is_dir() or root.resolve(strict=True) != root:
        raise ValueError('Exact absolute current dependency root required')
    actual = {}
    for name, expected in DEPENDENCY_SOURCES.items():
        path = root/(name+'.py')
        raw = _read_regular(path, 2097152)
        actual[name] = hashlib.sha256(raw).hexdigest()
        if actual[name] != expected:
            raise ValueError('Current M03 dependency source drift: '+name)
    return actual


def qualify(root):
    from magnetic_native_runtime import observation_pins
    from magnetic_original_adapter import binding_for_sources
    from magnetic_survey_json import digest
    from run_magnetic_survey import source_inventory
    expected = dependency_sources(root)
    modules = {}
    for name in expected:
        module = importlib.import_module(name)
        if Path(module.__file__).resolve(strict=True) != Path(root)/(name+'.py'):
            raise ValueError('Foreign loaded M03 dependency root: '+name)
        modules[name] = module
    observed = modules['magnetic_line_survey_runtime']
    for name, parameters in dict(query=('api', 'handle', 'code', 'record'),
            counters=('api', 'psapi', 'job', 'process'), require_job=('handle',)).items():
        if tuple(inspect.signature(getattr(observed, name)).parameters) != parameters:
            raise ValueError('Consumed public observation ABI drift')
    if observed.REQUIRED_FLAGS != 0x220c:
        raise ValueError('Public observation flags drift')
    # Invalid membership must refuse before an OS call or scientific import.
    try:
        observed.require_job(0)
    except modules['magnetic_line_survey'].SurveyError as error:
        if error.error['code'] != 'resource_refused':
            raise
    else:
        raise ValueError('Invalid public Job membership accepted')
    pins = observation_pins()
    if pins != {str(Path(root)/(name+'.py')): sha for name, sha in expected.items()}:
        raise ValueError('Complete seven-module terminal source custody required')
    sources = source_inventory(original=True)
    if any(sources.get(name) != sha for name, sha in expected.items()):
        raise ValueError('Complete seven-module producer source binding required')
    binding = binding_for_sources(sources, digest(sources))
    layouts = {name: dict(bytes=ctypes.sizeof(getattr(observed, name)),
        fields=[item[0] for item in getattr(observed, name)._fields_])
        for name in ('Basic', 'IO', 'Limits', 'Accounting', 'Memory', 'Security')}
    # Re-read after imports. A path/hash check is not an immutable host mount.
    if dependency_sources(root) != expected:
        raise ValueError('Dependency changed during qualification')
    return dict(schema='magnetic-current-m03-dependency-1', status='source_protocol_pass',
        m03_head=M03_HEAD, dependency_sources=expected, observation_sources=pins,
        producer_sources=sources, source_inventory_sha256=digest(sources), layouts=layouts,
        epoch=binding.runtime_epoch, policy=binding.policy,
        m03_run_worker_invoked=False, fit_started=False, native_process_started=False,
        full_method_accepted=False, field_source_verified=False, native_security_admitted=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dependency-root', required=True)
    parser.add_argument('--dependencies', nargs='+', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(argv)
    sys.path[:0] = [str(Path(__file__).parents[1]/'data-pipeline'), args.dependency_root,
        *(str(Path(root).resolve(strict=True)) for root in args.dependencies)]
    from magnetic_local_paths import external_path
    from magnetic_survey_json import canonical
    output = external_path(args.output)
    if output.exists() or not output.parent.is_dir():
        raise ValueError('Fresh explicit external receipt required')
    report = qualify(Path(args.dependency_root))
    with output.open('xb') as stream:
        stream.write(canonical(report))
        stream.flush()
        os.fsync(stream.fileno())
    print(report['status'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
