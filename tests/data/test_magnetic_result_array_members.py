"""Bounded NPY member codec controls; not a fitted result bundle."""

import hashlib
import struct

import numpy as np
import pytest

from magnetic_survey_json import InputError
from magnetic_survey_bundle import decode_array_member, encode_array_member


@pytest.mark.parametrize("array,unit", [
    (np.array([[1.25, -2.5], [0., 8.]], dtype=np.float64), "nT"),
    (np.array([[0, 1], [8, 17]], dtype=np.int64), "index"),
    (np.array([[True, False], [False, True]], dtype=np.bool_), "bool"),
])
def test_numeric_array_member_roundtrip(array, unit):
    member, raw = encode_array_member(array, name="rows.npy", unit=unit)
    assert set(member) == {"name", "dtype", "shape", "unit", "bytes", "sha256"}
    assert member["bytes"] == len(raw)
    assert member["sha256"] == hashlib.sha256(raw).hexdigest()
    restored = decode_array_member(member, raw)
    assert restored.dtype == array.dtype
    assert restored.shape == array.shape
    np.testing.assert_array_equal(restored, array)
    assert restored.flags.owndata


def test_rejects_object_and_unsupported_arrays_before_serializing():
    with pytest.raises((TypeError, ValueError)):
        encode_array_member(np.array([{"unsafe": True}], dtype=object),
                            name="object.npy", unit="1")
    with pytest.raises((TypeError, ValueError)):
        encode_array_member(np.array([1.], dtype=np.float32), name="single.npy", unit="nT")


@pytest.mark.parametrize("mutation", ["name", "dtype", "shape", "unit", "bytes", "hash"])
def test_rejects_member_descriptor_tampering(mutation):
    member, raw = encode_array_member(np.array([1., 2.], dtype=np.float64),
                                      name="observed.npy", unit="nT")
    changed = dict(member)
    if mutation == "name":
        changed["name"] = "../observed.npy"
    elif mutation == "dtype":
        changed["dtype"] = "int64"
    elif mutation == "shape":
        changed["shape"] = [1, 2]
    elif mutation == "unit":
        changed["unit"] = "degrees"
    elif mutation == "bytes":
        changed["bytes"] += 1
    else:
        changed["sha256"] = "0" * 64
    with pytest.raises(InputError):
        decode_array_member(changed, raw)


def test_rejects_pickle_object_payload_and_trailing_bytes():
    import io
    stream = io.BytesIO()
    np.lib.format.write_array(stream, np.array(["x"], dtype=object), allow_pickle=True)
    raw = stream.getvalue()
    member = {"name": "x.npy", "dtype": "float64", "shape": [1], "unit": "1",
              "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    with pytest.raises(InputError):
        decode_array_member(member, raw)

    valid, raw = encode_array_member(np.array([1.], dtype=np.float64), name="x.npy", unit="1")
    with pytest.raises(InputError):
        decode_array_member(valid, raw + b"trailing")


def test_big_endian_npy_is_decoded_to_owned_native_dtype():
    import io
    values = np.array([1.25, -2.5], dtype=">f8")
    stream = io.BytesIO()
    np.lib.format.write_array(stream, values, version=(2, 0), allow_pickle=False)
    raw = stream.getvalue()
    member = {"name": "endian.npy", "dtype": "float64", "shape": [2], "unit": "nT",
              "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    restored = decode_array_member(member, raw)
    assert restored.dtype == np.dtype(np.float64)
    assert restored.dtype.isnative and restored.flags.owndata
    np.testing.assert_array_equal(restored, [1.25, -2.5])


def test_rejects_numpy_header_above_contract_limit():
    header = b" " * 65537
    raw = b"\x93NUMPY\x02\x00" + struct.pack("<I", len(header)) + header + b"\x00"*8
    member = {"name": "x.npy", "dtype": "float64", "shape": [1], "unit": "nT",
              "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}
    with pytest.raises(InputError):
        decode_array_member(member, raw)
