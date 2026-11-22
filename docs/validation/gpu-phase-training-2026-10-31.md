# CUDA phase-picker training controls, 2026-10-31

## Result

The local CUDA training controls passed **7 tests, 0 failures, 0 errors, 0 skips**
in 40.780 seconds on the NVIDIA GeForce RTX 4070 Laptop GPU, using PyTorch
2.14.0+cu126 and CUDA 12.6. The run exercised the AMP non-finite-gradient
backoff path and a two-epoch train/resume/reproducibility path. It verifies the
training implementation's CUDA execution and checkpoint-resume controls; it is
not a full STEAD training run or evidence of phase-picking accuracy.

The test constructed isolated synthetic train/dev arrays under the external
`E:\_Datos\CAOS_Geophysics\_Temp\gpu-phase-training-20261031` root. It did not
open test waveforms. No canonical model, public artifact or repository data was
rewritten. The full JUnit receipt remains outside the repository at
`E:\_Datos\CAOS_Geophysics\validation\gpu-phase-training-20261031\junit.xml`.

## Reproduction

```powershell
$env:CUDA_VISIBLE_DEVICES='0'
$env:TORCHINDUCTOR_CACHE_DIR='E:\_Datos\CAOS_Geophysics\_Temp\torchinductor-phase-training-20261031'
$env:OPENBLAS_NUM_THREADS='1'
.venv-pipeline\Scripts\python.exe -m pytest tests/learning/test_phase_training.py -q --maxfail=1 --junitxml E:\_Datos\CAOS_Geophysics\validation\gpu-phase-training-20261031\junit.xml --basetemp E:\_Datos\CAOS_Geophysics\_Temp\gpu-phase-training-20261031
```

## Byte identities

| Item | SHA-256 |
| --- | --- |
| Product source revision at run start | `f0ec2fc37fdae1f0c1c7d40b6cae386a85d7e6ac` |
| `tests/learning/test_phase_training.py` | `f91edfc72eded8fbbb350c649280f86c1aca6dcf1558e0909dd97a69719998e4` |
| `scripts/train_stead_phase.py` | `dcf134847e257b1f73f18f6ef6484c6654d7a2450e3e89be334bd09d9abbcb8a` |
| `data-pipeline/phase_model.py` | `9a9f8b7db70831cdf1a17051b19250a5c16ac420cf68a0377254a2ccaeb49791` |
| External JUnit receipt | `5827e41e98caad0cf8e3dda315d6d76408b196bee775fec143221197d3612819` |
