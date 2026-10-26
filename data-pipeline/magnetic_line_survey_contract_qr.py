"""Strict separate QR epoch; original /1 and /2 contracts remain untouched."""
from copy import deepcopy

import magnetic_line_contract as base
import magnetic_line_survey as core
import magnetic_line_survey_contract_v2 as original
import magnetic_line_survey_qr as engine

E,L,I,literal=base.E,base.L,base.I,base.literal
POLICY_EPOCH='augmented_direct_qr_v3'
POLICY=dict(schema='m03-qr-policy/1',engine='DGELS_DTRTRI',epoch=engine.EPOCH,
    objective='original_weighted_Tikhonov_no_intercept',stationarity_relative_max=1e-9,
    condition_upper_bound_max=1e8,thread_limit=1,mandatory_fit_count=97,maximum_fit_count=98)
QR_TABLES=dict(candidate_fit_qr_v3='CandidateFit',qr_solve_identity='SolveIdentity')
SCHEMAS=deepcopy(original.SCHEMAS)
SCHEMAS.update({
    'QRPolicy':{key:literal(value) for key,value in POLICY.items()},
    'OriginalDiagnostics':dict(data_term='Nonneg',regularization_term='Nonneg',objective='Nonneg',
        gradient_denominator='Nonneg',stationarity_inf='Nonneg',stationarity_relative='Nonneg',coefficient_error_bound_nT='Nonneg'),
    'DenseCapacity':dict(rows=I(1,8000000),sources=I(1,65536),augmented_rows=I(2,8065536),lwork=I(1,2**31-1),
        augmented_matrix_bytes=I(1,core.RSS_LIMIT),triangular_matrix_bytes=I(1,core.RSS_LIMIT),
        extra_peak_bytes=I(1,core.RSS_LIMIT),factorization_work_bound=I(1,10**12),
        augmented_buffer_slots=literal(4),triangular_buffer_slots=literal(4)),
    'BLASIdentity':dict(library=E('numpy.libs','scipy.libs'),prefix=literal('libscipy_openblas'),sha256='Hash',threads=literal(1)),
    'EngineIdentity':dict(numpy=literal('2.2.6'),scipy=literal('1.15.2'),flapack_sha256=literal(engine.FLAPACK_SHA),
        blas=L('BLASIdentity',2,2),threads=literal(1)),
    'QRSolve':dict(schema=literal('m03-qr-solve/1'),epoch=literal(engine.EPOCH),rows=I(1,8000000),sources=I(1,65536),
        augmented_rows=I(2,8065536),damping='Pos',preconditioner_sha256='Hash',column_scales_sha256='Hash',
        coefficients_sha256='Hash',scaled_coefficients_sha256='Hash',lapack_info=literal(0),triangular_inverse_info=literal(0),
        lwork=I(1,2**31-1),condition_domain=literal(engine.CONDITION_DOMAIN),condition_upper_bound='Pos',
        triangular_diagonal_min_abs='Pos',triangular_diagonal_max_abs='Pos',original_diagnostics='OriginalDiagnostics',
        dense_capacity='DenseCapacity',engine_identity='EngineIdentity',numerical_verdict=literal('component_pass')),
    'CandidateFit':dict(original.SCHEMAS['CandidateFit'],solve='QRSolve'),
    'SolveIdentity':dict(sequence=I(0,96),source_geometry_index=I(0,3),fold_id='ID',depth_m='Pos',damping='Pos',solve='QRSolve'),
    'TableRef':dict(original.SCHEMAS['TableRef'],row_schema=E(*original.TABLE_NAMES,*QR_TABLES)),
    'TableManifest':dict(original.SCHEMAS['TableManifest'],schema=literal('magnetic-line-table-manifest/3'),row_schema=E(*QR_TABLES)),
    'FitReceipt':dict(original.SCHEMAS['FitReceipt'],solver='QRPolicy',legacy_request_solver='SolverPolicy',
        solve='QRSolve',solve_identities='TableRef',scaled_coefficients='FileIdentity',fit_count=literal(97)),
    'SurveyResult':dict(original.SCHEMAS['SurveyResult'],schema=literal('magnetic-line-survey-result/3'),
        policy_epoch=literal(POLICY_EPOCH),geometry='GeometrySeal',fit='FitReceipt',execution='FileIdentity'),
})


