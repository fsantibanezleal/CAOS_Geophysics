"""Actual package/license/source/native byte identity under full-survey Job.

Do not borrow the bounded operator's 512MiB/60s guard or invent wheel hashes.
This receipt identifies installed bytes, not rights approval or host admission.
"""
from __future__ import annotations

from hashlib import sha256
from importlib import import_module
from importlib.metadata import distribution
from pathlib import Path
import platform

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract as schema

SOURCES=('magnetic_line_contract','magnetic_lines','magnetic_line_validation',
    'magnetic_line_survey','magnetic_line_survey_contract','magnetic_line_survey_contract_v2',
    'magnetic_line_survey_io','magnetic_line_survey_representation','magnetic_line_survey_capacity_v2',
    'magnetic_line_survey_geometry','magnetic_line_survey_support','magnetic_line_survey_crossovers',
    'magnetic_line_survey_navigation','magnetic_line_survey_seal','magnetic_line_survey_measurements',
    'magnetic_line_survey_reference','magnetic_line_survey_corrections','magnetic_line_survey_physical_fit',
    'magnetic_line_survey_fit','magnetic_line_survey_grid','magnetic_line_survey_transforms',
    'magnetic_line_survey_environment','magnetic_line_survey_result','magnetic_line_survey_export',
    'magnetic_line_survey_cli','magnetic_line_survey_local_worker',
    'magnetic_line_survey_resolution_geometry','magnetic_line_survey_resolution_worker')
NATIVES=('numpy._core._multiarray_umath','numpy.linalg._umath_linalg','scipy.linalg._fblas',
    'scipy.linalg._flapack','scipy.spatial._qhull','sklearn.utils._cython_blas','numba._dispatcher')


def file_pin(path, name):
    from magnetic_line_survey import _plain_path,_file_key
    path=_plain_path(path)
    identity=sha256()
    with path.open('rb') as stream:
        import os
        before=os.fstat(stream.fileno())
        for chunk in iter(lambda:stream.read(1048576),b''):
            identity.update(chunk)
        after=os.fstat(stream.fileno())
        if _file_key(before)!=_file_key(after) or before.st_ctime_ns!=after.st_ctime_ns or \
           _file_key(after)!=_file_key(path.stat()):
            raise core.SurveyError('custody_mismatch','export')
    return dict(module_name=name,sha256=identity.hexdigest(),bytes=after.st_size)


def environment_identity(package_root, *, job_handle):
    from magnetic_line_survey_runtime import require_job
    require_job(job_handle)
    packages=core._plain_path(Path(package_root).resolve(strict=True),directory=True)
    core.engines()
    versions=[]
    for name,pin in core.ENGINE_PINS.items():
        dist=distribution(name)
        if dist.version!=pin:
            raise core.SurveyError('custody_mismatch','export')
        inventory,licenses=[],[]
        for entry in sorted(dist.files or [],key=str):
            if str(entry).endswith('.pyc') or '__pycache__' in str(entry):
                continue
            path=Path(dist.locate_file(entry)).resolve(strict=True)
            # Installed scripts/metadata may live next to site-packages in
            # the same actual pre-existing environment, never anywhere else.
            if not path.is_relative_to(packages.parents[1]):
                raise core.SurveyError('custody_mismatch','export')
            actual=file_pin(path,str(entry).replace('\\','/'))
            record=dict(name=actual['module_name'],sha256=actual['sha256'],bytes=actual['bytes'])
            inventory.append(record)
            if 'license' in str(entry).lower() or path.name=='METADATA':
                licenses.append(record)
        if not inventory or not licenses:
            raise core.SurveyError('custody_mismatch','export')
        versions.append(dict(name=name,version=pin,distribution_sha256=base.digest(inventory),
                             license_evidence_sha256=base.digest(licenses)))
    files=[]
    for name in SOURCES:
        module=import_module(name)
        path=Path(module.__file__).resolve(strict=True)
        if path!=Path(__file__).with_name(name+'.py').resolve(strict=True):
            raise core.SurveyError('custody_mismatch','export')
        files.append(file_pin(path,name))
    for name,(package,relative,expected) in core.SOURCE_PINS.items():
        module=import_module(name)
        path=Path(module.__file__).resolve(strict=True)
        if path!=Path(distribution(package).locate_file(relative)).resolve(strict=True):
            raise core.SurveyError('custody_mismatch','export')
        actual=file_pin(path,name)
        if actual['sha256']!=expected:
            raise core.SurveyError('custody_mismatch','export')
        files.append(actual)
    natives=[]
    for name in NATIVES:
        path=Path(import_module(name).__file__).resolve(strict=True)
        if not path.is_relative_to(packages) or path.suffix.lower() not in ('.pyd','.so'):
            raise core.SurveyError('custody_mismatch','export')
        natives.append(file_pin(path,name))
    value=dict(python_revision=platform.python_version(),os_revision=platform.platform(),
        cpu_identity=platform.processor() or platform.machine(),engine_versions=versions,loaded_modules=files,
        native_modules=natives,threads=1,source_revision=base.digest(files[:len(SOURCES)]))
    value['environment_receipt_sha256']=base.digest(value)
    return schema.typed(value,'Environment')
