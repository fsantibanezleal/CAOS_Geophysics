"""Bounded native transport and external-only local gravity workflow.

No raw-source adjudication, prepared engines, archive extraction or service
activation. All imported objects undergo native admission and physics replay.
"""
from __future__ import annotations

import argparse
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import re
import struct
import tempfile
import zipfile

import numpy as np

import gravity_irls as irls
import gravity_l2 as l2
import gravity_survey_l2 as survey

MAX_FILE = 264 * 1024**2
MAX_MANIFEST = 4 * 1024**2
MAX_MEMBERS = 4096
DTYPES = {'<f8': np.dtype('float64'), '<i8': np.dtype('int64'), '|b1': np.dtype('bool')}


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result: raise ValueError('archive: duplicate JSON key')
        result[key] = value
    return result


def _json(raw):
    def denied(value): raise ValueError('archive: nonfinite JSON')
    def integer(value):
        if len(value) > 21: raise ValueError('archive: integer cap')
        result = int(value)
        if result.bit_length() > 64: raise ValueError('archive: integer cap')
        return result
    return json.loads(raw, object_pairs_hook=_pairs, parse_constant=denied, parse_int=integer)


def archive_bytes(value):
    """Encode only exact native types after the unchanged whole-wrapper guard."""
    l2._result_native_metadata(value)
    survey._finite(value)
    members = {}
    def encode(item):
        kind = type(item)
        if kind is np.ndarray:
            name = f'a{len(members):04d}.bin'
            raw = item.tobytes(order='C')
            members[name] = raw
            return {'array': name, 'dtype': {'f':'<f8','i':'<i8','b':'|b1'}[item.dtype.kind],
                    'shape': list(item.shape), 'sha256': sha256(raw).hexdigest()}
        if kind is dict: return {'dict': [[key, encode(child)] for key, child in item.items()]}
        if kind is tuple: return {'tuple': [encode(child) for child in item]}
        return item
    manifest = {'schema':'gravity-native-archive-1', 'value':encode(value)}
    raw = json.dumps(manifest, ensure_ascii=False, allow_nan=False, separators=(',',':')).encode('utf-8')
    if len(raw) > MAX_MANIFEST or len(members)+1 > MAX_MEMBERS: raise ValueError('archive: transport cap')
    out = io.BytesIO()
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
        archive.writestr('manifest.json', raw)
        for name, raw in members.items(): archive.writestr(name, raw)
    result = out.getvalue()
    if len(result) > MAX_FILE: raise ValueError('archive: file cap')
    return result


