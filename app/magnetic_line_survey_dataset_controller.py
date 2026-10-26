"""Fixed, genuinely executing Windows preparation; no default installation grant.

The installation verifier is mandatory trusted backend assembly. It must bind
this method to installed code/environment/roots/caps, or refuse. Merely hashing
current files, a fixture pin, or an ERT/TT-only authority is not that grant.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from hashlib import sha256
import importlib
import os
from pathlib import Path
import sys
from typing import Protocol

from app.config import Settings
from app.errors import ApiError
from app.magnetic_line_survey_lifecycle import storage_root,validate_drain
from app.magnetic_line_survey_wire import _hash

METHOD='m03.owner-dataset-preparation/v1'
PIPELINE=Path(__file__).resolve().parents[1]/'data-pipeline'


class InstalledPreparationVerifier(Protocol):
    def verify(self,settings:Settings,*,method:str,source_sha256:dict,
               executable:Path,executable_sha256:str,package_root:Path)->str:
        """Verify real installation authority; return its SHA, never derive a grant."""


@dataclass(frozen=True)
class PreparationAuthority:
    sha256:str
    source_sha256:dict
    executable_sha256:str


def refuse():
    raise ApiError(409,'survey_preparation_authority_missing','Actual fixed preparation installation is required')


def _sources():
    tree=ast.parse((PIPELINE/'magnetic_line_survey_runtime.py').read_bytes())
    candidates=[node.value for node in ast.walk(tree) if isinstance(node,ast.Assign) and
        any(isinstance(target,ast.Name) and target.id=='source_names' for target in node.targets)]
    if len(candidates)!=1:refuse()
    names=ast.literal_eval(candidates[0])
    if type(names) is not tuple or not names or len(set(names))!=len(names):refuse()
    result={}
    for name in names:
        if type(name) is not str or Path(name).name!=name or not name.endswith('.py'):refuse()
        path=PIPELINE/name
        if path.is_symlink() or not path.is_file():refuse()
        result[name]=sha256(path.read_bytes()).hexdigest()
    return result


def _fixed_module(name):
    # No caller module name reaches this function. Reject a previously imported
    # copy from another concurrent checkout rather than silently reusing it.
    existing=sys.modules.get(name)
    expected=(PIPELINE/(name+'.py')).resolve(strict=True)
    if existing is not None and Path(existing.__file__).resolve()!=expected:refuse()
    if str(PIPELINE) not in sys.path:sys.path.insert(0,str(PIPELINE))
    module=importlib.import_module(name)
    if Path(module.__file__).resolve()!=expected:refuse()
    for leaf in _sources():
        imported=sys.modules.get(leaf[:-3])
        if imported is not None and Path(imported.__file__).resolve()!=(PIPELINE/leaf).resolve():refuse()
    return module


class WindowsPreparationController:
    """Component controller. Parent must supply an independently reviewed grant.

    No native launch occurs in the constructor, and no default verifier exists.
    This does not mount routes, edit configuration or enable production methods.
    """
    def __init__(self,executable:Path,package_root:Path,*,installation:InstalledPreparationVerifier):
        if installation is None or not callable(getattr(installation,'verify',None)):refuse()
        self.executable=executable.resolve(strict=True)
        self.package_root=package_root.resolve(strict=True)
        self.installation=installation

    def snapshot(self,settings:Settings)->PreparationAuthority:
        if os.name!='nt' or not self.executable.is_file() or self.executable.is_symlink() or \
           not self.package_root.is_dir() or self.package_root.is_symlink():refuse()
        storage_root(settings.data_dir)
        sources=_sources();executable_hash=sha256(self.executable.read_bytes()).hexdigest()
        installed_sources=dict(sources)
        for name in ('magnetic_line_survey_dataset_controller.py','magnetic_line_survey_dataset.py',
                'magnetic_line_survey_dataset_accounting.py','magnetic_line_survey_dataset_api.py',
                'magnetic_line_survey_dataset_recovery.py',
                'magnetic_line_survey_wire.py'):
            installed_sources['app/'+name]=sha256(Path(__file__).with_name(name).read_bytes()).hexdigest()
        authority=self.installation.verify(settings,method=METHOD,source_sha256=installed_sources,
            executable=self.executable,executable_sha256=executable_hash,package_root=self.package_root)
        try:_hash(authority)
        except ValueError:refuse()
        return PreparationAuthority(authority,sources,executable_hash)

    def run(self,settings:Settings,authority:PreparationAuthority,workspace:Path,limits:dict)->dict:
        if self.snapshot(settings)!=authority:refuse()
        runtime=_fixed_module('magnetic_line_survey_runtime')
        lifetime=runtime.run_worker(self.executable,self.package_root,workspace,workspace/'plan.json',configured_limits=limits)
        validate_drain(lifetime)
        if self.snapshot(settings)!=authority or lifetime['source_sha256']!=authority.source_sha256 or \
           lifetime['actual_executable_sha256']!=authority.executable_sha256:refuse()
        return lifetime

    def verify_preparation(self,settings:Settings,authority:PreparationAuthority,workspace:Path)->dict:
        if self.snapshot(settings)!=authority:refuse()
        base=_fixed_module('magnetic_line_contract')
        core=_fixed_module('magnetic_line_survey')
        bundle=_fixed_module('magnetic_line_survey_bundle')
        receipt=base.strict_json(base.read_bounded(core._plain_path(workspace/'preparation.json'),2097152))
        core._closed(receipt,'schema original metadata_sha256 request_sha256 bundle_sha256 rows geometry geometry_sha256 logical_members physical_members capacity semantic_closure value_access field_eligibility scientific_result','replay')
        if receipt['schema']!='m03-owner-preparation-receipt/1' or receipt['value_access']!='not_opened' or \
           receipt['semantic_closure']!='schema_recognized_encoded_bytes' or \
           receipt['field_eligibility']!='not_established' or receipt['scientific_result']!='not_established':refuse()
        actual=core.verify_geometry_inspection(workspace/'geometry',receipt['geometry'])
        if actual!=receipt['geometry'] or base.digest(actual)!=receipt['geometry_sha256']:refuse()
        # Closed source-document validators and original geometry, not receipt
        # status alone. Full bundle extraction was verified by the fixed child.
        plan=base.strict_json(base.read_bounded(core._plain_path(workspace/'plan.json'),2097152))
        metadata,request=bundle.decode_documents(bundle._verified_document(plan['metadata']),bundle._verified_document(plan['request']))
        if receipt['original']!=metadata['original'] or actual['original']!=metadata['original'] or \
           actual['arrays']!=metadata['arrays'] or actual['rows']!=receipt['rows'] or \
           request['dataset_version_sha256']!=base.dataset_identity(plan['original']['sha256'],base.digest(metadata)):refuse()
        if self.snapshot(settings)!=authority:refuse()
        return receipt
