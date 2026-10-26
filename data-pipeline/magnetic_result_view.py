"""Owner-resolved immutable magnetic result projection, never an HTTP executor.

The API owner supplies a durable receipt AFTER its existing owner/project/job
lookup. This adapter validates every numeric bundle member and all scientific
identities before projecting same-original-row views; no path comes from a URL.
"""

from magnetic_result_bundle import read_bundle
from magnetic_survey_json import keys, fail
from magnetic_local_paths import external_path


def project_result(bundle_path, receipt):
    keys(receipt, 'job_id dataset_id source_id generation_sha256 configuration_sha256 original_sha256', '$/owner-receipt')
    for key in ('job_id', 'dataset_id'):
        from uuid import UUID
        if type(receipt[key]) is not str or str(UUID(receipt[key])) != receipt[key]:
            fail('hash', '$/owner-receipt', 'Canonical durable owner job/dataset identity required')
    imported = read_bundle(external_path(bundle_path))
    result, request = imported['result'], imported['request']
    checks = dict(source_id=request['source']['id'], generation_sha256=imported['generation_sha256'],
        configuration_sha256=result['identity']['configuration_sha256'], original_sha256=request['source']['original_sha256'])
    if any(receipt[key] != value for key, value in checks.items()):
        fail('hash', '$/owner-receipt', 'Owner job/source/configuration/generation binding mismatch')
    c = len(result['prediction']['components'])
    observed = request['observations']['values']['data']
    p, r = result['prediction']['values_nT']['data'], result['prediction']['residual_nT']['data']
    rows = result['prediction']['rows']['data']
    offsets = {row: k*c for k, row in enumerate(rows)}
    xyz = result['inventory']['receivers_m']['data']
    original = []
    outer = set(result['partition']['outer_rows']['data'])
    for i, row_id in enumerate(result['inventory']['row_ids']):
        k = offsets.get(i)
        original.append(dict(row=i, row_id=row_id, group_id=result['inventory']['group_ids'][i],
            xyz_m=xyz[3*i:3*i+3], usable=result['inventory']['usable']['data'][i],
            qc_reason=result['inventory']['qc_reason'][i], role='outer' if i in outer else 'development',
            observed_nT=observed[c*i:c*i+c], predicted_nT=None if k is None else p[k:k+c],
            residual_nT=None if k is None else r[k:k+c]))
    return dict(schema='magnetic-owner-result-view-1', binding=receipt.copy(),
        lane='local_replay', online_admitted=False, claims=result['claims'],
        quantity=result['prediction']['quantity'], components=result['prediction']['components'],
        coordinate_frame=request['frame'], original=request['source'],
        rows=original, mesh=request['geometry']['mesh'], model=result['model'], selected=result['selected'],
        candidates=result['candidates'], metrics=result['metrics'], history=result['history'],
        diagnostics=result['diagnostics'], sensitivity=None,
        sensitivity_reason='Not exported by this immutable generation; no display recomputation or invented zero',
        resolution_interpretation='Local fixed-objective free-face point-spread; not posterior geological uncertainty')
