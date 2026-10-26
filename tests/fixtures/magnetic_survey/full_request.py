"""Complete modelling requests from UNCHANGED independent frozen S2 controls."""

import copy
import hashlib
import importlib.util
from pathlib import Path

from magnetic_survey_json import canonical, digest

spec = importlib.util.spec_from_file_location('s2_request_base', Path(__file__).parents[2]/'data'/'magnetic_survey_support.py')
support = importlib.util.module_from_spec(spec)
spec.loader.exec_module(support)


def generate(regime, quantity, binding):
    control = support.fixture.generate_control(regime, quantity)
    doc = support.request()
    doc['source'].update(id='S2-'+regime+'-'+quantity, original_sha256=hashlib.sha256(control['original_bytes']).hexdigest(),
        original_bytes=len(control['original_bytes']), citation='Independent full frozen authored S2 '+regime+', not field')
    doc['geometry'] = copy.deepcopy(control['geometry'])
    doc['acquisition'] = copy.deepcopy(control['acquisition'])
    doc['inducing_field'].update(control['declared_field'])
    doc['inducing_field']['source_sha256'] = digest(control['declared_field'])
    doc['observations'].update(quantity=quantity,
        values=support.descriptor('float64', list(control['observed_nT'].shape), control['observed_nT'].ravel().tolist()))
    support.rehash(doc, 'observations/values')
    doc['noise']['values'] = support.descriptor('float64', list(control['sd_nT'].shape), control['sd_nT'].ravel().tolist())
    doc['noise']['citation'] = 'Frozen authored conditional SD .5, PCG64 seed20261004; no field noise estimate'
    doc['processing']['quantity'] = quantity
    doc['processing']['background_relation'] = dict(secondary_enu_nT='secondary_field_declared',
        linear_tmi_nT='projection_of_secondary_declared',
        exact_total_anomaly_nT='total_norm_minus_declared_uniform_F')[quantity]
    doc['processing']['nodes'][0]['input_sha256'] = doc['source']['original_sha256']
    doc['policy']['optimizer_binding'] = dict(accepted_source=binding.optimizer_source_sha256,
        accepted_export=binding.accepted_export, epoch=binding.runtime_epoch)
    return doc, control['original_bytes'], dict(schema='magnetic-s2-evaluator-1', regime=regime, quantity=quantity,
        bodies=control['bodies'], truth_field=control['truth_field'], provenance=control['provenance'],
        original_bytes=len(control['original_bytes']), modelling_request_sha256=digest(doc),
        field_truth=False, frozen_generator_modified=False, control_identity=hashlib.sha256(canonical(control['provenance'])).hexdigest())
