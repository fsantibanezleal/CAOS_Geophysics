# M02 current-source resource replay : 2026-11-05

## Result

The source-pinned serial harness completed 20 capped and 20 nominal trials. All 20 nominal controls passed. The capped stress set passed 19/20; control 15 did not complete its admitted solve and is a hard failure for this run. The runner exits nonzero. This is not resource acceptance or a host-admission result.

| Lane | Passes | p95 sampled process-tree RSS | p95 outer wall time | Maximum observed RSS |
|---|---:|---:|---:|---:|
| Capped original-size controls | 19/20 | 755,546,112 bytes | 134.8457 s | 756,596,736 bytes |
| Nominal controls | 20/20 | 287,014,093 bytes | 471.1309 s | 287,543,296 bytes |

The failed capped control is `unsealed_real_cap_2048_4096_diagonal_prism`: 2,048 receivers, 4,096 active cells, and a 64 MiB dense kernel. Its solver stopped after two iterations at the internal wall cap, with normalized KKT `1.0810906429415282e-14`; the low KKT value does not turn a wall-capped, nonconverged result into a completed solve. The separately recorded high-precision chord diagnostic is explicitly marked `diagnostic_chord_not_solver_direction=true`; it is not evidence that the production solver accepted a step or converged.

## Reproduction and custody

Command:

```powershell
.\.venv-pipeline\Scripts\python.exe scripts\validate_m02_resources.py --output <external-validation-directory> --count 20
```

The complete per-trial JSON, process-tree sampling records, and logs remain outside the repository at `E:\_Datos\CAOS_Geophysics\validation\m02-resource-current-20261105\`. The aggregate `summary.json` SHA-256 is `b1d89a24f01e739ae6a426d9dbafc64b638fe9b38a96bda7bbe3f272c4e62d4f`. The harness SHA-256 is `d7dd475e18ccebceaa3a6a252c1ce8fc2c9aadc45e30dc439988a0c79c711d17`; the failed trial's scientific result SHA-256 is `e8fffadecadd807e5fef3d2b87119428e9e8d4618066cfb564ff85426bc3d458` and its specification SHA-256 is `7475b5ad61c584a6c1ce0f8dd8fef35bfdfd4448e94371c2bcc1f6156dc98d7a`.

These Windows process-tree observations are empirical samples, not a native allocation upper-bound proof. They do not qualify the ML VPS, its Linux process isolation, full workflow concurrency, disk budget, or submitted-user jobs. `resource_upper_proof=false` and `host_accepted=false` remain the controlling outcomes for both lanes. The failed sample must be diagnosed at its recorded solver stage without raising iteration or time limits or treating the diagnostic chord as the solver's direction.
