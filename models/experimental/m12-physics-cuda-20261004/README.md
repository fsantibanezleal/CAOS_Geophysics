# Geometry-normalized learned velocity experiment

This is a real locally trained CUDA checkpoint and a fully CPU-replayed receipt,
not a field model or a successful advantage claim. Original M12 source,
checkpoint and failed receipt are unchanged. Physical input corrects the
ray-length dimensional defect; output uses the already declared1400..4000 m/s
interval. Fresh realizations, selection and limitations are fixed in the
[revised design](../../../docs/design/features/velocity-physics-refinement/design.md).

Forty epochs on RTX4070 Laptop selected epoch40 by validation only. Checkpoint
SHA256 `23d51c42b079f37c85fe77796556962e9b7f4f2fe179650a329641a6faa9ded1`;
committed LF receipt SHA256 `d2d40acd5ce4bda7de54938c0ed50b21e0fd2666b84e6868f1b89adc4c22efa1`.
The original Windows-generated receipt is retained separately; Git's declared
LF normalization changes text bytes, not values, checkpoint or replay metrics.
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

Set M12_OUTPUT to a new absolute directory outside all repositories under the
device's model/data root. Use the ignored environment containing the pinned
scientific dependencies. TMP, TEMP and TMPDIR must point to external scratch.
Reproduce through the guarded launcher; the scientific source remains frozen:

```text
python scripts/run_m12_velocity.py --protocol physics-v2 --device cuda --output "$M12_OUTPUT"
python scripts/run_m12_velocity.py --protocol physics-v2 --verify --output "$M12_OUTPUT"
```

The above commands use POSIX variable syntax. On Windows use
`./scripts/run_m12_velocity.ps1 -Protocol physics-v2 -Device cuda -Output $env:M12_OUTPUT`
and `-Protocol physics-v2 -Verify -Output $env:M12_OUTPUT`. Verification needs
the original receipt and checkpoint together in that external directory, not
only the committed receipt. Launchers do not download missing weights or replace
an old receipt. They do not change the failed held-out comparator outcome.

User-data inference uses `scripts/process_velocity.py` with explicit
`--checkpoint-protocol physics-v2`, checkpoint path and the above SHA256.
It consumes the actual supplied times/geometry and keeps the negative benchmark
warning. No training, solver fallback or network occurs in that command.
