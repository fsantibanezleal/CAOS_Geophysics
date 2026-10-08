"""New typed QR tables; original array/table /1-/2 readers are unchanged."""
from hashlib import sha256
import struct

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract as original
import magnetic_line_survey_contract_qr as schema
import magnetic_line_survey_io as io
import magnetic_line_survey_representation as previous

write_array=previous.write_array


class Writer(previous.Writer):
    def __init__(self,root,identifier,*,row_schema=None,**kwargs):
        if row_schema not in schema.QR_TABLES:
            super().__init__(root,identifier,row_schema=row_schema,**kwargs)
            return
        if kwargs:raise core.SurveyError('invalid_contract','export')
        schema.validate('TableRef',dict(table_id=identifier,row_schema=row_schema,
            rows=96 if row_schema=='candidate_fit_qr_v3' else 97,
            manifest=dict(name=f'table-{identifier}.json',bytes=1,sha256='0'*64)))
        core._ChunkWriter.__init__(self,io.external_path(root),identifier,row_schema=row_schema)
        self.chunk_rows=4096

    def finish(self,ordered_ids_sha256=None):
        if self.row_schema not in schema.QR_TABLES:return super().finish(ordered_ids_sha256)
        if ordered_ids_sha256 is not None:raise core.SurveyError('invalid_contract','export')
        self.flush();self._page()
        manifest=schema.validate('TableManifest',dict(schema='magnetic-line-table-manifest/3',table_id=self.identifier,
            row_schema=self.row_schema,rows=self.rows,pages=self.pages,content_sha256=self.content.hexdigest()))
        member=core._write_member(self.root,f'table-{self.identifier}.json',base.canonical_bytes(manifest))
        return schema.validate('TableRef',dict(table_id=self.identifier,row_schema=self.row_schema,rows=self.rows,manifest=member))


class Reader(previous.Reader):
    def chunks(self,reference):
        if reference.get('row_schema') not in schema.QR_TABLES:
            yield from super().chunks(reference)
            return
        reference=schema.validate('TableRef',reference)
        manifest=schema.validate('TableManifest',base.strict_json(self.member(reference['manifest'],2097152)))
        identifier=reference['table_id']
        if any(reference[key]!=manifest[key] for key in ('table_id','row_schema','rows')):
            raise core.SurveyError('custody_mismatch','replay')
        count=sequence=0;identity=sha256()
        for number,page in enumerate(manifest['pages']):
            if page['sequence']!=number or page['first_row']!=count or page['file']['name']!=f'table-{identifier}-page-{number:06d}.json':
                raise core.SurveyError('custody_mismatch','replay')
            content=original.validate('ManifestPage',base.strict_json(self.member(page['file'])))
            if content['owner_id']!=identifier or content['sequence']!=number:raise core.SurveyError('custody_mismatch','replay')
            start=count
            for entry in content['entries']:
                if entry['sequence']!=sequence or entry['first_row']!=count or entry['name']!=f'table-{identifier}-{sequence:08d}.jsonl':
                    raise core.SurveyError('custody_mismatch','replay')
                member={key:entry[key] for key in ('name','bytes','sha256')}
                self._case_identity(member)
                previous_member=self.known.get(member['name'])
                if previous_member is not None and previous_member!=member:raise core.SurveyError('custody_mismatch','replay')
                payload=core._verified_member(self.root,member,set(),8388608);self.known[member['name']]=member
                lines=payload.splitlines()
                if len(lines)!=entry['rows'] or not payload.endswith(b'\n'):raise core.SurveyError('custody_mismatch','replay')
                decoded=[]
                for encoded in lines:
                    if len(encoded)+1>4096:raise core.SurveyError('resource_refused','replay')
                    value=schema.validate(schema.QR_TABLES[reference['row_schema']],base.strict_json(encoded))
                    if base.canonical_bytes(value)!=encoded:raise core.SurveyError('custody_mismatch','replay')
                    identity.update(struct.pack('<Q',len(encoded))+encoded);decoded.append(value)
                yield decoded
                count+=entry['rows'];sequence+=1
            if page['rows']!=count-start:raise core.SurveyError('custody_mismatch','replay')
        if count!=reference['rows'] or identity.hexdigest()!=manifest['content_sha256']:raise core.SurveyError('custody_mismatch','replay')


def write_table(root,identifier,row_schema,records):
    if row_schema not in schema.QR_TABLES:return previous.write_table(root,identifier,row_schema,records)
    writer=Writer(root,identifier,row_schema=row_schema)
    for record in records:
        encoded=base.canonical_bytes(schema.validate(schema.QR_TABLES[row_schema],record))
        if len(encoded)+1>4096:raise core.SurveyError('resource_refused','export')
        writer.append(encoded+b'\n',struct.pack('<Q',len(encoded))+encoded)
    return writer.finish()
