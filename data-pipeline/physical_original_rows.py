"""Closed terminal-only exact row reductions; no solver or caller authority.

The physical factor nesting is unchanged. Signed dyadic coefficients times
finite decimal endpoints are summed as integers, then rounded outwards once.
Unsupported ranges fail closed rather than changing the certificate method.
"""
from decimal import Decimal
import hashlib
from pathlib import Path
import sys

import numpy as np
import scipy.sparse as sp

import gravity_l2_precision as intervals

MAX_ENTRIES = 4096
MAX_DIGITS = 1200
MIN_EXPONENT, MAX_EXPONENT = -1200, 1200
ENDPOINT_SLOT_BYTES = 2048
ROW_WORKSPACE_BYTES = 8*1024*1024
ARITHMETIC_EPOCH = 'exact-dyadic-original-terminal-2'


def _endpoint(value):
    if type(value) is not Decimal or not value.is_finite():
        raise ValueError('original rows: finite literal Decimal endpoint')
    parts = value.as_tuple()
    if len(parts.digits) > MAX_DIGITS or not MIN_EXPONENT <= parts.exponent <= MAX_EXPONENT:
        raise ValueError('original rows: bounded endpoint digits/exponent')
    integer = int(Decimal((parts.sign, parts.digits, 0)))
    return integer, parts.exponent if integer else 0


def _prepare(vector, check):
    if not 0 <= len(vector) <= MAX_ENTRIES:
        raise ValueError('original rows: closed vector capacity')
    result = []
    exponent = 0
    for index, pair in enumerate(vector):
        if index % 16 == 0:
            check()
        if len(pair) != 2 or pair[0] > pair[1]:
            raise ValueError('original rows: ordered interval pair')
        lo, hi = _endpoint(pair[0]), _endpoint(pair[1])
        # Two significands/exponents plus container/backing count literally.
        capacity = (sys.getsizeof((lo, hi)) + sys.getsizeof(lo) + sys.getsizeof(hi)
            + sum(sys.getsizeof(v) for v in (*lo, *hi)) + 16)
        if capacity > ENDPOINT_SLOT_BYTES:
            raise ValueError('original rows: endpoint slot capacity')
        result.append((lo, hi))
        exponent = min(exponent, lo[1], hi[1])
    return result, exponent


def _decimal(integer, exponent):
    # Decimal(int) and tuple construction are exact and context-independent.
    d = Decimal(integer)
    p = d.as_tuple()
    return Decimal((p.sign, p.digits, exponent))


def _integer_bytes(bits):
    # CPython int stores 30-bit digits in 4-byte slots on the reviewed runtime.
    # Runtime-native sys.int_info is used instead of assuming the layout.
    return sys.getsizeof(0) + ((bits+sys.int_info.bits_per_digit-1)
        // sys.int_info.bits_per_digit)*sys.int_info.sizeof_digit


def _aligned(prepared, exponent):
    result = []
    for pair in prepared:
        bits = [abs(v).bit_length()+((e-exponent)*3322+999)//1000 for v, e in pair]
        capacity = 2*sys.getsizeof(None)+sum(_integer_bytes(b) for b in bits)+64
        if capacity > ENDPOINT_SLOT_BYTES:
            raise ValueError('original rows: aligned endpoint slot capacity')
        result.append(tuple(v*10**(e-exponent) for v, e in pair))
    return np.array(result, dtype=object).T.copy()


class OriginalTerminalIntervals(intervals._Intervals):
    """Private fixed arithmetic of the source-owned original terminal owner."""
    def __init__(self, digits, deadline):
        super().__init__(digits, deadline)
        self._use_native_rows = False

    def matrix(self, matrix, vector):
        self.check()
        if sp.issparse(matrix) or matrix.shape[1] <= 8:
            return self._decimal_matrix(matrix, vector)
        if (matrix.ndim != 2 or matrix.dtype != np.float64
            or matrix.shape[1] != len(vector) or max(matrix.shape) > MAX_ENTRIES):
            raise ValueError('original rows: closed dense source dimensions/dtype')
        prepared, exponent = _prepare(vector, self.check)
        aligned = _aligned(prepared, exponent)
        del prepared
        endpoint_bits = max((abs(v).bit_length() for v in aligned.flat), default=0)
        result = []
        offset = 0
        while offset < len(matrix):
            self.check()
            rows = matrix[offset:offset+8]
            if not np.isfinite(rows).all():
                raise ValueError('original rows: finite binary64 coefficient')
            bits = rows.view(np.uint64)
            binary = ((bits >> np.uint64(52)) & np.uint64(2047)).astype(np.int64)
            significands = (bits & np.uint64((1 << 52)-1)).astype(np.int64)
            significands[binary != 0] |= np.int64(1 << 52)
            negative = (bits >> np.uint64(63)) != 0
            significands[negative] *= -1
            powers = np.where(binary == 0, -1074, binary-1075)
            # Exact IEEE zero is 0*2^0, not a subnormal NONZERO coefficient.
            # It must not inflate the common denominator of other entries.
            powers[significands == 0] = 0
            binary_exponent = int(np.min(powers, initial=0))
            shifts = powers-binary_exponent
            max_bits = 53+int(np.max(shifts, initial=0))
            count = rows.shape[1]
            # Coefficients, selected endpoint references, one product array,
            # accumulator/conversion tuples, native arrays, and metadata coexist.
            # Native bit decoding is allocated for all <=8 source rows, even
            # if object products subsequently fit only a smaller block.
            fixed = 128*len(rows)*count+262144
            per_row = count*(_integer_bytes(max_bits)+_integer_bytes(max_bits+endpoint_bits)+96)
            block = min(len(rows), (ROW_WORKSPACE_BYTES-fixed)//per_row)
            if block < 1:
                raise ValueError('original rows: simultaneous exact row workspace capacity')
            multipliers = np.left_shift(significands[:block].astype(object), shifts[:block])
            left = np.where(negative[:block], aligned[1], aligned[0])
            right = np.where(negative[:block], aligned[0], aligned[1])
            lo = np.sum(multipliers*left, axis=1)
            hi = np.sum(multipliers*right, axis=1)
            power = 5**(-binary_exponent)
            for low, high in zip(lo, hi):
                # <14100 accumulator bits and <5100 final decimal digits.
                if max(int(low).bit_length(), int(high).bit_length()) >= 14100:
                    raise ValueError('original rows: accumulator capacity')
                lower = _decimal(int(low)*power, exponent+binary_exponent)
                upper = _decimal(int(high)*power, exponent+binary_exponent)
                result.append((self.lo.plus(lower), self.hi.plus(upper)))
            offset += block
        self.check()
        return result


SOURCE_SHA256 = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