def native_from_archive(raw):
    """Complete stored ZIP barrier before decoding; never returns partial data."""
    if type(raw) is not bytes or not 22 <= len(raw) <= MAX_FILE: raise ValueError('archive: byte/file cap')
    # No comments, appended bytes, ZIP64, split disks or hidden prefixes.
    end = struct.unpack('<4s4H2IH', raw[-22:])
    signature, disk, cd_disk, count_disk, count, cd_size, cd_offset, comment = end
    if (signature != b'PK\x05\x06' or disk or cd_disk or comment or count_disk != count
            or not 1 <= count <= MAX_MEMBERS or cd_offset+cd_size != len(raw)-22):
        raise ValueError('archive: exact EOF and bounded central directory')
    payloads = {}
    total = 0
    with zipfile.ZipFile(io.BytesIO(raw), 'r') as archive:
        infos = archive.infolist()
        if len(infos) != count: raise ValueError('archive: directory count')
        offset = 0
        for info in infos:
            name = info.filename
            if (name in payloads or (name != 'manifest.json' and re.fullmatch(r'a[0-9]{4}\.bin', name) is None)
                    or info.compress_type != zipfile.ZIP_STORED or info.flag_bits or info.extra or info.comment
                    or info.file_size != info.compress_size or info.header_offset != offset
                    or info.external_attr >> 16 & 0o170000 == 0o120000):
                raise ValueError('archive: member identity/type/layout')
            header = struct.unpack('<4s5H3I2H', raw[offset:offset+30])
            if (header[0] != b'PK\x03\x04' or header[2] or header[3] or header[-1]
                    or header[6] != info.CRC or header[7] != info.file_size or header[8] != info.file_size):
                raise ValueError('archive: exact local header')
            local_name = raw[offset+30:offset+30+header[-2]]
            if local_name != name.encode('ascii'): raise ValueError('archive: local name mismatch')
            limit = MAX_MANIFEST if name == 'manifest.json' else 256*1024**2
            if info.file_size > limit: raise ValueError('archive: member cap')
            total += info.file_size
            if total > 256*1024**2+MAX_MANIFEST: raise ValueError('archive: aggregate byte cap')
            offset += 30+len(local_name)+info.file_size
            if offset > cd_offset: raise ValueError('archive: overlapping member')
            payloads[name] = archive.read(info)  # CRC verified before native decoding.
        if offset != cd_offset or 'manifest.json' not in payloads: raise ValueError('archive: complete member barrier')
    manifest = _json(payloads.pop('manifest.json'))
    survey._keys(manifest, ('schema','value'), 'archive manifest')
    survey._enum(manifest['schema'], 'gravity-native-archive-1', 'archive schema')
    used = set()
    budget = [0,0]
    def decode(item, depth=0):
        budget[0] += 1
        if depth > 8 or budget[0] > 65536: raise ValueError('archive: native depth/node cap')
        kind = type(item)
        if kind is dict:
            if set(item) == {'dict'}:
                pairs = item['dict']
                if type(pairs) is not list or len(pairs) > 32768: raise ValueError('archive: dictionary cap')
                result = {}
                for pair in pairs:
                    if type(pair) is not list or len(pair) != 2 or type(pair[0]) is not str or pair[0] in result:
                        raise ValueError('archive: native dictionary keys')
                    result[pair[0]] = decode(pair[1], depth+1)
                return result
            if set(item) == {'tuple'}:
                if type(item['tuple']) is not list or len(item['tuple']) > 32768: raise ValueError('archive: tuple cap')
                return tuple(decode(child, depth+1) for child in item['tuple'])
            survey._keys(item, ('array','dtype','shape','sha256'), 'array descriptor')
            name, dtype, shape = item['array'], item['dtype'], item['shape']
            survey._enum(dtype, DTYPES, 'native dtype')
            survey._sha(item['sha256'], 'array hash')
            if type(name) is not str or name not in payloads or name in used: raise ValueError('archive: distinct array member')
            if type(shape) is not list or len(shape) not in (1,2) or any(type(n) is not int or not 0 <= n <= 4096 for n in shape):
                raise ValueError('archive: native array shape')
            expected = DTYPES[dtype].itemsize
            for n in shape: expected *= n
            data = payloads[name]
            budget[1] += expected
            if expected != len(data) or budget[1] > 256*1024**2 or sha256(data).hexdigest() != item['sha256']:
                raise ValueError('archive: native array byte/hash binding')
            if dtype == '|b1' and any(v not in (0,1) for v in data): raise ValueError('archive: canonical bool bytes')
            used.add(name)
            # Immutable byte-backed views: no numeric copy before the complete
            # logical-occurrence native metadata/array guard below.
            array = np.frombuffer(data, dtype=DTYPES[dtype]).reshape(shape)
            array.setflags(write=False)
            return array
        if kind not in (str,int,float,bool,type(None)): raise TypeError('archive: exact native scalar')
        if kind is str and len(item) > 1024: raise ValueError('archive: text cap')
        if kind is float and not np.isfinite(item): raise ValueError('archive: finite scalar')
        return item
    result = decode(manifest['value'])
    if used != set(payloads): raise ValueError('archive: unreferenced member')
    l2._result_native_metadata(result)
    survey._finite(result)
    return result


def external_root(value, env):
    """Explicit device root only, with no repository or reparse ancestors."""
    chosen = value if value is not None else os.environ.get(env)
    if not chosen: raise ValueError(env+': explicit absolute external root required')
    root = Path(chosen)
    if not root.is_absolute(): raise ValueError('root: absolute path required')
    for ancestor in (root,*root.parents):
        if ancestor.is_symlink() or (hasattr(ancestor,'is_junction') and ancestor.is_junction()):
            raise ValueError('root: reparse/symlink ancestor forbidden')
        if (ancestor/'.git').exists(): raise ValueError('root: repository storage forbidden')
    root = root.resolve()
    if root == Path(root.anchor): raise ValueError('root: device root is too broad')
    root.mkdir(parents=True, exist_ok=True)
    if not root.is_dir(): raise ValueError('root: directory required')
    return root


def _target(root, name):
    if type(name) is not str or re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,95}\.gza',name) is None:
        raise ValueError('archive: flat .gza name required')
    target = root/name
    if target.is_symlink() or (hasattr(target,'is_junction') and target.is_junction()): raise ValueError('archive: link forbidden')
    return target


def read_archive(root, name):
    root=external_root(root,'GEOPHYSICS_LOCAL_DATA_ROOT')
    target = _target(root,name)
    with target.open('rb') as stream: raw = stream.read(MAX_FILE+1)
    return native_from_archive(raw)


