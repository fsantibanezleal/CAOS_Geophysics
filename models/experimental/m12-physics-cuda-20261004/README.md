# Geometry-normalized learned velocity experiment

This is a real locally trained CUDA checkpoint and a fully CPU-replayed receipt,
not a field model or a successful advantage claim. Original M12 source,
checkpoint and failed receipt are unchanged. Physical input corrects the
ray-length dimensional defect; output uses the already declared1400..4000 m/s
interval. Fresh realizations, selection and limitations are fixed in the
[revised design](../../../docs/design/features/velocity-physics-refinement/design.md).

Forty epochs on RTX4070 Laptop selected epoch40 by validation only. Checkpoint
SHA256 `23d51c42b079f37c85fe77796556962e9b7f4f2fe179650a329641a6faa9ded1`;
receipt SHA256 `9c4d0df43aa1d3e7fd995c81a7a3da497465459c17ed1ebf618f2615a41621da`.
All480 held-out records and160 validation records are independently replayed
on CPU, retaining all failures/flags. Full combined physical/user-data suite
was32PASS/zero skips before optional revised-checkpoint CLI integration.

| Cohort | N | CNN model RMSE,m/s | Classical model RMSE,m/s | CNN forward RMSE,ms | Classical forward RMSE,ms | Flagged |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Validation |160|46.87|16.62|3.43|0.82|8|
| ID |160|50.51|16.86|3.66|0.83|13|
| New family |80|212.82|97.99|13.09|2.35|80|
| New acquisition |80|53.10|17.53|3.99|0.84|8|
| Joint family/acquisition |160|206.21|94.27|12.56|2.32|160|

These are means of per-realization RMSE, not pooled training RMSE. The CNN still
loses to the matched classical baseline: joint model ratio2.1875 and data
ratio5.4173. The validation95th-percentile residual flag is5.8050 ms; all160
joint cases are flagged, but13/160 ID controls are flagged too. It is not a
field-calibrated novelty probability. Fresh realization seeds do not make the
already known family definitions an independent geological discovery.

Reproduce from a new explicit output directory:

```text
python data-pipeline/velocity_physics_refinement.py --device cuda --output data/experiments/m12-physics-new
python data-pipeline/velocity_physics_refinement.py --verify --output models/experimental/m12-physics-cuda-20261004
```

User-data inference uses `scripts/process_velocity.py` with explicit
`--checkpoint-protocol physics-v2`, checkpoint path and the above SHA256.
It consumes the actual supplied times/geometry and keeps the negative benchmark
warning. No training, solver fallback or network occurs in that command.
