# M12 protocol launcher: actual CLI forwarding receipt

Date: 2026-10-27. Scope: launcher custody and child-argument forwarding only.
This receipt is not M12 model validation, acceptance, or GPU training evidence.

## Focused controls

Command:

```powershell
$env:TMP = 'E:\_Temp\CAOS_Geophysics\pytest-m12-launcher-20261027-bcbaadf'
$env:TEMP = $env:TMP
$env:CAOS_TEMP_ROOT = $env:TMP
.venv-pipeline\Scripts\python.exe -m pytest tests\ops\test_m12_launcher.py -q --basetemp "$env:TMP\pytest"
```

Result: 26 passed, zero failures/errors/skips. The suite executes refusal cases
through the CLI, checks PowerShell and Bash boundaries, and verifies exact argv
forwarding for both protocols. Child argv is mocked for the unit-level exact
forwarding assertions; the next control independently invokes the real child.

## Actual frozen physics-v2 fixture forwarding

Command:

```powershell
.venv-pipeline\Scripts\python.exe scripts\run_m12_velocity.py `
  --output 'E:\_Temp\CAOS_Geophysics\m12-launcher-physics-fixture-20261027-bcbaadf' `
  --protocol physics-v2 --device cpu --fixture
```

The wrapper launched `velocity_physics_refinement.py`, which executed one
authored fixture epoch and wrote its checkpoint and receipt outside Git. The
receipt says `fixture-only`, device `cpu`, one epoch, and retains the failed
fixture comparator ratios (model 3.5458233, forward 12.7277058). It cannot be
used to infer the full 40-epoch result.

Evidence hashes:

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `m12-physics.npz` | 121,158 | `b7c63caf529807a5e6775550e2962518d805f2b77e9aaf566fd5317178578d3e` |
| `receipt.json` | 60,655 | `c9664913123f693aa36f3d68b1eb68b39ed5bf5a05eb6b0c8a972e086e99e29d` |

The exact code identities recorded in that receipt were confirmed against the
working tree:

| Source | SHA-256 |
| --- | --- |
| `data-pipeline/velocity_physics_refinement.py` | `99f1b079774709143debf0702059108acb7a6d18f3364404f791124053b5a460` |
| `data-pipeline/velocity_validation.py` | `2b9ed95d3ba7b1b0f9f80167fa610640dc75c8a142dafb9f7f09791b96a1fd44` |

The runtime recorded Python 3.12.10, NumPy 2.2.6, SciPy 1.15.2 and Torch
2.14.0+cu126. Although this wheel supports CUDA, the actual fixture was
explicitly run on CPU.

Running the same wrapper with `--protocol physics-v2 --verify` exited 1 with
`Fixture does not qualify the full experiment`. This is the expected safety
boundary, not a failed full-experiment verification. Earlier source-frozen
inventory validation still has its own retained MemoryError and remains
unqualified; this launcher receipt does not replace it.
