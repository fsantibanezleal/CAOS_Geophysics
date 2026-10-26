"""Fixed finite /1-or-/2 member decoding, with explicit new manifest epochs.

No mutation of the legacy reader/roles. Existing members still pass their
original validator; new axes/transfers are only legal with /2 manifests.
"""
from __future__ import annotations

import struct

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract as v1
import magnetic_line_survey_contract_v2 as v2
import magnetic_line_survey_io as io


class Writer(io.Writer):
    def __init__(self, root, identifier, *, role=None, row_schema=None, shape=None,
                 dtype=None, unit=None, mask_array_id=None):
        root = io.external_path(root)
        if role:
            v2.validate('ArrayRef',dict(array_id=identifier,role=role,shape=shape,dtype=dtype,unit=unit,
                chunk_rows=1,manifest=dict(name=f'array-{identifier}.json',bytes=1,sha256='0'*64),
                ordered_ids_sha256='0'*64,mask_array_id=mask_array_id))
        else:
            v2.validate('TableRef',dict(table_id=identifier,row_schema=row_schema,rows=96 if row_schema=='candidate_fit_v2' else 1,
                manifest=dict(name=f'table-{identifier}.json',bytes=1,sha256='0'*64)))
        core._ChunkWriter.__init__(self,root,identifier,role=role,row_schema=row_schema)
        self.shape,self.dtype,self.unit,self.mask=shape,dtype,unit,mask_array_id
        if role:
            width=io.WIDTHS[dtype]*(shape[1] if len(shape)==2 else 1)
            self.chunk_rows=min(4096,8388608//width)
            if self.chunk_rows<1:
                raise core.SurveyError('resource_refused','export')
        else:
            self.chunk_rows=4096

    def finish(self, ordered_ids_sha256=None):
        self.flush()
        self._page()
        if self.role:
            if self.rows!=self.shape[0]:
                raise core.SurveyError('invalid_contract','export')
            manifest=dict(schema='magnetic-line-array-manifest/2',array_id=self.identifier,
                shape=self.shape,dtype=self.dtype,unit=self.unit,pages=self.pages,content_sha256=self.content.hexdigest())
        else:
            manifest=dict(schema='magnetic-line-table-manifest/2',table_id=self.identifier,
                row_schema=self.row_schema,rows=self.rows,pages=self.pages,content_sha256=self.content.hexdigest())
        v2.validate('ArrayManifest' if self.role else 'TableManifest',manifest)
        identity=core._write_member(self.root,f'{self.prefix}-{self.identifier}.json',base.canonical_bytes(manifest))
        if self.role:
            reference=dict(array_id=self.identifier,role=self.role,shape=self.shape,dtype=self.dtype,unit=self.unit,
                chunk_rows=self.chunk_rows,manifest=identity,ordered_ids_sha256=ordered_ids_sha256,mask_array_id=self.mask)
        else:
            reference=dict(table_id=self.identifier,row_schema=self.row_schema,rows=self.rows,manifest=identity)
        return v2.validate('ArrayRef' if self.role else 'TableRef',reference)


class Reader(io.Reader):
    def chunks(self, reference):
        array='array_id' in reference
        v2.validate('ArrayRef' if array else 'TableRef',reference)
        kind='array' if array else 'table'
        body=base.strict_json(self.member(reference['manifest'],2097152))
        if type(body) is not dict:
            raise core.SurveyError('invalid_contract','replay')
        if body.get('schema')==f'magnetic-line-{kind}-manifest/1':
            # Exact original schema, including its original role/shape limits.
            v1.validate('ArrayRef' if array else 'TableRef',reference)
            yield from super().chunks(reference)
            return
        manifest=v2.validate('ArrayManifest' if array else 'TableManifest',body)
        identifier=reference[kind+'_id']
        keys=('array_id','shape','dtype','unit') if array else ('table_id','row_schema','rows')
        if any(manifest[key]!=reference[key] for key in keys):
            raise core.SurveyError('custody_mismatch','replay')
        rows=reference['shape'][0] if array else reference['rows']
        count=sequence=0
        from hashlib import sha256
        identity=sha256()
        if (rows==0)!=(len(manifest['pages'])==0):
            raise core.SurveyError('custody_mismatch','replay')
        for number,page in enumerate(manifest['pages']):
            if page['sequence']!=number or page['first_row']!=count or page['file']['name']!=f'{kind}-{identifier}-page-{number:06d}.json':
                raise core.SurveyError('custody_mismatch','replay')
            # The generic page/chunk layout is unchanged, explicitly shared.
            content=v1.validate('ManifestPage',base.strict_json(self.member(page['file'])))
            if content['owner_id']!=identifier or content['sequence']!=number:
                raise core.SurveyError('custody_mismatch','replay')
            start=count
            for entry in content['entries']:
                if entry['sequence']!=sequence or entry['first_row']!=count or \
                   entry['name']!=f'{kind}-{identifier}-{sequence:08d}.'+('bin' if array else 'jsonl'):
                    raise core.SurveyError('custody_mismatch','replay')
                member={key:entry[key] for key in ('name','bytes','sha256')}
                self._case_identity(member)
                previous=self.known.get(member['name'])
                if previous is not None and previous!=member:
                    raise core.SurveyError('custody_mismatch','replay')
                payload=core._verified_member(self.root,member,set(),8388608)
                self.known[member['name']]=member
                if array:
                    width=io.WIDTHS[reference['dtype']]*(reference['shape'][1] if len(reference['shape'])==2 else 1)
                    if entry['rows']>reference['chunk_rows'] or len(payload)!=entry['rows']*width:
                        raise core.SurveyError('custody_mismatch','replay')
                    identity.update(payload)
                    yield payload
                else:
                    lines=payload.splitlines()
                    if len(lines)!=entry['rows'] or not payload.endswith(b'\n'):
                        raise core.SurveyError('custody_mismatch','replay')
                    decoded=[]
                    for encoded in lines:
                        value=base.strict_json(encoded)
                        if reference['row_schema']=='candidate_fit_v2':
                            value=v2.validate('CandidateFit',value)
                        else:
                            value=v1.validate(v1.TABLE_TYPES[reference['row_schema']],value)
                        if base.canonical_bytes(value)!=encoded:
                            raise core.SurveyError('custody_mismatch','replay')
                        identity.update(struct.pack('<Q',len(encoded))+encoded)
                        decoded.append(value)
                    yield decoded
                count+=entry['rows']
                sequence+=1
            if page['rows']!=count-start:
                raise core.SurveyError('custody_mismatch','replay')
        if count!=rows or identity.hexdigest()!=manifest['content_sha256'] or \
           array and reference['role']=='row_id' and identity.hexdigest()!=reference['ordered_ids_sha256']:
            raise core.SurveyError('custody_mismatch','replay')


def write_array(root,identifier,role,values,shape,dtype,unit,ordered_ids_sha256,mask=None):
    writer=Writer(root,identifier,role=role,shape=shape,dtype=dtype,unit=unit,mask_array_id=mask)
    for value in values:
        cells=value if len(shape)==2 else (value,)
        writer.append(b''.join(io.encoded_cell(cell,dtype) for cell in cells))
    return writer.finish(ordered_ids_sha256)


def write_table(root,identifier,row_schema,records):
    writer=Writer(root,identifier,row_schema=row_schema)
    for value in records:
        value=v2.validate('CandidateFit',value) if row_schema=='candidate_fit_v2' else v1.validate(v1.TABLE_TYPES[row_schema],value)
        encoded=base.canonical_bytes(value)
        writer.append(encoded+b'\n',struct.pack('<Q',len(encoded))+encoded)
    return writer.finish()