def typed(value,spec,parent=None):
    if type(spec) is str and spec.startswith('?'):
        return None if value is None else typed(value,spec[1:],parent)
    if type(spec) is str and spec in SCHEMAS:return validate(spec,value)
    if type(spec) is tuple and spec[0]=='list':
        if type(value) is not list or not spec[2]<=len(value)<=spec[3]:raise core.SurveyError('invalid_contract','ingest')
        return [typed(item,spec[1]) for item in value]
    return original.typed(value,spec,parent)


def validate(name,value):
    # Original documents and their nested policy still have the original parser.
    if name in ('SurveyInput','SurveyRequest'):return original.validate(name,value)
    try:
        table=SCHEMAS[name]
        if type(value) is not dict or set(value)!=set(table):raise core.SurveyError('invalid_contract','ingest')
        result={key:typed(value[key],spec,value) for key,spec in table.items()}
        conditions(name,result)
        return result
    except core.SurveyError:raise
    except (base.MagneticContractError,KeyError,TypeError,ValueError,OverflowError):
        raise core.SurveyError('invalid_contract','ingest') from None


def conditions(name,v):
    def check(condition):
        if not condition:raise core.SurveyError('invalid_contract','ingest')
    if name in ('QRPolicy','BLASIdentity'):return
    if name=='EngineIdentity':
        check([item['library'] for item in v['blas']]==['numpy.libs','scipy.libs'])
        check(all(item['sha256']==engine.DLL_PINS[item['library']] for item in v['blas']))
        return
    if name=='DenseCapacity':
        check(v==engine.dense_capacity(v['rows'],v['sources'],lwork=v['lwork']))
        return
    if name=='OriginalDiagnostics':
        check(v['objective']==v['data_term']+v['regularization_term'])
        relative=v['stationarity_inf']/v['gradient_denominator'] if v['gradient_denominator'] else 0.
        check((v['gradient_denominator']>0 or v['stationarity_inf']==0) and v['stationarity_relative']==relative)
        check(v['stationarity_relative']<=1e-9)
        return
    if name=='QRSolve':
        check(v['augmented_rows']==v['rows']+v['sources'])
        check(all(v[key]==v['dense_capacity'][key] for key in ('rows','sources','augmented_rows','lwork')))
        check(v['condition_upper_bound']<1e8 and v['triangular_diagonal_min_abs']<=v['triangular_diagonal_max_abs'])
        return
    if name in ('CandidateFit','SolveIdentity'):
        check(v['damping']==v['solve']['damping'])
        if name=='CandidateFit':
            check(v['rmse_nT'] is not None and v['scored']>0 and v['verdict']==dict(overall='pass',
                gates=[dict(gate_id='solve',verdict='pass',evidence_sha256=base.digest(v['solve']),reason=None)],
                numerical_success=True,reasons=[]))
        return
    if name in ('TableRef','TableManifest') and v['row_schema'] in QR_TABLES:
        check(v['rows']==(96 if v['row_schema']=='candidate_fit_qr_v3' else 97) and len(v['table_id'])<=32)
        if name=='TableRef':check(v['manifest']['name']=='table-'+v['table_id']+'.json')
        return
    if name=='FitReceipt':
        check(v['candidates']['row_schema']=='candidate_fit_qr_v3' and v['solve_identities']['row_schema']=='qr_solve_identity')
        check(v['selected_damping']==v['solve']['damping'] and v['sources']['shape'][0]==v['solve']['sources'])
        return
    if name=='SurveyResult':return
    original.conditions(name,v)
