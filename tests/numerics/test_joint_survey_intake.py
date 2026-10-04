"""Original-byte development intake; no solve, sealed values or field claim."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

import joint_survey_intake as intake
import joint_survey_plan as planner
from test_joint_survey_plan import request


PATHS = {
    'mesh_origin':('mesh','origin_m'), 'mesh_hx':('mesh','hx_m'),
    'mesh_hy':('mesh','hy_m'), 'mesh_hz':('mesh','hz_m'),
    'mesh_active':('mesh','active'), 'prior_lengths':('prior','lengths_m'),
}
for modality in ('gravity','magnetic'):
    for key in ('receivers','mask','groups','partition'):
        PATHS[modality+'_'+key]=(modality,key+'_m' if key=='receivers' else key)
for label,prop in (('density','density'),('susceptibility','susceptibility')):
    for key in ('lower','upper','start','reference'):
        PATHS[label+'_'+key]=('prior',prop,key)


def sha(value):
    return hashlib.sha256(value).hexdigest()


def write_request(directory, doc):
    (directory/'request.json').write_bytes(json.dumps(
        doc,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode('utf-8'))


def fixture(directory, covariance=False, provided=False):
    req=request()
    raw={m:(m+' original unmodified observations').encode() for m in ('gravity','magnetic')}
    correction=b'{"schema":"authored-correction-receipt","field":false}'
    for m in raw:
        req[m]['source'].update(raw_sha256=sha(raw[m]),raw_bytes=len(raw[m]),
                                correction_sha256=sha(correction))
        if covariance:
            req[m]['noise'].update(kind='full_covariance',unit=req[m]['unit']+'^2',
                                   cross_partition='possible_not_removed')
    plan=planner.plan_joint_survey(req)
    dev={'plan_sha256':plan['plan_sha256']}
    arrays={}
    survey=deepcopy(req)
    for identifier,path in PATHS.items():
        node=survey
        for key in path[:-1]: node=node[key]
        arrays[identifier]=node[path[-1]]
        node[path[-1]]={'array':identifier}
    survey['frame']['axes']=list(survey['frame']['axes'])
    manifest={}
    access={}
    for m in raw:
        survey[m]['missing_reasons']=list(survey[m]['missing_reasons'])
        rows=np.r_[plan[m]['training_rows'],plan[m]['validation_rows']]
        observed=np.array([.01,-.02,.03,.04])
        noise=(.65*np.eye(4)+.35*np.ones((4,4))) if covariance else np.ones(4)
        d={'rows':rows,'observed':observed,'noise_values':noise}
        d['observations_sha256']=planner._digest({'rows':rows,'observed':observed,
            'unit':req[m]['unit'],'plan_sha256':plan['plan_sha256']})
        d['noise_sha256']=planner._digest({'rows':rows,'noise_values':noise,
            'unit':req[m]['noise']['unit'],'kind':req[m]['noise']['kind'],
            'plan_sha256':plan['plan_sha256']})
        for key,label in (('rows','rows'),('observed','observed'),('noise_values','noise')):
            identifier=m+'_development_'+label
            arrays[identifier]=d[key]
            d[key]={'array':identifier}
        dev[m]=d
        manifest[m]={'rows_sha256':sha(plan[m]['sealed_rows'].tobytes()),
            'observations_file_sha256':'d'*64,'noise_file_sha256':'e'*64,
            'count':len(plan[m]['sealed_rows']),'noise_kind':req[m]['noise']['kind']}
        access[m]={'availability':'provided' if provided else 'provider_reference_only',
                   'raw_present':provided,'correction_present':provided}
        if provided:
            (directory/(m+'.raw')).write_bytes(raw[m])
            (directory/(m+'.corrections.json')).write_bytes(correction)
    descriptors={}
    for identifier,value in arrays.items():
        file=directory/(identifier+'.npy')
        with file.open('xb') as stream:
            np.lib.format.write_array(stream,value,version=(1,0),allow_pickle=False)
        descriptors[identifier]={'dtype':value.dtype.str,'shape':list(value.shape),
            'file_bytes':file.stat().st_size,'file_sha256':sha(file.read_bytes()),
            'data_sha256':sha(value.tobytes(order='C'))}
    doc={'schema':'joint-survey-intake-1','survey':survey,'development':dev,
         'arrays':descriptors,'sealed_manifest':{'schema':'joint-survey-sealed-manifest-1',**manifest},
         'raw_access':access}
    write_request(directory,doc)
    return doc,req


@pytest.mark.parametrize('covariance',[False,True])
@pytest.mark.parametrize('provided',[False,True])
def test_original_bytes_and_native_admission(tmp_path,covariance,provided):
    doc,req=fixture(tmp_path,covariance,provided)
    before={p.name:sha(p.read_bytes()) for p in tmp_path.iterdir()}
    result=intake.load_joint_development(str(tmp_path))
    assert set(result)=={'schema','survey_request','plan','development','sealed_manifest','bindings','diagnostics'}
    assert result['schema']=='joint-survey-development-intake-1'
    assert result['plan']['plan_sha256']==planner.plan_joint_survey(req)['plan_sha256']
    assert result['diagnostics']['source_bytes_verified']==dict.fromkeys(('gravity','magnetic'),provided)
    assert result['diagnostics']['correction_bytes_verified']==dict.fromkeys(('gravity','magnetic'),provided)
    for key in ('field_eligible','inverse_completed','rights_verified','sealed_values_loaded',
                'correction_science_verified','concurrent_snapshot_guaranteed'):
        assert result['diagnostics'][key] is False
    for array in planner._arrays(result['survey_request'])+planner._arrays(result['development']):
        assert array.flags.owndata and array.flags.c_contiguous and not array.flags.writeable
    assert before=={p.name:sha(p.read_bytes()) for p in tmp_path.iterdir()}
    assert result['bindings']['request_file_sha256']==before['request.json']
    assert len(doc['arrays'])==28


@pytest.mark.parametrize('bad',['root_extra','unknown_id','alias','wrong_dtype','wrong_rank',
    'axis65','receivers2049','active4097','prior_length','covariance_shape','int_scale',
    'sealed_schema','sealed_count','raw_access','injected_kernel','nested_list','bad_sha'])
def test_all_metadata_precedes_value_load_hash_finite_or_engine(tmp_path,bad,monkeypatch):
    doc,_=fixture(tmp_path)
    if bad=='root_extra': doc['engine']='arbitrary'
    elif bad=='unknown_id': doc['arrays']['untrusted_path']=doc['arrays']['mesh_hx']
    elif bad=='alias': doc['survey']['mesh']['hy_m']={'array':'mesh_hx'}
    elif bad=='wrong_dtype': doc['arrays']['mesh_origin']['dtype']='>f8'
    elif bad=='wrong_rank': doc['arrays']['mesh_origin']['shape']=[1,3]
    elif bad=='axis65': doc['arrays']['mesh_hx']['shape']=[65]
    elif bad=='receivers2049': doc['arrays']['gravity_receivers']['shape']=[2049,3]
    elif bad=='active4097': doc['arrays']['mesh_active']['shape']=[4097]
    elif bad=='prior_length': doc['arrays']['density_start']['shape']=[11]
    elif bad=='covariance_shape': doc['arrays']['gravity_development_noise']['shape']=[4,4]
    elif bad=='int_scale': doc['survey']['prior']['density']['scale']=750
    elif bad=='sealed_schema': doc['sealed_manifest']['schema']='another'
    elif bad=='sealed_count': doc['sealed_manifest']['gravity']['count']=True
    elif bad=='raw_access': doc['raw_access']['gravity']['raw_present']=True
    elif bad=='injected_kernel': doc['development']['kernel']='not a callback'
    elif bad=='nested_list': doc['survey']['gravity']['source']['citation']=[[]]*100
    else: doc['arrays']['mesh_hx']['file_sha256']='X'*64
    write_request(tmp_path,doc)
    def prohibited(*args,**kwargs): pytest.fail('metadata admitted before value/hash/engine work')
    monkeypatch.setattr(np,'load',prohibited)
    monkeypatch.setattr(np,'isfinite',prohibited)
    monkeypatch.setattr(intake,'_file_sha',prohibited)
    monkeypatch.setattr(planner.discretize,'TensorMesh',prohibited)
    with pytest.raises((ValueError,TypeError)):
        intake.load_joint_development(str(tmp_path))


@pytest.mark.parametrize('payload',[b'\xef\xbb\xbf{}',b'{"a":1,"a":2}',b'{"a":NaN}',
    b'{"a":Infinity}',b'{"a":1e999}',b'\xff',b'['*30+b']'*30,b' '*262145],
    ids=['bom','duplicate','nan','infinity','overflow','utf8','depth','bytes-plus-one'])
def test_strict_json(tmp_path,payload):
    fixture(tmp_path)
    (tmp_path/'request.json').write_bytes(payload)
    with pytest.raises((ValueError,TypeError,UnicodeError)):
        intake.load_joint_development(str(tmp_path))


@pytest.mark.parametrize('bad',['trailing','truncated','file_hash','data_hash','object',
    'fortran','npy_v2','oversize_header','header_keys'])
def test_npy_and_original_hash_negatives(tmp_path,bad):
    doc,_=fixture(tmp_path)
    file=tmp_path/'mesh_origin.npy'
    if bad=='trailing': file.write_bytes(file.read_bytes()+b'!')
    elif bad=='truncated': file.write_bytes(file.read_bytes()[:-1])
    elif bad=='file_hash': doc['arrays']['mesh_origin']['file_sha256']='f'*64
    elif bad=='data_hash': doc['arrays']['mesh_origin']['data_sha256']='f'*64
    elif bad in ('object','fortran','npy_v2'):
        value=np.array([object(),object(),object()],dtype=object) if bad=='object' else np.zeros(3)
        with file.open('wb') as stream:
            if bad=='fortran':
                np.lib.format.write_array_header_1_0(stream,{'descr':'<f8','fortran_order':True,'shape':(3,)})
                stream.write(value.tobytes())
            else: np.lib.format.write_array(stream,value,version=(2,0) if bad=='npy_v2' else (1,0))
        doc['arrays']['mesh_origin'].update(file_bytes=file.stat().st_size,file_sha256=sha(file.read_bytes()))
    elif bad=='oversize_header': file.write_bytes(b'\x93NUMPY\x01\x00'+(4097).to_bytes(2,'little')+b' '*4097)
    else: file.write_bytes(b'\x93NUMPY\x01\x00'+(12).to_bytes(2,'little')+b'{"evil":1}\n ')
    write_request(tmp_path,doc)
    with pytest.raises((ValueError,TypeError)):
        intake.load_joint_development(str(tmp_path))


@pytest.mark.parametrize('extra',['sealed.npy','truth.npy','Mesh_hx.npy','directory','script.py'])
def test_closed_directory(tmp_path,extra):
    fixture(tmp_path)
    if extra=='directory': (tmp_path/extra).mkdir()
    else: (tmp_path/extra).write_bytes(b'not an input')
    with pytest.raises(ValueError): intake.load_joint_development(str(tmp_path))


def test_sealed_commitment_not_calibration_identity(tmp_path):
    doc,_=fixture(tmp_path)
    original=intake.load_joint_development(str(tmp_path))
    doc['sealed_manifest']['gravity']['observations_file_sha256']='a'*64
    write_request(tmp_path,doc)
    changed=intake.load_joint_development(str(tmp_path))
    assert original['plan']['plan_sha256']==changed['plan']['plan_sha256']
    assert original['bindings']['development_sha256']==changed['bindings']['development_sha256']
    assert original['bindings']['directory_content_sha256']!=changed['bindings']['directory_content_sha256']


@pytest.mark.parametrize('bad',['sealed_hash','sealed_count','rows','noise','observed_nan','raw','correction'])
def test_semantic_hash_and_noise_failures(tmp_path,bad):
    doc,_=fixture(tmp_path,provided=True)
    if bad=='sealed_hash': doc['sealed_manifest']['gravity']['rows_sha256']='a'*64
    elif bad=='sealed_count': doc['sealed_manifest']['gravity']['count']=1
    elif bad in ('rows','noise','observed_nan'):
        identifier={'rows':'gravity_development_rows','noise':'gravity_development_noise',
                    'observed_nan':'gravity_development_observed'}[bad]
        file=tmp_path/(identifier+'.npy')
        value=np.load(file,allow_pickle=False)
        if bad=='rows': value[:]=[0,0,2,3]
        elif bad=='noise': value[0]=-1.
        else: value[0]=np.nan
        with file.open('wb') as stream: np.lib.format.write_array(stream,value,version=(1,0),allow_pickle=False)
        doc['arrays'][identifier].update(file_sha256=sha(file.read_bytes()),data_sha256=sha(value.tobytes()))
    elif bad=='raw': (tmp_path/'gravity.raw').write_bytes(b'X'*doc['survey']['gravity']['source']['raw_bytes'])
    else: (tmp_path/'magnetic.corrections.json').write_bytes(b'{}')
    write_request(tmp_path,doc)
    with pytest.raises((ValueError,TypeError)):
        intake.load_joint_development(str(tmp_path))


def test_post_load_drift(tmp_path,monkeypatch):
    fixture(tmp_path)
    original=np.load
    def drift(file,*args,**kwargs):
        value=original(file,*args,**kwargs)
        path=Path(file.name if hasattr(file,'name') else file)
        if path.name=='mesh_origin.npy': path.write_bytes(path.read_bytes()[:-1]+b'!')
        return value
    monkeypatch.setattr(np,'load',drift)
    with pytest.raises(ValueError,match='drift|hash'):
        intake.load_joint_development(str(tmp_path))


@pytest.mark.parametrize('kind',['child','root'])
def test_actual_symlink_refusal(tmp_path,kind):
    source=tmp_path/'source'; source.mkdir(); fixture(source)
    link=tmp_path/'link'
    try:
        if kind=='root': link.symlink_to(source,target_is_directory=True)
        else:
            file=source/'mesh_origin.npy'; moved=tmp_path/'original.npy'
            file.rename(moved); file.symlink_to(moved)
    except OSError as exc:
        pytest.skip('actual OS cannot create this symlink: '+str(exc))
    with pytest.raises(ValueError,match='link|reparse'):
        intake.load_joint_development(str(link if kind=='root' else source))


@pytest.mark.parametrize('directory',[Path('local'),'', '.', 'https://example.org/survey',123])
def test_directory_exact_local_type(directory):
    with pytest.raises((TypeError,ValueError)):
        intake.load_joint_development(directory)


@pytest.mark.parametrize('bad',['logical96mib','directory256mib','header_injection','late_header',
    'shape_bool','shape_float','filebytes_bool','json_null','unexpected_reference'])
def test_additional_bounded_prevalue_controls(tmp_path,bad,monkeypatch):
    doc,_=fixture(tmp_path)
    if bad=='logical96mib': doc['arrays']['gravity_development_noise']['shape']=[4096,4096]
    elif bad=='shape_bool': doc['arrays']['mesh_hx']['shape']=[True]
    elif bad=='shape_float': doc['arrays']['mesh_hx']['shape']=[3.0]
    elif bad=='filebytes_bool': doc['arrays']['mesh_hx']['file_bytes']=True
    elif bad=='json_null': doc['survey']['frame']['horizontal_datum']=None
    elif bad=='unexpected_reference': doc['survey']['gravity']['source']['citation']={'array':'mesh_hx'}
    elif bad=='header_injection':
        path=tmp_path/'mesh_origin.npy'
        header=b"{'descr':'<f8','fortran_order':False,'shape':__import__('os').system('not executed')}\n"
        path.write_bytes(b'\x93NUMPY\x01\x00'+len(header).to_bytes(2,'little')+header)
        doc['arrays']['mesh_origin']['file_bytes']=path.stat().st_size
    elif bad=='late_header':
        # Last descriptor must reject before FIRST array value/hash work.
        identifier=next(reversed(doc['arrays']))
        path=tmp_path/(identifier+'.npy');path.write_bytes(path.read_bytes()+b'trailing')
        doc['arrays'][identifier]['file_bytes']=path.stat().st_size
    write_request(tmp_path,doc)
    def prohibited(*args,**kwargs): pytest.fail('prevalue guard invoked numerical/value work')
    monkeypatch.setattr(np,'load',prohibited)
    monkeypatch.setattr(np,'isfinite',prohibited)
    monkeypatch.setattr(intake,'_file_sha',prohibited)
    monkeypatch.setattr(planner,'_snapshot',prohibited)
    monkeypatch.setattr(planner.discretize,'TensorMesh',prohibited)
    if bad=='directory256mib':
        real=intake._ordinary
        def oversize(path,directory=False):
            info=real(path,directory)
            if path.name=='request.json':
                values=list(info);values[6]=intake.MAX_DIRECTORY_BYTES+1
                return type(info)(values)
            return info
        monkeypatch.setattr(intake,'_ordinary',oversize)
    with pytest.raises((ValueError,TypeError)):
        intake.load_joint_development(str(tmp_path))


def test_growing_file_hash_is_bounded(tmp_path,monkeypatch):
    path=tmp_path/'growth';path.write_bytes(b'actual bytes')
    info=path.stat()
    values=list(info);values[6]=3
    smaller=type(info)(values)
    monkeypatch.setattr(intake,'_ordinary',lambda p,directory=False:smaller)
    # Actual fstat proves the mismatch before streaming, no hash-until-EOF.
    with pytest.raises(ValueError,match='drift'):
        intake._file_sha(path)
