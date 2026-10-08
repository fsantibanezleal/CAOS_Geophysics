"""Bounded structural native datasets, original bytes and explicit dependencies.

No numerical imports, sealed-value decode or inversion during indexing. Parent
unions validators, reconciliation and this route into the canonical application.
"""
from __future__ import annotations

import asyncio
import hashlib
import os
import stat
import uuid
from contextlib import contextmanager

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select, text

from app import joint_contract as native
from app.database import checked_storage_path
from app.errors import ApiError
from app.joint_models import JointDatasetSource
from app.models import AccountUsage, ObservationDataset, RawAsset, SourceRecord, User, utcnow
from app.processing_contract import canonical_bytes, checked_derived_path, dataset_key, sha256, verified_json
from app.processing_storage import account_derived_usage
from app.projects import _owned_asset, _owned_project

REQUEST_CAP = 65536
MAX_MEMBERS = 40
SCHEMA = 'geophysics.joint-native-dataset/v1'


def member_request(raw):
    if len(raw) > REQUEST_CAP: raise ValueError('joint_dataset_request_cap')
    value = native.bounded_json(raw)
    native._keys(value, ('development', 'sealed'))
    seen = set()
    for role, members in value.items():
        if type(members) is not dict or not members: raise ValueError('joint_dataset_members')
        for name, asset_id in members.items():
            if type(asset_id) is not str or str(uuid.UUID(asset_id)) != asset_id or asset_id in seen:
                raise ValueError('joint_dataset_unique_asset')
            seen.add(asset_id)
            # Closed upload names without inventing a scientific descriptor.
            allowed = {k+'.npy' for k in (native.DEVELOPMENT if role == 'development' else native.SEALED)}
            allowed |= {'request.json','gravity.raw','magnetic.raw','gravity.corrections.json','magnetic.corrections.json'} if role == 'development' else {'sealed.json'}
            if name not in allowed: raise ValueError('joint_dataset_name')
    if len(seen) > MAX_MEMBERS: raise ValueError('joint_dataset_member_cap')
    if 'request.json' not in value['development'] or 'sealed.json' not in value['sealed']:
        raise ValueError('joint_dataset_manifest_required')
    return value


@contextmanager
def held_original(settings, asset):
    native.external_root(settings.data_dir)
    if asset.storage_key != f'projects/{asset.owner_id}/{asset.project_id}/{asset.id}':
        raise ValueError('joint_source_path_binding')
    path = checked_storage_path(settings, asset.storage_key)
    for parent in (path, *path.parents):
        info = parent.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info,'st_file_attributes',0)&stat.FILE_ATTRIBUTE_REPARSE_POINT:
            raise ValueError('joint_source_reparse')
        if parent == settings.data_dir: break
    named_before = path.lstat()
    with path.open('rb') as stream:
        before = os.fstat(stream.fileno())
        if not stat.S_ISREG(before.st_mode) or before.st_size != asset.byte_count:
            raise ValueError('joint_source_file_size')
        yield stream
        after = os.fstat(stream.fileno()); named = path.lstat()
        identity = lambda info:(info.st_dev,info.st_ino,info.st_size,info.st_mtime_ns)
        # Windows fstat and lstat do not expose the same ctime namespace.
        # Retain exact ctime stability IN EACH namespace, not their equality.
        if (identity(before) != identity(after) or identity(after) != identity(named)
                or identity(named_before) != identity(named)
                or before.st_ctime_ns != after.st_ctime_ns or named_before.st_ctime_ns != named.st_ctime_ns):
            raise ValueError('joint_source_file_changed')


