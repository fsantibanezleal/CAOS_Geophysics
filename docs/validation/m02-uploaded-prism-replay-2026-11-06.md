# M02 uploaded prism replay acceptance — 2026-11-06

## Result

The selected owner-workbench browser run passed **2/2 tests** in 53.1 s. It
uploaded the fixed 144-station authored Choclo-prism control, validated its
physical metadata, ran the bounded local ordinary weighted-L2 child worker,
rendered the returned inversion, and verified its exported ZIP with the
independent Python bundle verifier.

The browser replay now explicitly moves the returned trace from its terminal
accepted iterate to its initial iterate. The accepted-state label changes,
the displayed objective and normalized KKT values change, and the captured
WebGL density-volume frames have different SHA-256 hashes. This tests that the
saved solver states reach the scientific result view; it does not run another
inverse when the user scrubs the trace.

## Reproduction

From `frontend/` on Windows:

```powershell
npx.cmd playwright test -c playwright.processing.config.ts `
  --grep "owner upload to flag result|authored prism upload" --reporter=line
```

The run used the loopback QA API and the local `.venv-gravity` worker. It did
not contact or qualify the VPS.

The application code under test was at commit `037aa0373f23ef94695ea4aaf7deb49513aa9c0f`.
The executed test file SHA-256 was
`847913fbdb9d42352b0cf982e66b0deb7a692502f93d2dcee210722b7b01924c`.

## Run measurements

| Quantity | Value |
| --- | ---: |
| Stations / withheld stations | 144 / 36 |
| Active cells | 48 |
| Fit status | converged |
| Child wall time | 35,077 ms |
| Peak RSS | 212,701,184 bytes |
| Scratch | 549,785 bytes |
| Configured wall / memory / scratch limits | 600 s / 2 GiB / 256 MiB |
| Preflight memory / scratch estimates | 628,684,560 / 16,785,354 bytes |

The receipt records `field_eligible=false`, `full_M02_accepted=false`, and
`host_accepted=false`. These are synthetic local-control results.

## Retained artifacts

The exact run receipt and browser evidence are outside Git under
`E:\_Datos\CAOS_Geophysics\validation\m02-replay-state-20261106\`. Their
byte counts and SHA-256 values are recorded in that directory's
`manifest.json`.

| Artifact | SHA-256 |
| --- | --- |
| Uploaded-job receipt | `3495c1f1f29fe1c84684e85714d912916951d85bc2482a75a66422e2e01f8fd6` |
| Verified result ZIP | `bc055ca9d1099ace4bf859e63b6f4170561641068d9306002d09f73952d36530` |
| Rendered result page | `e96320a085967b3abc87f81c16fc85215ba7af27dc3dd6b00a2cb0a7019d67ef` |
| Terminal accepted-state WebGL frame | `389e3b9780be3be58e7b67446b7f93cdf262fc97860ce62e8920aaf1fcff0e0a` |
| Initial accepted-state WebGL frame | `c27cd5f2a3d3cdce22f93e0099235904c5bb9c7b0eb3d436fb1aa18713f65ad9` |

## Acceptance boundary

This closes only the local authored-control upload, inverse, trace-replay,
render and export path exercised above. It does not establish field eligibility,
complete M02 acceptance, other uploaded modalities, VPS admission, product-wide
visual acceptance, or release readiness. The convergence ledger remains
authoritative and the broader M01–M13 acceptance gates remain open.

## Windows QA teardown rerun

After the replay assertions were retained, the loopback server gained an
explicit shutdown route. The owner suite posts to it after all selected tests;
the route stops the worker and signals Uvicorn to exit, allowing the server's
`TemporaryDirectory` context to remove that run's private files on Windows.
This avoids leaving the worker orphaned when Playwright terminates its server
process group.

The same two browser tests then passed again in **1.1 minutes**. The QA run
directory count was 37 both before and after, and no QA worker or server process
remained. The application code under test was unchanged at
`037aa0373f23ef94695ea4aaf7deb49513aa9c0f`; the follow-up test file SHA-256 is
`2e486eef077e91f25816d0f5c5a018e9605beb529d13533eabd4026b0328f3cf` and the
QA server SHA-256 is
`223ca38f657790019f9100ae34ec63fe59b46be824ce642189cf8594140fba47`.
The follow-up receipt, screenshots, ZIP, and their hashes are under
`E:\_Datos\CAOS_Geophysics\validation\m02-replay-state-20261106-cleanup-verified\`;
`manifest.json` binds these outputs and the process-cleanup observation.
