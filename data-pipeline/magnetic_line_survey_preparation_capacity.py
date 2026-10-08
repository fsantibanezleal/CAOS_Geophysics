"""Value-free inspection/extraction proof, separate from fit admission."""
import magnetic_line_survey as core

INSPECTION_BYTES=16*1024**2
MEMORY_BYTES=512*1024**2
DESCRIPTOR_BYTES=2*1024**2


def inspection_capacity(original_bytes,document_bytes,bundle_bytes):
    core._count(original_bytes,1,4294967296)
    if type(document_bytes) is not list or len(document_bytes)!=2 or type(bundle_bytes) is not list or not 1<=len(bundle_bytes)<=16:
        raise core.SurveyError('invalid_contract','seal')
    for size in document_bytes:core._count(size,1,2097152)
    for size in bundle_bytes:core._count(size,56,4294967296)
    if sum(bundle_bytes)>4294967296:raise core.SurveyError('resource_refused','seal')
    return dict(schema='m03-owner-inspection-capacity/1',scratch_bound_bytes=INSPECTION_BYTES,
        memory_bound_bytes=MEMORY_BYTES,original_bytes=original_bytes,document_bytes=document_bytes,
        auxiliary_bytes=sum(bundle_bytes),physical_member_cap=min(1000000,sum((size-12)//44 for size in bundle_bytes)),
        value_access='not_opened')


def preparation_capacity(rows,auxiliary_bytes,members):
    core._count(rows,1,8000000);core._count(auxiliary_bytes,56,4294967296);core._count(members,1,1000000)
    if 12+44*members>auxiliary_bytes:raise core.SurveyError('resource_refused','seal')
    index=4096*(16+(2048*members+4095)//4096)
    geometry=65536*rows+67108864
    phase=auxiliary_bytes+2*index+geometry+67108864
    reservation=INSPECTION_BYTES+phase+DESCRIPTOR_BYTES
    if index>2147483648 or reservation>core.SCRATCH_LIMIT:raise core.SurveyError('resource_refused','seal')
    return dict(schema='m03-owner-preparation-capacity/2',original_rows=rows,auxiliary_bytes=auxiliary_bytes,
        physical_members=members,index_and_journal_bytes=2*index,geometry_workspace_bytes=geometry,
        scratch_bound_bytes=phase,memory_bound_bytes=MEMORY_BYTES,dataset_reservation_bytes=reservation,
        logical_member_limit=192,physical_member_limit=1000000,value_access='not_opened',full_job_admission='not_established')
