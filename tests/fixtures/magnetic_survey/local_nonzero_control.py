"""Separate off-grid tiny supplied-data control; NOT frozen 528-cell S2 gates.

Acquisition/field/noise are declared before Choclo truth. No inverse simulation,
truth-derived prior, generated-amplitude SD or post-outer choice. Clean authored
observations have no added noise realization; SD .5 is conditional test metadata.
"""

import hashlib
import json


def populate(doc):
    import numpy as np
    import choclo
    from choclo.constants import VACUUM_MAGNETIC_PERMEABILITY as MU0
    from magnetic_survey_support import descriptor, rehash
    from magnetic_survey_json import parse_request
    from magnetic_survey import plan_geometry
    raw = json.dumps(doc, separators=(',', ':'), allow_nan=False).encode()
    plan = plan_geometry(parse_request(raw))  # geometry BEFORE physical values
    if doc['prior']['start_si']['shape'] != [7] or len(plan['inventory']['row_ids']) != 288:
        raise ValueError('Separate seven-cell/288-row control required')
    xyz = np.array(doc['geometry']['receivers_m']['data']).reshape(288, 3)
    inclination, declination = np.deg2rad([37., -73.])
    direction = np.array([np.cos(inclination)*np.sin(declination),
                          np.cos(inclination)*np.cos(declination), -np.sin(inclination)])
    bounds = (-125., -80., -145., -90., -250., -150.)
    magnetization = .012*50000.*direction*1e-9/MU0
    clean = np.array([[fun(*row, *bounds, *magnetization)*1e9
        for fun in (choclo.prism.magnetic_e, choclo.prism.magnetic_n, choclo.prism.magnetic_u)] for row in xyz])
    doc['observations']['values'] = descriptor('float64', [288, 3], clean.ravel().tolist())
    rehash(doc, 'observations/values')
    original = json.dumps(dict(schema='authored-local-magnetic-original-1', acquisition=doc['acquisition'],
        receivers_m=doc['geometry']['receivers_m'], quantity='secondary_enu_nT',
        observations=doc['observations'], inducing_field=doc['inducing_field']),
        sort_keys=True, separators=(',', ':'), allow_nan=False).encode()
    doc['source'].update(id='tiny-offgrid-independent-control', original_sha256=hashlib.sha256(original).hexdigest(),
        original_bytes=len(original), citation='Authored clean independent Choclo control, not field or frozen S2 truth')
    doc['processing']['nodes'][0]['input_sha256'] = doc['source']['original_sha256']
    doc['noise']['citation'] = 'Fixed SD .5 conditional control, no injected stochastic realization'
    return original, dict(bounds_m=list(bounds), chi_si=.012, remanence_A_m=[0., 0., 0.],
                         scope='separate_authored_tiny_evaluator_only')
