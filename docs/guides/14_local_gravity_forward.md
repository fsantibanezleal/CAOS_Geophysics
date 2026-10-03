# Calculate a declared rectangular-prism gravity response

This local Python function evaluates a declared density-contrast model. It does
not invert measured data. Use the already installed, independently source-checked
CPython3.12.10 Windows runtime described in the
[operator design](../design/features/m02-prism-operator/design.md).
An unknown runtime rejects; this recipe does not install or upgrade packages.

Run from the repository root with its `data-pipeline` directory on the Python
module search path. In PowerShell, set `$env:PYTHONPATH` to that resolved local
directory and invoke the trusted pipeline interpreter. Do not reuse a runtime
solely because an environment has a similar name. The exact source/pin audit is
an external prerequisite, not a claim made by the function.

```python
import numpy as np
from gravity_forward import forward_gravity

request = {
    "schema": "gravity-prism-forward-request-1",
    "engine": "simpeg-0.25.2-geoana-0.8.1-f64-ram",
    "frame": {"kind": "local_cartesian", "axes": ("east", "north", "up"),
              "length_unit": "m", "vertical_positive": "up"},
    "mesh": {
        "origin_m": np.array([-50., -50., -100.]),
        "hx_m": np.array([100.]), "hy_m": np.array([100.]),
        "hz_m": np.array([100.]), "active": np.array([True]),
    },
    "receivers_m": np.array([[0., 0., 100.], [100., 50., 120.],
                             [-170., 30., 220.]]),
    "density_kg_m3": np.array([1000.]),
}
result = forward_gravity(request)
print(result["gz_up_mgal"])
print(result["jacobian_mgal_per_kg_m3"])
```

MAIN executed this exact Markdown code block in the reviewed runtime. The
three upward responses were approximately (-0.29272360, -0.13493608,
-0.05476427) mGal, with the single Jacobian column equal to those values divided
by1000 kg/m3. These displayed values are rounded readouts, not reference precision
or a fitted result. The independent physical-oracle checks retain full precision.

Float arrays must be native float64 exact NumPy arrays; the active mask is bool.
No list conversion, implicit dtype cast, default frame or receiver displacement
occurs. The mesh origin is its lower west/south/bottom corner, widths are positive
metres, and active cells follow x-fast full-mesh order. Every receiver must be
strictly outside the entire closed tensor box, including inactive/zero-density
cells. Interior, face and edge locations reject rather than shift.

Density contrast is in kg/m3. SimPEG's official field call consumes g/cm3;
the function converts exactly by1/1000 and returns upward g_z in mGal.
Positive mass below a receiver therefore produces negative upward g_z.
The Jacobian is mGal/(kg/m3), and the returned prediction must equal J times the
submitted active density. Signed and zero contrasts are valid. Returned owned
arrays are read-only and do not alias the submitted arrays.

The exact six-key result contains schema, frame, gz_up_mgal,
jacobian_mgal_per_kg_m3, geometry and provenance. Its verified engine geometry
includes physical bounds, centres, volumes, active indices, receivers and density.
Provenance records the actual runtime; `external_required_not_performed_by_operator`
does not mean the source audit was performed inside this pure function.

At most4096 total cells and2048 receivers are admitted. Oversized/malformed input,
unrepresentable geometry, unknown runtime or failed/nonfinite engine output
rejects without a successful result. Exception contexts are not a safe HTTP error
surface. No observed data, error model, residual, fitted model, uncertainty,
source eligibility or host approval exists in this contract.

Use the [independent review](../validation/gravity-forward-independent-review-2026-10-03.md)
for actual test counts, additional signed nonuniform geometry, two independent
physical oracles, runtime/source identity and retained integration failure.
