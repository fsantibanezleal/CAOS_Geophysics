# M09 Koenigsee local traveltime tasks

Dependency order; each task names its requirement gate.

1. [x] Read approved product SDD and governing ADRs/dossiers; inspect official method, fixed source bytes, rights, geometry and pick suitability. TT-01, TT-03, TT-08.
2. [x] Implement strict `.sgt` parse, source-bound units/geometry QC and malformed/negative/reciprocal-availability tests. TT-01 through TT-03.
3. [x] Pin isolated pyGIMLi runtime and independently test homogeneous Dijkstra travel time against analytic distance/speed, reciprocity and scaling. TT-04.
4. [x] Implement fixed whole-shot inverse/holdout gates, ray coverage, start/mesh sensitivity, failure-retaining ignored receipt and numerical tests. TT-05 through TT-07.
5. [x] Expand source/theory docs, run relevant tests/lint/content and record convergence; commit/push this scoped branch only, without merge or deploy. TT-08.
6. [x] Diagnose the reported independent rerun without modifying the old ignored receipt; distinguish fixed-model forward/mesh/Jacobian from the nonlinear inner solve. TT-09.
7. [x] Pin and test the inner CGLS convergence controls; tighten repeatability comparison without changing the predictive holdout/stop gates. TT-09.
8. [x] Run fresh and repeated full-field tests, verify the old receipt hash, update the convergence verdict, and push only the existing task branch. TT-09.