def scan_member(settings, asset, source, role, name):
    binding = native.source_identity(asset,source,owner_id=asset.owner_id,project_id=asset.project_id)
    meta = asset.physical_metadata
    if (asset.detected_format != 'joint_native' or asset.filename != name
            or type(meta) is not dict or set(meta) != {'schema','role','name','descriptor','scientific_values_decoded','scientific_accepted'}
            or meta['schema'] != 'joint-native-member-1' or meta['role'] != role or meta['name'] != name
            or meta['scientific_values_decoded'] is not False or meta['scientific_accepted'] is not False):
        raise ValueError('joint_source_member_binding')
    descriptor = meta['descriptor']
    native.member_metadata(canonical_bytes({'role':role,'name':name,'descriptor':descriptor,
        'source':{'expected_bytes':asset.byte_count,'expected_sha256':asset.sha256}}))
    with held_original(settings,asset) as stream:
        head = stream.read(4106); stream.seek(0)
        digest = hashlib.sha256(); count = 0
        for chunk in iter(lambda:stream.read(1024*1024),b''):
            count += len(chunk)
            if count > asset.byte_count: raise ValueError('joint_source_file_grew')
            digest.update(chunk)
        if digest.hexdigest() != asset.sha256: raise ValueError('joint_source_original_digest')
        if descriptor is not None:
            offset = native.native_header(head,descriptor,asset.byte_count)
            stream.seek(offset); digest = hashlib.sha256()
            for chunk in iter(lambda:stream.read(1024*1024),b''): digest.update(chunk)
            if digest.hexdigest() != descriptor['data_sha256']: raise ValueError('joint_source_data_digest')
        raw = None
        if name.endswith('.json'):
            if asset.byte_count > native.MAX_JSON: raise ValueError('joint_source_json_cap')
            stream.seek(0); raw = stream.read(native.MAX_JSON+1)
    return {**binding,'descriptor':descriptor}, raw


def close_manifests(payload):
    manifests = payload['manifests']; sources = payload['members']; total = 0
    parsed = {}
    for role in ('development','sealed'):
        main = 'request.json' if role == 'development' else 'sealed.json'
        raw = canonical_bytes(manifests[role])
        parsed[role], expected = native.manifest(raw,role)
        if set(sources[role]) != set(expected): raise ValueError('joint_dataset_exact_inventory')
        for name, original in expected.items():
            binding = sources[role][name]
            # Input JSON may be valid noncanonical UTF8. Its actual byte identity
            # is in the source row; canonicalized metadata is not its original.
            if name != main and (binding['raw_sha256'] != original['sha256']
                    or original['bytes'] is not None and binding['raw_bytes'] != original['bytes']):
                raise ValueError('joint_dataset_original_binding')
            if name.endswith('.npy') and binding['descriptor'] != parsed[role]['arrays'][name[:-4]]:
                raise ValueError('joint_dataset_descriptor_binding')
            total += binding['raw_bytes']
    if total > native.MAX_BYTES: raise ValueError('joint_dataset_total_bytes')
    dev, sealed = parsed['development'], parsed['sealed']
    if sealed['payload']['plan_sha256'] != dev['development']['plan_sha256']:
        raise ValueError('joint_dataset_plan_binding')
    seal = dev['sealed_manifest']; native._keys(seal, ('schema','gravity','magnetic'))
    if seal['schema'] != 'joint-survey-sealed-manifest-1': raise ValueError('joint_dataset_sealed_schema')
    for m in ('gravity','magnetic'):
        declaration = seal[m]
        native._keys(declaration,('count','noise_kind','observations_file_sha256','noise_file_sha256','rows_sha256'))
        rows, observed, noise = (sealed['arrays'][m+'_'+name] for name in ('rows','observed','noise'))
        if (type(declaration['count']) is not int or rows['shape'] != [declaration['count']]
                or observed['shape'] != rows['shape'] or declaration['rows_sha256'] != rows['data_sha256']
                or declaration['observations_file_sha256'] != observed['file_sha256']
                or declaration['noise_file_sha256'] != noise['file_sha256']
                or declaration['noise_kind'] not in ('diagonal_sd','full_covariance')
                or noise['shape'] != ([declaration['count']] if declaration['noise_kind']=='diagonal_sd' else [declaration['count']]*2)):
            raise ValueError('joint_dataset_sealed_binding')
    return sum(dev['arrays'][m+'_receivers']['shape'][0] for m in ('gravity','magnetic'))


