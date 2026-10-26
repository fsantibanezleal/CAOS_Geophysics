"""Immutable private replay closure and transitive public redaction.

No permission is inferred from convergence, CC0 catalogue metadata, derivative
permission alone or a syntactic SurveyResult. Original bytes are never invented.
"""
from __future__ import annotations

from hashlib import sha256
import os

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_io as io
import magnetic_line_survey_representation_qr as representation
from magnetic_line_survey_result_qr import verify_result,_refs


def _permissions(result,request):
    identities=[result['rights']]+[identity['rights'] for identity in result['input']['auxiliary_identities']]
    private=all(rights['decision']=='allowed' and rights['private_processing']=='allowed' for rights in identities)
    public=private and all(rights['raw_mirroring']=='allowed' and rights['derivative_publication']=='allowed' for rights in identities)
    mirror=private and all(rights['raw_mirroring']=='allowed' for rights in identities) and request['export_policy']['raw_requested']=='include'
    return private,public,mirror


def _copy_original(source,target,original):
    source=io.external_path(source,directory=False)
    identity=sha256()
    count=0
    with source.open('rb') as stream,target.open('xb') as output:
        before=os.fstat(stream.fileno())
        for chunk in iter(lambda:stream.read(1048576),b''):
            count+=len(chunk)
            if count>original['csv_bytes']:
                raise core.SurveyError('custody_mismatch','export')
            identity.update(chunk)
            output.write(chunk)
        after=os.fstat(stream.fileno())
        if core._file_key(before)!=core._file_key(after) or before.st_ctime_ns!=after.st_ctime_ns or \
           core._file_key(after)!=core._file_key(source.stat()) or count!=original['csv_bytes'] or identity.hexdigest()!=original['csv_sha256']:
            raise core.SurveyError('custody_mismatch','export')
        output.flush()
        os.fsync(output.fileno())
    return dict(name='original.csv',bytes=count,sha256=identity.hexdigest())


def export_result(root,destination,*,scope,temp_root,original_csv=None):
    """Export verified closure, or actual redaction receipt with no data roots.

    Public derivatives cannot leak location/row IDs/masks through nested request,
    metadata, array/page manifests or auxiliary objects. Whole result publication
    requires raw and derivative rights across *every* data-bearing source.
    """
    if scope not in ('private','public'):
        raise core.SurveyError('invalid_contract','export')
    root,destination=io.external_path(root),io.external_path(destination)
    if destination.exists():
        raise core.SurveyError('custody_mismatch','export')
    checked=verify_result(root,temp_root=temp_root)
    result=base.strict_json(base.read_bounded(core._plain_path(root/'result.json'),2097152))
    reader=representation.Reader(root)
    request=base.strict_json(reader.member(result['request']))
    private,public,mirror=_permissions(result,request)
    if not private:
        raise core.SurveyError('metadata_ineligible','export')
    destination.mkdir()
    raw=None
    if scope=='public' and not public:
        # Redaction has its own discriminator, not a malformed complete Result.
        manifest=dict(schema='m03-survey-export/3',scope=scope,result_sha256=checked['result_sha256'],
            result=None,original=None,raw_disposition='denied',replay='unresolved',
            redacted=[dict(role='withheld',name=f'withheld-{index:03d}',bytes=0,sha256=None,permission='denied',disposition='denied',
                reason='No transitive raw/location and derivative publication grant') for index in range(len(result['artifacts']))],
            reason='Public derivative permission alone does not authorize original IDs, coordinates, masks or auxiliaries')
    else:
        output=destination/'result'
        output.mkdir()
        for ref in _refs([result,request]):
            reader.verify(ref)
        for item in result['artifacts']:
            if item['disposition']=='included':
                reader.member({key:item[key] for key in ('name','bytes','sha256')})
        # Explicit ChannelReceipt mask targets live in included actual array
        # manifests; verify_result has already proved their semantic binding.
        for identity in list(reader.known.values()):
            if identity['name'].startswith('array-') and identity['name'].endswith('.json') and '-page-' not in identity['name']:
                manifest=base.strict_json(reader.member(identity))
                for page in manifest['pages']:
                    content=base.strict_json(reader.member(page['file']))
                    for entry in content['entries']:
                        member={key:entry[key] for key in ('name','bytes','sha256')}
                        reader._case_identity(member)
                        reader.known[member['name']]=member
        reader.reject_unknown(extra=('result.json',))
        for identity in reader.known.values():
            core._write_member(output,identity['name'],core._verified_member(root,identity,set(),8388608))
        final=core._write_member(output,'result.json',base.read_bounded(core._plain_path(root/'result.json'),2097152))
        verified=verify_result(output,temp_root=temp_root)
        if verified['result_sha256']!=checked['result_sha256']:
            raise core.SurveyError('custody_mismatch','export')
        if mirror and original_csv is not None:
            raw=_copy_original(original_csv,destination/'original.csv',result['input']['original'])
        manifest=dict(schema='m03-survey-export/3',scope=scope,result_sha256=checked['result_sha256'],
            result=final,original=raw,raw_disposition='included' if raw else 'denied' if not mirror else 'unresolved',
            replay='available' if raw else 'unresolved',redacted=[],
            reason='Original acquisition missing or not permitted; no replay success' if raw is None else
                'Original acquisition and permitted immutable private closure retained; replay still requires actual execution')
    core._write_member(destination,'export.json',base.canonical_bytes(manifest))
    return manifest