def publish_archive(root, temp_root, name, value):
    """Atomic no-replace publication; temp and destination must share a volume."""
    root = external_root(root,'GEOPHYSICS_LOCAL_DATA_ROOT')
    temp_root = external_root(temp_root,'GEOPHYSICS_LOCAL_TEMP_ROOT')
    target = _target(root,name)
    if target.exists(): raise FileExistsError(target)
    raw = archive_bytes(value)
    # Validate exactly what is being published, before any durable target exists.
    native_from_archive(raw)
    with tempfile.TemporaryDirectory(prefix='gravity-',dir=temp_root) as temporary:
        staged = Path(temporary)/'result.gza'
        with staged.open('xb') as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(staged,target)  # Atomic failure if target exists; never os.replace.
    return target


def _close(actual, expected, field):
    if not np.allclose(actual,expected,rtol=1e-10,atol=1e-12): raise ValueError('L2 replay: '+field)


def replay_l2_fit(solve, admitted, rows, beta):
    """Native single-fit replay shared by calibration and conditional refits."""
    plan,prior = admitted['plan'],admitted['prior']
    req,observed = plan['request'],admitted['observations']['gz_up_mgal']
    noise = {k:admitted['noise'][k] for k in ('kind','values')}
    l2._validate_solve_state(solve,rows)
    problem = l2._build_problem(req,observed,noise,prior,rows,beta,observation_rows=plan['development_rows'])
    trace = solve['trace']
    models = trace['models_kg_m3']/1000.
    if not len(models): return
    if not np.array_equal(trace['models_kg_m3'][0],prior['start_kg_m3']): raise ValueError('L2 replay: unchanged start')
    lower,upper = prior['lower_kg_m3']/1000.,prior['upper_kg_m3']/1000.
    if np.any(models<lower) or np.any(models>upper): raise ValueError('L2 replay: model box')
    norm = None
    for index,q in enumerate(models):
        pd,pm = float(problem['misfit'](q)),float(problem['regularization'](q))
        gradient = problem['misfit'].deriv(q)+problem['beta_engine']*problem['regularization'].deriv(q)
        if norm is None: norm = max(1.,float(np.linalg.norm(gradient,ord=np.inf)))
        absolute = float(np.linalg.norm(l2._kkt_gradient(q,gradient,lower,upper),ord=np.inf))
        _close([pd,pm,pd+problem['beta_engine']*pm,absolute/norm],
            [trace[k][index] for k in ('phi_d','phi_m','phi_engine','kkt_normalized')],'actual native metrics')
    if solve['reason']=='absolute_stationary' and absolute>1e-12:
        raise ValueError('L2 replay: absolute native stop unavailable after physical conversion')
    prediction = problem['simulation'].dpred(models[-1])+problem['background']
    if solve['predicted_mgal'] is not None:
        _close(prediction,solve['predicted_mgal'],'physical prediction')
        _close(observed[np.searchsorted(plan['development_rows'],rows)]-prediction,
            solve['residual_observed_minus_predicted_mgal'],'physical residual')


