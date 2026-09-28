# M07 Slagdump ERT tasks

Dependency order; each task names its requirement gate.

1. [x] Read approved SDD/ADRs, source guide and scientific dossier; verify fixed provider bytes/hash and inspect upstream rights and source geometry. ERT-01, ERT-02, ERT-08.
2. [x] Implement strict `.ohm` parser and source-bound QC, with malformed, unit, index, geometry and reciprocal-availability tests. ERT-01 through ERT-03.
3. [x] Pin pyGIMLi and implement analytical flat plus numerical topographic factor/oracle controls. ERT-04.
4. [x] Implement fixed train/holdout 2D inverse, reproducible ignored receipt, forward residual and sensitivity checks. ERT-05 through ERT-07.
5. [x] Expand source guide with units, rights, reproducibility and limitations; run tests, lint and content gates; record convergence, then commit/push this branch without merge or deploy. ERT-08.