def verify_export(root,*,temp_root):
    root=io.external_path(root)
    body=base.strict_json(base.read_bounded(core._plain_path(root/'export.json'),2097152))
    core._closed(body,'schema scope result_sha256 result original raw_disposition replay redacted reason','replay')
    if body['schema']!='m03-survey-export/3' or body['scope'] not in ('private','public') or \
       body['raw_disposition'] not in ('included','denied','unresolved') or body['replay'] not in ('available','unresolved'):
        raise core.SurveyError('invalid_contract','replay')
    base._type(body['result_sha256'],'Hash','export',0)
    base._type(body['reason'],'Text','export',0)
    if body['result'] is None:
        if body['scope']!='public' or body['original'] is not None or body['raw_disposition']!='denied' or body['replay']!='unresolved' or \
           type(body['redacted']) is not list or not 1<=len(body['redacted'])<=192:
            raise core.SurveyError('custody_mismatch','replay')
        from magnetic_line_survey_contract_v2 import validate
        for index,member in enumerate(body['redacted']):
            validate('SurveyMember',member)
            if member['disposition']!='denied' or member['permission']!='denied' or member['role']!='withheld' or \
               member['name']!=f'withheld-{index:03d}' or member['bytes']!=0 or member['sha256'] is not None:
                raise core.SurveyError('custody_mismatch','replay')
        if {item.name for item in root.iterdir()}!={'export.json'}:
            raise core.SurveyError('custody_mismatch','replay')
        return body
    from magnetic_line_survey_contract import validate
    identity=validate('FileIdentity',body['result'])
    if identity['name']!='result.json' or body['redacted']!=[]:
        raise core.SurveyError('custody_mismatch','replay')
    payload=core._verified_member(root/'result',identity,set(),2097152)
    if sha256(payload).hexdigest()!=body['result_sha256'] or verify_result(root/'result',temp_root=temp_root)['result_sha256']!=body['result_sha256']:
        raise core.SurveyError('custody_mismatch','replay')
    result=base.strict_json(payload)
    request=base.strict_json(representation.Reader(root/'result').member(result['request']))
    private,public,mirror=_permissions(result,request)
    if not private or body['scope']=='public' and not public:
        raise core.SurveyError('metadata_ineligible','replay')
    expected={'export.json','result'}
    if body['original'] is not None:
        core._closed(body['original'],'name bytes sha256','replay')
        original=result['input']['original']
        if not mirror:
            raise core.SurveyError('metadata_ineligible','replay')
        if body['original']!=dict(name='original.csv',bytes=original['csv_bytes'],sha256=original['csv_sha256']) or \
           body['raw_disposition']!='included' or body['replay']!='available':
            raise core.SurveyError('custody_mismatch','replay')
        source=io.external_path(root/'original.csv',directory=False)
        from magnetic_line_survey_measurements import _verify_original
        with source.open('rb') as stream:
            _verify_original(stream,source,original)
        expected.add('original.csv')
    elif body['raw_disposition']=='included' or body['replay']!='unresolved':
        raise core.SurveyError('custody_mismatch','replay')
    elif body['raw_disposition']!=('unresolved' if mirror else 'denied'):
        raise core.SurveyError('custody_mismatch','replay')
    if {item.name for item in root.iterdir()}!=expected:
        raise core.SurveyError('custody_mismatch','replay')
    return body
