"""Separate HP prospective proof; frozen v2 proof remains byte-unchanged."""
import magnetic_line_survey as core
import magnetic_line_survey_capacity_v2 as v2


def plan_capacity(rows, training_counts, validation_counts, source_counts, **options):
    capacity, proof = v2.plan_capacity(rows, training_counts, validation_counts, source_counts, **options)
    capacity, proof = dict(capacity), dict(proof)
    all_fit_pairs = sum(8*item['rows']*item['sources'] for item in proof['inner_shapes'])
    final_shape = max(training_counts[0]*row[0] for row in source_counts)
    comparator = options.get('comparator', False)
    proof['inner_fit_pairs'] = 4006*all_fit_pairs
    proof['final_fit_pairs'] = 4006*final_shape
    proof['comparator_pairs'] = proof['final_fit_pairs']+proof['final_prediction_pairs'] if comparator else 0
    # Independent P reconstruction for EACH identity, not just the winner:
    # two unweighted STD passes and one weighted-column pass. Conservatively
    # keep the old independent final objective/gradient/prediction allowance too.
    proof['preconditioner_verification_pairs'] = 3*(all_fit_pairs+final_shape*(2 if comparator else 1))
    added_pairs = 2*(all_fit_pairs+final_shape*(2 if comparator else 1))+proof['preconditioner_verification_pairs']
    capacity['kernel_pair_bound'] += added_pairs
    vectors = 8*(24*rows+32*capacity['sources'])
    for key in ('fit_buffer_bytes', 'geometry_buffer_bytes', 'transform_buffer_bytes'):
        capacity[key] += vectors
    # One bounded 97-row identity table, NOT 97 arrays. Actual incoming closure
    # is authoritative: current corrected S3 has125 logical/104 arrays, not119/98.
    table_bytes = 2097152+4096*proof['maximum_fit_count']
    index_bytes = 4096
    proof['logical_members'] += 1
    proof['retained_member_bytes'] += table_bytes
    proof['retained_index_bytes'] += index_bytes
    capacity['scratch_bound_bytes'] += vectors+table_bytes+index_bytes
    proof.update(policy_epoch='augmented_hp/1', kernel_passes_per_fit=4006,
        additional_vector_bytes=vectors, augmented_rows_max=rows+capacity['sources'],
        preconditioner_table_bytes=table_bytes, preconditioner_index_bytes=index_bytes,
        additional_physical_members=2, preconditioner_arrays=0)
    capacity['profile'] = 'm03-offline-hp/1'
    if proof['logical_members'] > 192 or proof['arrays'] > 128 or \
       capacity['kernel_pair_bound'] > 10**15 or capacity['scratch_bound_bytes'] > core.SCRATCH_LIMIT or \
       max(capacity[k] for k in ('fit_buffer_bytes', 'geometry_buffer_bytes', 'transform_buffer_bytes')) > core.RSS_LIMIT:
        raise core.SurveyError('resource_refused', 'seal')
    return capacity, proof
