"""Submitted M11 native planning controls; no inverse/field acceptance."""

from copy import deepcopy
import hashlib
import json

import numpy as np
import pytest

import joint_survey_plan as js


def request():
    def survey(magnetic=False):
        result = {
            'source': {'source_id': 'magnetic' if magnetic else 'gravity',
                       'citation': 'Original authored control, not field data',
                       'raw_sha256': ('b' if magnetic else 'a')*64, 'raw_bytes': 123,
                       'rights': 'private_use', 'correction_sha256': 'c'*64},
            'reference_id': 'authored-local-enu',
            'component': 'linear_tmi' if magnetic else 'gz_up',
            'unit': 'nT' if magnetic else 'mGal',
            'receivers_m': np.array([[20.,30.,100.], [50.,80.,110.], [-90.,40.,130.],
                                     [10.,-10.,150.], [90.,-50.,120.], [130.,40.,160.]]),
            'mask': np.zeros(6, dtype=bool), 'missing_reasons': ('',)*6,
            'groups': np.array([0,0,1,1,2,2], dtype=np.int64),
            'partition': np.array([0,0,1,1,2,2], dtype=np.int64),
            'noise': {'kind': 'diagonal_sd', 'unit': 'nT' if magnetic else 'mGal',
                      'basis': 'measured_gaussian', 'cross_partition': 'declared_absent',
                      'citation': 'Independent declared observation-error experiment'}}
        if magnetic:
            result['inducing_field'] = {'amplitude_nt':50000., 'inclination_deg':60.,
                                        'declination_deg':12.}
            result['receivers_m'][:,0] += 5.
        return result

    def prior(magnetic=False):
        return {'lower': np.full(12, 0. if magnetic else -1500.),
                'upper': np.full(12, .1 if magnetic else 1500.),
                'start': np.full(12, .005 if magnetic else 0.),
                'reference': np.full(12, .005 if magnetic else 0.),
                'scale': .03 if magnetic else 750.}

    return {'schema':'joint-survey-plan-request-1',
            'frame':{'kind':'local_cartesian','axes':('east','north','up'),'length_unit':'m',
                     'vertical_positive':'up','reference_id':'authored-local-enu',
                     'horizontal_datum':'declared local east/north origin',
                     'vertical_datum':'declared local elevation datum'},
            'mesh':{'origin_m':np.array([-140.,-180.,-260.]),
                    'hx_m':np.array([40.,70.,90.]),'hy_m':np.array([30.,50.]),
                    'hz_m':np.array([60.,110.]),'active':np.ones(12, dtype=bool)},
            'gravity':survey(), 'magnetic':survey(True),
            'prior':{'density':prior(),'susceptibility':prior(True),
                     'lengths_m':np.array([60.,110.,75.]),'coupling_length_m':100.,
                     'basis':'Author declared scales, no trained normalization'},
            'policy':{'name':'joint-survey-l2-cross-gradient-1','seed':42,
                      'cell_order':'x-fast','training':'not_applicable_classical',
                      'group_scope':'global_acquisition','modal_covariance':'independent'}}


def arrays(value):
    if type(value) is dict:
        return [a for child in value.values() for a in arrays(child)]
    if type(value) is tuple:
        return [a for child in value for a in arrays(child)]
    return [value] if type(value) is np.ndarray else []


class Hook:
    def __eq__(self, other):
        pytest.fail('custom equality invoked')
    def __array__(self, *args, **kwargs):
        pytest.fail('custom array conversion invoked')


@pytest.mark.parametrize('bad', ['root_subclass','root_extra','schema_hook','frame_subclass',
    'axes_hook','axes_list','source_hook','source_extra','source_id_hook','rights_unknown',
    'field_float_subclass','array_subclass','float32','object','endian','seed_bool',
    'unit_wrong','noise_cov_units','datum_empty','prior_int_scale','prior_array_hook'])
