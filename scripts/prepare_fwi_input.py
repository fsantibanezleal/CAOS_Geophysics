"""Bind operator-prepared little-endian acoustic arrays; no scientific solve."""
import argparse
from pathlib import Path
import struct
import sys
import math

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/"data-pipeline"))
from fwi_user_data import (SCHEMA, SOURCES, MAX_ARRAY, SHAPE, admit, canonical,
                           digest, exclusive, external, read_regular,
                           receiver_coordinates, validate_request)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--observed", type=Path, required=True)
    p.add_argument("--initial", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--id", required=True)
    p.add_argument("--citation", required=True)
    p.add_argument("--rights", choices=("owner-permitted", "CC0", "CC-BY"), required=True)
    p.add_argument("--scope", choices=("owner-provided", "synthetic-control"), required=True)
    p.add_argument("--receivers", type=int, choices=(20,40), required=True)
    p.add_argument("--samples", type=int, required=True)
    p.add_argument("--frequency-hz", type=float, required=True)
    p.add_argument("--beta", type=float, required=True)
    p.add_argument("--iterations-per-stage", type=int, required=True)
    args = p.parse_args(argv)
    try:
        output = external(args.output)
        if output.exists() or not output.parent.is_dir():
            raise ValueError()
        original = {"observed":read_regular(args.observed,MAX_ARRAY),
                    "initial":read_regular(args.initial,4*96*128)}
        descriptors = {}
        for name, raw in original.items():
            shape = [3,args.receivers,args.samples] if name == "observed" else SHAPE
            descriptors[name] = {"shape":shape,"dtype":"float32-le","units":"point-source-amplitude" if name == "observed" else "m/s",
                                 "bytes":len(raw),"sha256":digest(raw)}
        request = {"schema":SCHEMA,"id":args.id,"source":{"citation":args.citation,"rights":args.rights,"scope":args.scope},
                   "acquisition":{"frame":"local-x-z-down","spacing_m":12.5,"dt_s":.0005,"sources_m":SOURCES,
                                  "receivers_m":receiver_coordinates(args.receivers),"wavelet":"Ricker-peak-at-1.5-over-f",
                                  "amplitude_convention":"Deepwave-scalar-point-source"},
                   **descriptors,"parameters":{"frequency_hz":args.frequency_hz,"beta":args.beta,"iterations_per_stage":args.iterations_per_stage}}
        raw_request = canonical(request)
        validate_request(raw_request)
        for name, raw in original.items():
            energy = [0.,0.]
            for index, (value,) in enumerate(struct.iter_unpack("<f",raw)):
                if not math.isfinite(value) or (name == "initial" and not 1400 < value < 4400) or (name == "observed" and abs(value) > 1e12):
                    raise ValueError()
                if name == "observed":
                    energy[int((index//args.samples)%args.receivers%5 == 2)] += value*value
            if name == "observed" and min(energy) <= 0:
                raise ValueError()
        output.mkdir(parents=False)
        for name, raw in original.items():
            exclusive(output/(name+".f32"),raw)
        exclusive(output/"request.json",raw_request)
        admit(output)
    except (OSError, ValueError, KeyError, TypeError, OverflowError):
        print("Acoustic input preparation failed; arrays, declarations or fresh external output invalid",file=sys.stderr)
        return 2
    print("Original acoustic arrays bound and independently reopened; no solve, source estimation or field claim")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
