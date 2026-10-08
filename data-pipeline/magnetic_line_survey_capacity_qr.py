"""New QR complete-shape proof, NOT a relabelled iterative policy."""
import magnetic_line_survey as core
import magnetic_line_survey_capacity_hp as hp
import magnetic_line_survey_qr as qr


def plan_capacity(rows,training_counts,validation_counts,source_counts,**options):
    capacity,proof=hp.plan_capacity(rows,training_counts,validation_counts,source_counts,**options)
    capacity,proof=dict(capacity),dict(proof)
    inner_pairs=sum(8*s['rows']*s['sources'] for s in proof['inner_shapes'])
    final_pairs=max(training_counts[0]*counts[0] for counts in source_counts)
    comparator=options.get('comparator',False)
    total_pairs=inner_pairs+final_pairs*(2 if comparator else 1)
    capacity['kernel_pair_bound']-=4000*total_pairs
    proof['inner_fit_pairs']=6*inner_pairs
    proof['final_fit_pairs']=6*final_pairs
    proof['comparator_pairs']=proof['final_fit_pairs']+proof['final_prediction_pairs'] if comparator else 0
    shapes=[qr.dense_capacity(training_counts[f],source_counts[g][f]) for g in range(4) for f in range(4)]
    conservative=qr.dense_capacity(rows,capacity['sources'])
    extra=max(s['extra_peak_bytes'] for s in [*shapes,conservative])
    work=sum(8*shapes[g*4+f]['factorization_work_bound'] for g in range(4) for f in range(1,4))
    final_work=max(shapes[g*4]['factorization_work_bound'] for g in range(4))
    work+=final_work*(2 if comparator else 1)
    for key in ('fit_buffer_bytes','geometry_buffer_bytes','transform_buffer_bytes'):capacity[key]+=extra
    table=2097152+4096*proof['maximum_fit_count'];index=4096
    capacity['scratch_bound_bytes']+=table+index
    proof['logical_members']+=1
    proof['retained_member_bytes']+=table
    proof['retained_index_bytes']+=index
    proof.update(policy_epoch=qr.EPOCH,kernel_passes_per_fit=6,
        qr_shapes=shapes,qr_conservative_shape=conservative,additional_dense_bytes=extra,
        qr_receipt_table_bytes=table,qr_receipt_index_bytes=index,
        additional_physical_members=4,factorization_work_bound=work,factorization_work_limit=10**12)
    capacity['profile']='m03-offline-direct-qr/1'
    if proof['logical_members']>192 or proof['arrays']>128 or work>10**12 or \
       capacity['kernel_pair_bound']>10**15 or capacity['scratch_bound_bytes']>core.SCRATCH_LIMIT or \
       max(capacity[k] for k in ('fit_buffer_bytes','geometry_buffer_bytes','transform_buffer_bytes'))>core.RSS_LIMIT:
        raise core.SurveyError('resource_refused','seal')
    return capacity,proof