def test_exact_contract(bad, monkeypatch):
    req=request()
    if bad=='root_subclass': req=type('Sub',(dict,),{})(req)
    elif bad=='root_extra': req['observations']=np.zeros(6)
    elif bad=='schema_hook': req['schema']=Hook()
    elif bad=='frame_subclass': req['frame']=type('Sub',(dict,),{})(req['frame'])
    elif bad=='axes_hook': req['frame']['axes']=(Hook(),'north','up')
    elif bad=='axes_list': req['frame']['axes']=['east','north','up']
    elif bad=='source_hook': req['gravity']['source']=Hook()
    elif bad=='source_extra': req['gravity']['source']['fetch']='not permitted'
    elif bad=='source_id_hook': req['gravity']['source']['source_id']=Hook()
    elif bad=='rights_unknown': req['gravity']['source']['rights']='unknown'
    elif bad=='field_float_subclass': req['magnetic']['inducing_field']['amplitude_nt']=np.float64(50000.)
    elif bad=='array_subclass': req['mesh']['hx_m']=req['mesh']['hx_m'].view(type('Sub',(np.ndarray,),{}))
    elif bad in ('float32','object','endian'):
        req['gravity']['receivers_m']=req['gravity']['receivers_m'].astype(
            {'float32':'float32','object':'object','endian':'>f8'}[bad])
    elif bad=='seed_bool': req['policy']['seed']=True
    elif bad=='unit_wrong': req['gravity']['unit']='m/s2'
    elif bad=='noise_cov_units': req['gravity']['noise']['kind']='full_covariance'
    elif bad=='datum_empty': req['frame']['vertical_datum']=''
    elif bad=='prior_int_scale': req['prior']['density']['scale']=750
    elif bad=='prior_array_hook': req['prior']['susceptibility']['upper']=Hook()
    monkeypatch.setattr(js,'_finite',lambda *a:pytest.fail('finite before type rejection'))
    with pytest.raises((TypeError,ValueError)): js.plan_joint_survey(req)


@pytest.mark.parametrize('bad',['axis65','cells_plus1','receiver2049','receiver_shape',
    'prior_shape','mask_shape','groups_dtype','citation_empty_containers','oversize_text',
    'metadata_bytes','kernel_bytes'])
def test_preallocation_rejection(bad, monkeypatch):
    req=request()
    if bad=='axis65': req['mesh']['hx_m']=np.ones(65)
    elif bad=='cells_plus1':
        req['mesh'].update(hx_m=np.ones(17),hy_m=np.ones(17),hz_m=np.ones(17))
    elif bad=='receiver2049': req['magnetic']['receivers_m']=np.ones((2049,3))
    elif bad=='receiver_shape': req['magnetic']['receivers_m']=np.ones((6,4))
    elif bad=='prior_shape': req['prior']['density']['upper']=np.ones(13)
    elif bad=='mask_shape': req['gravity']['mask']=np.zeros(7,bool)
    elif bad=='groups_dtype': req['gravity']['groups']=np.arange(6, dtype=np.int32)
    elif bad=='citation_empty_containers': req['gravity']['source']['citation']=(((),)*32768,)*5
    elif bad=='oversize_text': req['gravity']['source']['citation']='a'*4097
    elif bad=='metadata_bytes':
        n=70
        req['gravity'].update(receivers_m=np.zeros((n,3)),mask=np.ones(n,bool),
            missing_reasons=('a'*4096,)*n,groups=np.arange(n,dtype=np.int64),partition=np.zeros(n,np.int64))
    elif bad=='kernel_bytes':
        n=2048; full=4096
        req['mesh'].update(hx_m=np.ones(16),hy_m=np.ones(16),hz_m=np.ones(16),active=np.ones(full,bool))
        for key in ('density','susceptibility'):
            for name in ('lower','upper','start','reference'): req['prior'][key][name]=np.zeros(full)
        for modality in ('gravity','magnetic'):
            req[modality].update(receivers_m=np.zeros((n,3)),mask=np.zeros(n,bool),
                missing_reasons=('',)*n,groups=np.arange(n,dtype=np.int64),partition=np.zeros(n,np.int64))
    monkeypatch.setattr(js,'_finite',lambda *a:pytest.fail('finite before cap rejection'))
    monkeypatch.setattr(js,'_snapshot',lambda *a:pytest.fail('copy before cap rejection'))
    monkeypatch.setattr(js,'_digest',lambda *a:pytest.fail('hash before cap rejection'))
    monkeypatch.setattr(js.discretize,'TensorMesh',lambda *a,**k:pytest.fail('mesh before cap rejection'))
    with pytest.raises((TypeError,ValueError)): js.plan_joint_survey(req)


