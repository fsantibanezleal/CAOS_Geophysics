"""The service and CLI must parse the same original grammar without normalization."""
import numpy as np
import pytest

from ert import ERTError, parse_ohm, parse_ohm_bytes
from traveltime import TraveltimeError, parse_sgt, parse_sgt_bytes


@pytest.mark.parametrize("method", ["ert", "traveltime"])
def test_bytes_and_original_file_are_identical(tmp_path, method):
    if method == "ert":
        raw = (b"# Wenner array with 2m\n8# Number of sensors\n#x z\n0 0\n2 0\n4 0\n6 0\n8 0\n10 0\n12 0\n14 0\n"
               b"5# Number of data\n#a b m n R\n1 4 2 3 1\n2 5 3 4 1\n3 6 4 5 1\n4 7 5 6 1\n5 8 6 7 1\n")
        parse_file, parse_bytes, error = parse_ohm, parse_ohm_bytes, ERTError
        keys = ("sensors_xz_m", "abmn", "resistance_ohm")
    else:
        raw = (b"5 # shot/geophone points\n#x y\n0 0\n1 0\n2 0\n3 0\n4 0\n"
               b"4 # measurements\n#s g t\n1 2 .001\n1 3 .002\n1 4 .003\n1 5 .004\n")
        parse_file, parse_bytes, error = parse_sgt, parse_sgt_bytes, TraveltimeError
        keys = ("sensor_xy_m", "shot_geophone", "time_s")
    path = tmp_path/"original"
    path.write_bytes(raw)
    file_survey, byte_survey = parse_file(path), parse_bytes(raw)
    for key in keys:
        assert np.array_equal(getattr(file_survey, key), getattr(byte_survey, key))
    for invalid in (raw+b"unexpected trailing payload\n", raw.replace(b"0 0", b"nan 0", 1), b"\xff"):
        path.write_bytes(invalid)
        with pytest.raises(error):
            parse_file(path)
        with pytest.raises(error):
            parse_bytes(invalid)
    with pytest.raises(error):
        parse_bytes(b"x"*1_000_001)