def validate_dataset(payload, dataset):
    native._keys(payload,('schema','dataset_id','version','owner_id','project_id','raw_asset_id',
        'parent_raw_sha256','parser_version','modality','dimensions','manifests','members',
        'qc_verdict','scientific_values_decoded','scientific_accepted'))
    if (payload['schema'] != SCHEMA or payload['dataset_id'] != dataset.id or type(payload['version']) is not int
            or payload['version'] != dataset.version or payload['owner_id'] != str(dataset.owner_id)
            or payload['project_id'] != dataset.project_id or payload['raw_asset_id'] != dataset.raw_asset_id
            or payload['parent_raw_sha256'] != dataset.raw_sha256 or payload['parser_version'] != native.PARSER
            or dataset.parser_version != native.PARSER or payload['modality'] != native.MODALITY or dataset.modality != native.MODALITY
            or payload['scientific_values_decoded'] is not False or payload['scientific_accepted'] is not False
            or payload['qc_verdict'] != 'structural_native_members_only'
            or payload['dimensions'] != {'source_observations':dataset.row_count}
            or close_manifests(payload) != dataset.row_count):
        raise ValueError('joint_dataset_identity')
    seen = set()
    for members in payload['members'].values():
        for binding in members.values():
            native._keys(binding,('asset_id','source_id','source_version','raw_sha256','raw_bytes',
                'rights_decision','private_storage_permission','descriptor'))
            if binding['asset_id'] in seen: raise ValueError('joint_dataset_duplicate_asset')
            seen.add(binding['asset_id'])
    primary = payload['members']['development']['request.json']
    if primary['asset_id'] != dataset.raw_asset_id or primary['raw_sha256'] != dataset.raw_sha256:
        raise ValueError('joint_dataset_primary_binding')


async def validate_source_rows(settings, session, dataset, payload):
    validate_dataset(payload,dataset)
    rows = (await session.execute(select(JointDatasetSource).where(JointDatasetSource.dataset_id==dataset.id))).scalars().all()
    expected = {(role,name):binding for role,members in payload['members'].items() for name,binding in members.items()}
    if {(row.role,row.name) for row in rows} != set(expected): raise ValueError('joint_dataset_dependency_inventory')
    for row in rows:
        binding = expected[row.role,row.name]
        if any(getattr(row,k) != binding[k] for k in ('asset_id','source_id','raw_sha256','raw_bytes','source_version')):
            raise ValueError('joint_dataset_dependency_binding')
        asset = await session.get(RawAsset,row.asset_id); source = await session.get(SourceRecord,row.source_id)
        if asset is None or source is None: raise ValueError('joint_dataset_dependency_missing')
        native.source_identity(asset,source,owner_id=dataset.owner_id,project_id=dataset.project_id)
        actual, raw = await asyncio.to_thread(scan_member,settings,asset,source,row.role,row.name)
        if actual != binding: raise ValueError('joint_dataset_dependency_changed')
        if row.name in ('request.json','sealed.json') and native.bounded_json(raw) != payload['manifests'][row.role]:
            raise ValueError('joint_dataset_manifest_changed')


