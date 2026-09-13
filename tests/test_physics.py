import numpy as np

from geophysicslab.cases import get_case
from geophysicslab.model.physics import layered_mt, subsurface_model


def test_mt_response_is_finite_and_frequency_ordered():
    response = layered_mt(get_case("MT_MIXED"))
    assert len(response["frequency_hz"]) == len(response["phase_deg"]) == 24
    assert np.all(np.isfinite(response["apparent_resistivity_ohm_m"]))
    assert response["frequency_hz"][0] < response["frequency_hz"][-1]


def test_model_changes_with_depth_and_contrast():
    shallow = subsurface_model(get_case("GRAVITY_INTRUSION"))
    deep = subsurface_model(get_case("GRAVITY_DEEP_BODY"))
    assert shallow["density_gcc"] != deep["density_gcc"]
