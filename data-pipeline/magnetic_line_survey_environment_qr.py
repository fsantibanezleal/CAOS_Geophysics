"""Actual complete QR environment extension; not an installation grant."""
from importlib import import_module
from pathlib import Path

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract_qr as schema
from magnetic_line_survey_environment import environment_identity as previous,file_pin
from magnetic_line_survey_qr_execution import SOURCES


def environment_identity(package_root,*,job_handle):
    value=previous(package_root,job_handle=job_handle)
    known={item['module_name'] for item in value['loaded_modules']}
    for name in SOURCES:
        if name in known:continue
        path=Path(import_module(name).__file__).resolve(strict=True)
        if path!=Path(__file__).with_name(name+'.py').resolve(strict=True):raise core.SurveyError('custody_mismatch','export')
        value['loaded_modules'].append(file_pin(path,name))
    source_files=[item for item in value['loaded_modules'] if item['module_name'] in SOURCES]
    value['source_revision']=base.digest(source_files)
    value.pop('environment_receipt_sha256')
    value['environment_receipt_sha256']=base.digest(value)
    return schema.typed(value,'Environment')