async def materialize_inputs(settings, session, dataset, payload, stage):
    """Exclusive original input copies for the fixed worker, not an API path.

    Any failed/uncertain stage is retained for exact recovery. This function
    neither decodes native values nor starts a job or grants host admission.
    """
    await validate_source_rows(settings,session,dataset,payload)
    native.external_root(stage)
    target = stage/'inputs'
    if target.exists() or target.is_symlink(): raise ValueError('joint_input_exclusive_stage')
    target.mkdir(mode=0o700)
    def copy(asset,destination):
        digest = hashlib.sha256(); count = 0
        with held_original(settings,asset) as source, destination.open('xb') as output:
            for chunk in iter(lambda:source.read(1024*1024),b''):
                count += len(chunk)
                if count > asset.byte_count: raise ValueError('joint_input_copy_cap')
                output.write(chunk);digest.update(chunk)
            output.flush();os.fsync(output.fileno())
        if count != asset.byte_count or digest.hexdigest() != asset.sha256:
            raise ValueError('joint_input_copy_binding')
    for role,members in payload['members'].items():
        directory = target/role;directory.mkdir(mode=0o700)
        for name,binding in members.items():
            asset = await session.get(RawAsset,binding['asset_id'])
            if asset is None: raise ValueError('joint_input_source_missing')
            await asyncio.to_thread(copy,asset,directory/name)
        if {path.name for path in directory.iterdir()} != set(members):
            raise ValueError('joint_input_exact_inventory')
    await validate_source_rows(settings,session,dataset,payload)
    return {role:target/role for role in ('development','sealed')}


async def audit_dependencies(settings, session, datasets):
    """Canonical startup/export union: all source rows, including orphan refusal."""
    joint_datasets = {item.id:item for item in datasets if item.modality==native.MODALITY}
    rows = (await session.execute(select(JointDatasetSource.dataset_id))).scalars().all()
    if any(identity not in joint_datasets for identity in rows):
        raise ValueError('joint_dataset_orphan_dependency')
    for dataset in joint_datasets.values():
        if dataset.storage_key != dataset_key(str(dataset.owner_id),dataset.project_id,dataset.id):
            raise ValueError('joint_dataset_path_binding')
        payload = verified_json(settings,dataset.storage_key,dataset.sha256,dataset.byte_count)
        await validate_source_rows(settings,session,dataset,payload)