def test_descriptor_exact_boundary_and_empty_containers():
    body={'unicode':'café\n"','tuple':(0.,-0.,True),'array':np.zeros((2,3))}
    descriptor={'unicode':'café\n"','tuple':(0.,-0.,True),
                'array':{'dtype':'<f8','shape':[2,3],'sha256':'0'*64}}
    expected=len(json.dumps(descriptor,ensure_ascii=False,sort_keys=True,
                            separators=(',',':')).encode('utf-8'))
    assert js._metadata_budget(body,expected)==expected
    with pytest.raises(ValueError): js._metadata_budget(body,expected-1)
    with pytest.raises(ValueError): js._metadata_budget((((),)*32768,)*5)
    assert js._metadata_budget(((),)*40000)==120001


def test_metadata_scalar_and_logical_alias_boundaries():
    assert js._metadata_budget((0.,)*32768)==131073
    with pytest.raises(ValueError): js._metadata_budget((0.,)*32769)
    leaf=np.zeros(8192)  #64KiB physical storage,96MiB logical alias descriptor.
    assert js._metadata_budget((leaf,)*1536)<262144
    with pytest.raises(ValueError): js._metadata_budget((leaf,)*1537)
    # Container punctuation alone exceeds the cap before an invalid child can
    # be visited; no huge value storage and no full-tree serialization.
    with pytest.raises(ValueError): js._metadata_budget((Hook(),)*262145)


def test_same_raw_bytes_not_independent_source_proof():
    req=request(); req['magnetic']['source']['raw_sha256']=req['gravity']['source']['raw_sha256']
    plan=js.plan_joint_survey(req)
    assert plan['diagnostics']['shared_raw_bytes']
    assert plan['diagnostics']['rank_not_assessed']
    req['magnetic']['source']['source_id']=req['gravity']['source']['source_id']
    with pytest.raises(ValueError): js.plan_joint_survey(req)


@pytest.mark.parametrize('bad',['mask_reason','unmasked_reason','masked_partition',
    'cross_modal_group','negative_group','duplicate_receiver','reference_mismatch'])
def test_global_blocks_and_masks(bad):
    req=request()
    if bad=='mask_reason': req['gravity']['mask'][0]=True
    elif bad=='unmasked_reason': req['gravity']['missing_reasons']=('excluded',)+('',)*5
    elif bad=='masked_partition':
        req['gravity']['mask'][4:]=True; req['gravity']['missing_reasons']=('',)*4+('missing',)*2
    elif bad=='cross_modal_group': req['magnetic']['partition'][0]=2
    elif bad=='negative_group': req['gravity']['groups'][0]=-1
    elif bad=='duplicate_receiver': req['gravity']['receivers_m'][1]=req['gravity']['receivers_m'][0]
    elif bad=='reference_mismatch': req['magnetic']['reference_id']='different origin'
    with pytest.raises(ValueError): js.plan_joint_survey(req)


@pytest.mark.parametrize('bad',['nonfinite','inside','on_face','width_negative',
    'unrepresentable_origin','start_outside','lower_equal_upper','chi_negative','length_zero'])
def test_geometry_and_order(bad):
    req=request()
    if bad=='nonfinite': req['gravity']['receivers_m'][0,0]=np.nan
    elif bad=='inside': req['gravity']['receivers_m'][0]=[-120.,-165.,-230.]
    elif bad=='on_face': req['gravity']['receivers_m'][0]=[-140.,-165.,-230.]
    elif bad=='width_negative': req['mesh']['hx_m'][0]=-1.
    elif bad=='unrepresentable_origin': req['mesh']['origin_m'][0]=1e16
    elif bad=='start_outside': req['prior']['density']['start'][0]=1501.
    elif bad=='lower_equal_upper': req['prior']['density']['lower'][0]=1500.
    elif bad=='chi_negative': req['prior']['susceptibility']['lower'][0]=-.01
    elif bad=='length_zero': req['prior']['lengths_m'][0]=0.
    with pytest.raises(ValueError): js.plan_joint_survey(req)