def validate_l2(result, request):
    """Every fit and selection replay, including unsuccessful original records."""
    l2._result_native_metadata({'result':result,'request':request})
    l2._calibration_result_metadata(result)
    admitted = l2._admit_calibration(request)
    survey._finite(result)
    if survey._digest({k:v for k,v in result.items() if k!='result_sha256'}) != result['result_sha256']:
        raise ValueError('L2 replay: content hash')
    plan, prior = admitted['plan'], admitted['prior']
    if survey._digest(plan) != survey._digest(result['plan']): raise ValueError('L2 replay: original plan')
    provenance = {'source':plan['request']['source'],'plan_sha256':plan['plan_sha256'],
        'normalized_values_sha256':admitted['observations']['values_sha256'],'noise_sha256':admitted['noise']['values_sha256'],
        'prior_sha256':survey._digest(prior),'policy_sha256':survey._digest(admitted['policy']),
        'forward_source_sha256':l2.FORWARD_SOURCE,'runtime_epoch':l2.RUNTIME_EPOCH,'runtime_versions':l2.forward._runtime(),
        'source_verification':'external_required_not_performed_by_solver'}
    if result['provenance'] != provenance: raise ValueError('L2 replay: original declarations')
    req, observed = plan['request'], admitted['observations']['gz_up_mgal']
    noise = {k:admitted['noise'][k] for k in ('kind','values')}
    for candidate in result['candidates']:
        for j, fold in enumerate(candidate['folds']):
            expected = plan['folds'][j]
            replay_l2_fit(fold['solve'],admitted,expected['fit_rows'],candidate['beta_candidate'])
            if not np.array_equal(fold['validation_rows'],expected['validation_rows']): raise ValueError('L2 replay: validation rows')
            scores = [fold[k] for k in ('validation_phi_d','validation_wrms','validation_rmse_mgal')]
            if any(v is not None for v in scores):
                if fold['solve']['status']!='converged' or any(v is None for v in scores): raise ValueError('L2 replay: partial score')
                prediction = l2._physical_prediction(req,fold['solve']['model_kg_m3'])
                positions = np.searchsorted(plan['development_rows'],fold['validation_rows'])
                _close(l2._marginal_metrics(prediction[fold['validation_rows']],observed[positions],noise,positions)[:3],scores,'marginal score')
        valid = all(f['solve']['status']=='converged' for f in candidate['folds'])
        eligible = valid and all(f['validation_phi_d'] is not None for f in candidate['folds'])
        score = float(sum(f['validation_phi_d'] for f in candidate['folds'])/sum(len(f['validation_rows']) for f in candidate['folds'])) if eligible else None
        reason = 'eligible' if eligible else 'invalid_score' if valid else 'fold_failure'
        if (candidate['eligible'],candidate['score_q'],candidate['reason'])!=(eligible,score,reason): raise ValueError('L2 replay: eligibility')
    selected = l2._selected_index(result['candidates'])
    if result['selected_index']!=selected: raise ValueError('L2 replay: fixed selection')
    final = result['final_solve']
    if selected is None:
        if final is not None or result['selection_status']!='insufficient_candidates' or result['predictions']['gz_up_mgal'] is not None:
            raise ValueError('L2 replay: unavailable selection')
    else:
        if final is None: raise ValueError('L2 replay: missing refit')
        replay_l2_fit(final,admitted,plan['development_rows'],l2.BETA_CANDIDATES[selected])
        status = 'selected' if final['status']=='converged' else 'final_nonconverged'
        if status!=result['selection_status']: raise ValueError('L2 replay: refit status')
        if result['predictions']['gz_up_mgal'] is not None:
            _close(l2._physical_prediction(req,final['model_kg_m3']),result['predictions']['gz_up_mgal'],'full prediction')
        elif status=='selected': raise ValueError('L2 replay: missing full prediction')
    if not np.array_equal(result['predictions']['rows'],np.arange(len(req['background_mgal']),dtype=np.int64)):
        raise ValueError('L2 replay: original prediction rows')
    diagnostics = l2._fit_diagnostics(req,noise,observed,prior,plan)
    warnings = list(diagnostics['warnings'])
    if admitted['noise']['basis']=='explicit_conditional_gaussian': warnings.append('error_assumed_conditional')
    warnings.append('geometry_uncertainty_not_propagated')
    if admitted['noise']['cross_partition_dependence']=='possible_not_removed': warnings.append('cross_partition_dependence')
    diagnostics['warnings'] = tuple(warnings)
    for key, value in diagnostics.items():
        if type(value) is np.ndarray: _close(value,result['diagnostics'][key],'diagnostics')
        elif value!=result['diagnostics'][key]: raise ValueError('L2 replay: diagnostic identity')
    return result


def verify_calibration(value):
    survey._keys(value,('schema','request','result'),'calibration archive')
    survey._enum(value['schema'],'gravity-calibration-archive-1','calibration archive schema')
    schema = value['result'].get('schema') if type(value['result']) is dict else None
    if schema == 'gravity-survey-l2-calibration-result-1': validate_l2(value['result'],value['request'])
    elif schema == 'gravity-survey-irls-calibration-result-3': irls.validate_gravity_irls(value['result'],value['request'])
    elif schema == 'gravity-survey-irls-corrected-calibration-result-1':
        from gravity_irls_corrected_workflow import validate
        validate(value['result'], value['request'])
    elif schema == 'gravity-survey-irls-original-calibration-result-1':
        from gravity_irls_original import validate
        validate(value['result'], value['request'])
    else: raise ValueError('archive: unsupported calibration method')
    return value


