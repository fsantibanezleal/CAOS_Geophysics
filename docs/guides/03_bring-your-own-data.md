# Bring your own observations

For layered forward modelling, open Experiments and import JSON with `rho` and `thickness` arrays. Inputs stay inside your browser. Export includes calculated complex impedance, apparent resistivity and phase. This is not an EDI inversion interface.

For gravity or magnetics, prepare CSV with exact headers `east_m,north_m,up_m,value,sigma`. Run `python data-pipeline/ingest.py --csv survey.csv --family gravity --output data/raw/user-inversion.json`. Coordinates must be Cartesian ENU metres; gravity is upward gz in mGal, magnetics TMI in nT. Explicit errors reject nonfinite values, nonpositive sigma and duplicate stations. Do not submit geographic longitude/latitude as metres.

The automatic mesh is a simple bounded local volume below the stations. You must handle regional removal, terrain, coordinate transforms and magnetic field configuration before interpreting the inverse model. The returned result has no known-truth accuracy metric.

Run `python data-pipeline/ingest.py --external` to obtain/check and preprocess the two provenance-pinned SimPEG tutorial observation tables. These are synthetic teaching datasets, not field data. Their raw and preprocessed values remain local; public metadata records 289 stations per archive and transformation hashes. This workflow is independent from the original synthetic public benchmark.