def test_source_and_snapshot():
    req=request(); before=[hashlib.sha256(a.tobytes()).hexdigest() for a in arrays(req)]
    plan=js.plan_joint_survey(req); other=js.plan_joint_survey(deepcopy(req))
    assert plan['schema']=='joint-survey-plan-1'
    assert plan['plan_sha256']==other['plan_sha256']
    assert plan['resources']['projected_kernel_bytes']==(6+3*6)*12*8
    assert not plan['diagnostics']['field_eligible']
    assert not plan['diagnostics']['source_bytes_verified']
    assert not plan['diagnostics']['rights_verified']
    assert not plan['diagnostics']['inverse_completed']
    np.testing.assert_array_equal(plan['gravity']['training_rows'],[0,1])
    for output in arrays(plan):
        assert output.flags.owndata and output.flags.c_contiguous and not output.flags.writeable
        assert all(not np.shares_memory(output,a) for a in arrays(req))
    assert before==[hashlib.sha256(a.tobytes()).hexdigest() for a in arrays(req)]
    req['gravity']['receivers_m'][0,0]+=1.
    assert js.plan_joint_survey(req)['plan_sha256']!=plan['plan_sha256']


def test_sparse_active_and_decimal_geometry():
    req=request(); req['mesh']['hx_m']=np.array([.3,.7,.9])
    req['mesh']['active'][[2,5,8]]=False
    for prop in ('density','susceptibility'):
        for key in ('lower','upper','start','reference'):
            req['prior'][prop][key]=req['prior'][prop][key][req['mesh']['active']]
    plan=js.plan_joint_survey(req)
    assert plan['mesh']['active'].sum()==9
    assert plan['diagnostics']['active_cells']==9


def test_no_private_m02_import_or_io():
    from pathlib import Path
    import ast
    source=Path(js.__file__).read_text(encoding='utf-8'); tree=ast.parse(source)
    names=[n.module for n in ast.walk(tree) if isinstance(n,ast.ImportFrom)]
    names += [a.name for n in ast.walk(tree) if isinstance(n,ast.Import) for a in n.names]
    assert not any(name and ('gravity_l2' in name or 'gravity_survey_l2' in name) for name in names)
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id=='open' for n in ast.walk(tree))


@pytest.mark.parametrize('version',['0.0.0',Hook()])
def test_loaded_runtime_version_types(version,monkeypatch):
    monkeypatch.setattr(js.simpeg,'__version__',version)
    with pytest.raises(RuntimeError): js.plan_joint_survey(request())


@pytest.mark.parametrize('bad',['node_nan','node_shift','centre_bias','bad_volume','bad_bounds','nonfinite_centre'])
def test_actual_tensor_geometry_fail_closed(bad,monkeypatch):
    from types import SimpleNamespace
    real=js.discretize.TensorMesh
    def invalid(*args,**kwargs):
        mesh=real(*args,**kwargs)
        state=SimpleNamespace(nodes_x=mesh.nodes_x.copy(),nodes_y=mesh.nodes_y.copy(),
            nodes_z=mesh.nodes_z.copy(),cell_bounds=mesh.cell_bounds.copy(),
            cell_centers=mesh.cell_centers.copy(),cell_volumes=mesh.cell_volumes.copy())
        if bad=='node_nan': state.nodes_x[0]=np.nan
        elif bad=='node_shift': state.nodes_x[1]+=1.
        elif bad=='centre_bias': state.cell_centers[0,0]+=1.
        elif bad=='bad_volume': state.cell_volumes[0]*=1.01
        elif bad=='bad_bounds': state.cell_bounds[0,1]+=1.
        else: state.cell_centers[0,0]=np.nan
        return state
    monkeypatch.setattr(js.discretize,'TensorMesh',invalid)
    with pytest.raises(ValueError): js.plan_joint_survey(request())