def evaluate(value):
    schema = value.get('schema') if type(value) is dict else None
    if schema == 'gravity-survey-l2-evaluation-request-2':
        survey._keys(value,('schema','frozen_calibration','calibration_request','observations','noise'),'L2 evaluation archive')
        validate_l2(value['frozen_calibration'],value['calibration_request'])
        native = {k:v for k,v in value.items() if k!='calibration_request'}
        native['schema']='gravity-survey-l2-evaluation-request-1'
        return l2.evaluate_gravity_l2(native)
    if schema == 'gravity-survey-irls-evaluation-request-3': return irls.evaluate_gravity_irls(value)
    if schema == 'gravity-survey-irls-corrected-evaluation-request-1':
        from gravity_irls_corrected_workflow import evaluate as corrected_evaluate
        return corrected_evaluate(value)
    if schema == 'gravity-survey-irls-original-evaluation-request-1':
        from gravity_irls_original import evaluate as original_evaluate
        return original_evaluate(value)
    raise ValueError('archive: complete original calibration request required for evaluation')


def verify_evaluation(value):
    survey._keys(value,('schema','evaluation_schema','frozen_calibration','calibration_request','observations','noise','result'),'evaluation archive')
    survey._enum(value['schema'],'gravity-evaluation-archive-1','evaluation archive schema')
    request = {k:v for k,v in value.items() if k not in ('schema','evaluation_schema','result')}
    request['schema']=value['evaluation_schema']
    expected=evaluate(request)
    if survey._digest(expected)!=survey._digest(value['result']): raise ValueError('archive: actual frozen evaluation replay')
    return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('calibrate','verify','evaluate','refit'))
    parser.add_argument('--data-root')
    parser.add_argument('--temp-root')
    parser.add_argument('--input',required=True)
    parser.add_argument('--output')
    parser.add_argument('--calibration',help='original frozen calibration archive for verifying noise refits')
    args = parser.parse_args(argv)
    root = external_root(args.data_root,'GEOPHYSICS_LOCAL_DATA_ROOT')
    temp_root = external_root(args.temp_root,'GEOPHYSICS_LOCAL_TEMP_ROOT')
    value = read_archive(root,args.input)
    if args.command == 'verify':
        if value.get('schema')=='gravity-noise-refits-result-1':
            if not args.calibration: parser.error('--calibration required for noise-refit verification')
            from gravity_noise_refits import validate_noise_refits
            original=verify_calibration(read_archive(root,args.calibration))
            validate_noise_refits(value,original['request'],original['result'])
            print(json.dumps({'transport_replay':'passed','actual_refits':32,'field_eligible':False,'full_M02_accepted':False}))
            return 0
        if value.get('schema')=='gravity-evaluation-archive-1': verify_evaluation(value)
        else: verify_calibration(value)
        print(json.dumps({'transport_replay':'passed','selection_status':value['result'].get('selection_status'),
                          'field_eligible':False,'full_M02_accepted':False}))
        return 0
    if not args.output: parser.error('--output required for calibrate/evaluate')
    if _target(root,args.output).exists(): raise FileExistsError(args.output)
    if args.command == 'refit':
        from gravity_noise_refits import refit_gravity_noise, validate_noise_refits
        original=verify_calibration(value)
        result=refit_gravity_noise(original['request'],original['result'])
        validate_noise_refits(result,original['request'],original['result'])
        output=result
        code=0 if np.all(result['successful']) else 2
    elif args.command == 'calibrate':
        schema = value.get('schema') if type(value) is dict else None
        if schema == 'gravity-survey-l2-calibration-request-1': result = l2.calibrate_gravity_l2(value)
        elif schema == 'gravity-survey-irls-calibration-request-1': result = irls.calibrate_gravity_irls(value)
        elif schema == 'gravity-survey-irls-corrected-calibration-request-1':
            from gravity_irls_corrected_workflow import calibrate
            result = calibrate(value)
        elif schema == 'gravity-survey-irls-original-calibration-request-1':
            from gravity_irls_original import calibrate
            result = calibrate(value)
        else: raise ValueError('archive: unsupported calibration request')
        output = {'schema':'gravity-calibration-archive-1','request':value,'result':result}
        verify_calibration(output)
        code = 0 if result['selection_status']=='selected' else 2
    else:
        result = evaluate(value)
        # Lossless flattening: adding another request wrapper would violate
        # the unchanged depth8 guard for L2's original nested fold traces.
        output = {k:v for k,v in value.items() if k!='schema'}
        output.update(schema='gravity-evaluation-archive-1',evaluation_schema=value['schema'],result=result)
        verify_evaluation(output)
        code = 0
    target = publish_archive(root,temp_root,args.output,output)
    print(json.dumps({'archive':str(target),'result_sha256':result['result_sha256'],
                      'field_eligible':False,'full_M02_accepted':False}))
    return code


if __name__ == '__main__': raise SystemExit(main())