def install_joint_dataset_routes(app, settings, current_user, get_session, *, register_root=None):
    router = APIRouter(prefix='/api/projects/{project_id}',tags=['joint-native'])

    @router.post('/joint-datasets',status_code=201)
    async def create_dataset(project_id:str, request:Request, user:User=Depends(current_user), session=Depends(get_session)):
        await _owned_project(session,project_id,user)
        raw = bytearray()
        async for chunk in request.stream():
            if len(raw)+len(chunk)>REQUEST_CAP: raise ApiError(413,'joint_dataset_request_cap','Native dataset request exceeds its bound')
            raw.extend(chunk)
        try: members = member_request(bytes(raw))
        except (ValueError,TypeError,KeyError) as exc:
            raise ApiError(422,'joint_dataset_members_invalid','Native dataset members are invalid') from exc
        await session.rollback(); await session.execute(text('BEGIN IMMEDIATE')); await session.refresh(user)
        await _owned_project(session,project_id,user)
        bindings = {}; manifests = {}; primary = None; originals = {}; total = 0
        try:
            # Close combined declared size before any member hashing/scan.
            for role, names in members.items():
                for name, asset_id in names.items():
                    asset, source = await _owned_asset(session,project_id,asset_id,user)
                    native.source_identity(asset,source,owner_id=user.id,project_id=project_id)
                    total += asset.byte_count
                    if total > native.MAX_BYTES: raise ValueError('joint_dataset_total_bytes')
                    originals[role,name] = (asset,source)
            for role, names in members.items():
                bindings[role] = {}
                for name, asset_id in names.items():
                    asset, source = originals[role,name]
                    bindings[role][name], original = await asyncio.to_thread(scan_member,settings,asset,source,role,name)
                    if name in ('request.json','sealed.json'): manifests[role] = native.bounded_json(original)
                    if role=='development' and name=='request.json': primary = asset
            existing = (await session.execute(select(ObservationDataset.id).where(
                ObservationDataset.raw_asset_id==primary.id,ObservationDataset.parser_version==native.PARSER))).scalar_one_or_none()
            if existing is not None: raise ApiError(409,'dataset_exists','This native request already has an immutable dataset')
            identity = str(uuid.uuid4())
            payload = {'schema':SCHEMA,'dataset_id':identity,'version':1,'owner_id':str(user.id),'project_id':project_id,
                'raw_asset_id':primary.id,'parent_raw_sha256':primary.sha256,'parser_version':native.PARSER,
                'modality':native.MODALITY,'dimensions':{},'manifests':manifests,'members':bindings,
                'qc_verdict':'structural_native_members_only','scientific_values_decoded':False,'scientific_accepted':False}
            count = close_manifests(payload); payload['dimensions'] = {'source_observations':count}
        except (ValueError,TypeError,KeyError,OSError) as exc:
            raise ApiError(422,'joint_dataset_original_invalid','Native dataset originals or source bindings are invalid') from exc
        encoded = canonical_bytes(payload)
        if len(encoded)>native.MAX_JSON: raise ApiError(413,'joint_dataset_index_cap','Native dataset index exceeds its bound')
        raw_usage = (await session.execute(select(AccountUsage.raw_bytes).where(AccountUsage.user_id==user.id))).scalar_one_or_none() or 0
        if raw_usage+await account_derived_usage(session,user.id)+len(encoded)>settings.account_quota_bytes:
            raise ApiError(507,'account_quota_exceeded','Account private-byte quota exceeded')
        key = dataset_key(str(user.id),project_id,identity); target = checked_derived_path(settings,key)
        target.parent.mkdir(parents=True,exist_ok=True)
        created = attempted = committed = False
        try:
            with target.open('xb') as stream:
                created = True; stream.write(encoded); stream.flush(); os.fsync(stream.fileno())
            dataset = ObservationDataset(id=identity,project_id=project_id,owner_id=user.id,raw_asset_id=primary.id,
                version=1,parser_version=native.PARSER,modality=native.MODALITY,row_count=count,raw_sha256=primary.sha256,
                sha256=sha256(encoded),byte_count=len(encoded),storage_key=key,created_at=utcnow())
            if register_root is None:
                session.add(dataset); await session.flush()
            else:
                dataset = await register_root(session,dataset,payload)
            for role, names in bindings.items():
                for name,binding in names.items():
                    session.add(JointDatasetSource(dataset_id=identity,role=role,name=name,
                        **{k:binding[k] for k in ('asset_id','source_id','raw_sha256','raw_bytes','source_version')}))
            await session.flush(); attempted = True; await session.commit(); committed = True
            return {'dataset_id':identity,'project_id':project_id,'raw_asset_id':primary.id,'parser_version':native.PARSER,
                'modality':native.MODALITY,'row_count':count,'sha256':dataset.sha256,'qc_verdict':payload['qc_verdict'],
                'scientific_accepted':False,'receipt_url':f'/api/projects/{project_id}/joint-datasets/{identity}'}
        finally:
            if not committed:
                await session.rollback()
                if created and not attempted: target.unlink(missing_ok=True)

    @router.get('/joint-datasets/{dataset_id}')
    async def get_dataset(project_id:str, dataset_id:str, user:User=Depends(current_user), session=Depends(get_session)):
        await _owned_project(session,project_id,user)
        dataset = (await session.execute(select(ObservationDataset).where(ObservationDataset.id==dataset_id,
            ObservationDataset.owner_id==user.id,ObservationDataset.project_id==project_id,ObservationDataset.modality==native.MODALITY))).scalar_one_or_none()
        if dataset is None: raise ApiError(404,'not_found','Native dataset not found')
        try:
            if dataset.storage_key != dataset_key(str(user.id),project_id,dataset.id): raise ValueError('joint_dataset_path_binding')
            payload = verified_json(settings,dataset.storage_key,dataset.sha256,dataset.byte_count)
            await validate_source_rows(settings,session,dataset,payload)
        except (ValueError,TypeError,KeyError,OSError) as exc:
            raise ApiError(409,'joint_dataset_integrity_failed','Native dataset or source dependencies changed') from exc
        return JSONResponse(payload,headers={'Cache-Control':'no-store'})

    app.include_router(router)
