# ML VPS candidate runtime qualification: 2026-10-27

This records bounded host evidence for the replacement candidate. It is not
release acceptance, scientific admission, or a deployment receipt.

## Live site and retained releases

- The existing site origin remains `https://geophysics.ml.fasl-work.com`.
- The `current` link remained `/var/www/geophysics.ml.fasl-work.com/releases/20260926235216` throughout these checks.
- The current release and two preceding dated releases remain present at 816,111,047; 816,120,188; and 686,433,273 logical bytes.
- `geophysics-api.socket`, `geophysics-api.service`, and `geophysics-worker.service` were inactive before and after qualification. No service was started and no database operation was run.
- At the final read-only snapshot, the filesystem had 25,711,915,008 available bytes and `/proc/meminfo` reported 5,166,000 KiB `MemAvailable`. The host's `/usr/bin/python3` is CPython 3.12.3.

## Recovered candidate configuration selector

The root-owned `/etc/geophysics/api.env` and `worker.env` still matched the
SHA-256 and byte lengths in the historical successful bootstrap receipt
`bootstrap-837c154-actual/bootstrap.json`. The active static release had no
release-specific selector directory, so the candidate workflow could not
stage a replacement environment.

Created `/etc/geophysics/releases/20260926235216` with byte-identical copies
of those two receipt-verified files, mode 0600, under a mode-0700 root-owned
directory. The `current` link, global environment files, private database,
and active services were not changed. Subsequent candidate environment
staging succeeded using this selector.

## Candidate outcomes

All following candidates are qualification artifacts under `releases/`, not
live releases. Failed candidate files and private evidence were retained.

| Candidate | Exact result |
| --- | --- |
| `release-0b2ea33` | Interrupted directory transfer; incomplete artifact, never run. |
| `release-0b2ea33b` | Bundle extracted and verified; original environment staging helper rejected the service-owned data-root owner. |
| `release-94ad4f4` | Environment staging passed. API runtime installation and `pip check` passed; runtime inventory rejected valid `tzdata` entries such as `Etc/GMT+10`. |
| `release-92e53bd` | API and gravity packages installed; both `pip check` steps passed. The gravity audit pin file was absent from the release inventory. |
| `release-d576a9d` | Bundle and environment staging passed; API and gravity packages installed; both `pip check` steps passed. Gravity source audit rejected host CPython 3.12.3 because the approved Linux runtime pin requires CPython 3.12.10. |
| `release-5355478` | Full bundle manifest verified on the VPS. Pinned CPython 3.12.16 archive hash and runtime probe passed, but the receipt recorded the temporary extraction path instead of the final path. This runtime was not passed to service staging or used by the app; retain it as failed qualification evidence. |
| `release-ca9e2c1` | Full bundle manifest, corrected private CPython 3.12.16 runtime and candidate environment selectors verified. API and gravity dependencies installed and both `pip check` steps passed; external gravity source audit passed. The final gravity forward probe rejected 3.12.16 because the in-repo operator still hard-coded 3.12.10. Candidate runtime staging failed, no runtime receipt was admitted, and no service started. |
| `release-b544af1` | Bundle, private runtime and environment selectors verified. API/gravity dependencies, both `pip check` steps and the installed-source audit passed. The final workspace-closure probe rejected 3.12.16 because `gravity_l2_metric.py` still hard-coded 3.12.10. No runtime receipt was admitted and no service started. |
| `release-37f1883` | Bundle, private runtime and environment selectors verified. API/gravity dependencies, both `pip check` steps, installed-source audit and both scientific runtime guards passed. The release harness then incorrectly asserted a return value from the workspace-closure validator, which validates by raising and otherwise returns `None`. This harness defect caused failure before runtime receipt; no service started. |
| `release-033a5e7` | Candidate runtime and source receipt staged successfully. The fresh Linux CPython 3.12.16 replay passed 381 tests with zero failures or skips in 10,793.32 seconds. This is numerical compatibility evidence only; host admission, API/worker job controls and full product acceptance remain open. |
| `release-9d203f1` | The corrected v2 bootstrap verifier was exercised read-only against this fresh candidate. It correctly found a 5,119,892-byte runtime receipt rejected by the shared 4 MiB JSON manifest limit; no `/var/lib/geophysics` state/database was created and the active release remained unchanged. A bounded 16 MiB parser option and regression test are now implemented; a new immutable candidate must replay the verifier. |
| `release-8f192e8b` | Fresh read-only bootstrap verification correctly rejected the shared CPython r2 runtime because its tree no longer matched its immutable receipt (163 generated `.pyc` files across 22 cache directories; expected 4,732 entries, observed 4,913). No database/state was created and `current` remained unchanged. A controlled clean-runtime clone completed the exact gravity dependency installation with bytecode writing disabled and preserved its receipt. The source now registers a new immutable r3 runtime and verifies the private interpreter receipt before and after candidate dependency installation; qualification remains pending. |

On the local CPython 3.12.10 Windows validation environment, the full M02 gravity-forward and M04 induced-magnetic-forward suites passed after aligning the disposable pipeline environment to the committed `pymatsolver==0.4.0` pin. New version-boundary tests accept the historical 3.12.10 runtime and the explicitly registered 3.12.16 candidate. The fresh VPS CPython 3.12.16 replay for `release-033a5e7` also passed; its exact command, overlay digest, runtime receipt digest, test count and runtime are recorded in [the replay receipt](vps-science-replay-033a5e7-2026-10-27.json).

The repository fixes for service-owned state validation, legal `+` characters
in runtime paths, and inclusion of the gravity audit pin are committed and
pushed in this branch. Regression tests cover those changes. The branch now
registers CPython 3.12.16 from a hash-pinned standalone distribution and adds a
private interpreter staging command. Candidate `release-033a5e7` passed dependency installation, source audit, runtime probes and the fresh numerical replay. The system interpreter was not relabelled as 3.12.10. Earlier failed receipts and hard-coded version gates remain documented above; the corrected versioned stager records the final installed interpreter path.
[Python 3.12.16 release](https://www.python.org/downloads/release/python-31216/).

## Release decision

No candidate passed the full host admission matrix. The production `current`
link and legacy site remain unchanged. The service runtime, isolated API
workflow qualification, seven host workload controls, whole-product
acceptance, and final deployment gate remain open. The convergence ledger is
still 1 failed, 18 unresolved, and 0 passed; this report does not change any
requirement verdict.
