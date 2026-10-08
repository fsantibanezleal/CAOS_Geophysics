"""Value-free prospective 96-inner plus worst-selected-final planning.

Only Python integer arithmetic occurs here, before native allocation or any
measurement decoding. This is a conservative refusal proof, not measured host
admission, a new seal, or authorization to open historical outer observations.
"""
from __future__ import annotations

import magnetic_line_survey as core
import magnetic_line_survey_contract_v2 as schema


def plan_capacity(rows, training_counts, validation_counts, source_counts, *,
                  auxiliary_rows=0, crossover_candidates=0, exported_cells=0,
                  fft_cells=0, raw_bytes=1, auxiliary_bytes=0,
                  retained_member_bytes=0, retained_index_bytes=0,
                  logical_members=0, arrays=0, dictionaries=0, comparator=False):
    """Counts are ordered final/A/B/C; source_counts is four such rows.

    Each exact inner shape participates eight times (two depths/four lambdas).
    Before selection the final shape is MAX over four geometries, not the first
    or subsequently selected shape. Each solve bounds scaling and independent
    gradient with four pair passes plus two per declared 2000 iterations.
    Validation scores every candidate once; outer/grid scores the worst final
    model once. A comparator reserves another worst final solve and prediction.

    Member/index bytes must be conservative producer bounds for *all* retained
    originals, maps, channels and artifacts, not zero-filled runtime receipts.
    Scratch also retains the original independent phase/index allowance; sums
    can overestimate, never discount an unknown winner or future retained file.
    """
    core._count(rows,1,8000000)
    if type(training_counts) is not list or type(validation_counts) is not list or \
       len(training_counts)!=4 or len(validation_counts)!=4 or type(source_counts) is not list or len(source_counts)!=4 or \
       any(type(counts) is not list or len(counts)!=4 for counts in source_counts) or type(comparator) is not bool:
        raise core.SurveyError('invalid_contract','seal')
    for training,validation in zip(training_counts,validation_counts,strict=True):
        core._count(training,1,rows)
        core._count(validation,1,rows)
        if training+validation>rows:
            raise core.SurveyError('invalid_contract','seal')
    for counts in source_counts:
        for index,count in enumerate(counts):
            core._count(count,1,min(training_counts[index],65536))
    for value,maximum in ((auxiliary_rows,16000000),(crossover_candidates,8000000),
            (exported_cells,1048576),(fft_cells,4194304),(auxiliary_bytes,4294967296),
            (retained_member_bytes,34359738368),(retained_index_bytes,34359738368),
            (logical_members,192),(arrays,128),(dictionaries,16)):
        core._count(value,0,maximum)
    core._count(raw_bytes,1,4294967296)
    # Exact-shape cost table, retained in the seal proof separately from the
    # closed CapacityRecord. No native arrays or measurement values are used.
    inner_shapes=[dict(source_geometry_index=g,fold_index=f,rows=training_counts[f],
                       sources=source_counts[g][f],fit_count=8)
                  for g in range(4) for f in range(1,4)]
    inner_fit_pairs=sum(8*4004*shape['rows']*shape['sources'] for shape in inner_shapes)
    inner_prediction_pairs=sum(8*validation_counts[f]*source_counts[g][f] for g in range(4) for f in range(1,4))
    final_fit_pairs=max(4004*training_counts[0]*counts[0] for counts in source_counts)
    final_prediction_pairs=(validation_counts[0]+exported_cells)*max(counts[0] for counts in source_counts)
    comparator_pairs=final_fit_pairs+final_prediction_pairs if comparator else 0
    pairs=inner_fit_pairs+inner_prediction_pairs+final_fit_pairs+final_prediction_pairs+comparator_pairs
    m=max(count for counts in source_counts for count in counts)
    bounds=core.allocation_bounds(rows,m,exported_cells,fft_cells)
    # Sixteen maps each retain exact N_f two-column uint64 membership and M_gf
    # triple float64 sources. Training indexes are shared across geometries.
    maps=sum(16*training_counts[f]+24*source_counts[g][f] for g in range(4) for f in range(4))
    partitions=sum(8*(training_counts[f]+validation_counts[f]+rows) for f in range(4))
    scratch=(2*(raw_bytes+auxiliary_bytes)+512*rows+256*m+256*crossover_candidates+
             256*exported_cells+128*fft_cells+268435456+maps+partitions+
             retained_member_bytes+retained_index_bytes)
    if max(bounds.values())>core.RSS_LIMIT or scratch>core.SCRATCH_LIMIT or pairs>10**15:
        raise core.SurveyError('resource_refused','seal')
    capacity=schema.validate('CapacityRecord',dict(profile='m03-offline-stream/2',rows=rows,sources=m,
        auxiliary_rows=auxiliary_rows,crossover_candidates=crossover_candidates,exported_cells=exported_cells,
        fft_cells=fft_cells,raw_bytes=raw_bytes,auxiliary_bytes=auxiliary_bytes,**bounds,
        scratch_bound_bytes=scratch,kernel_pair_bound=pairs,resource_state='unmeasured'))
    proof=dict(mandatory_fit_count=97,maximum_fit_count=98 if comparator else 97,
        inner_shapes=inner_shapes,inner_fit_pairs=inner_fit_pairs,inner_prediction_pairs=inner_prediction_pairs,
        final_fit_pairs=final_fit_pairs,final_prediction_pairs=final_prediction_pairs,comparator_pairs=comparator_pairs,
        map_bytes=maps,partition_bytes=partitions,retained_member_bytes=retained_member_bytes,
        retained_index_bytes=retained_index_bytes,logical_members=logical_members,arrays=arrays,dictionaries=dictionaries)
    return capacity,proof
