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

On the local CPython 3.12.10 Windows validation environment, the full M02 gravity-forward and M04 induced-magnetic-forward suites passed after aligning the disposable pipeline environment to the committed `pymatsolver==0.4.0` pin. New version-boundary tests accept the historical 3.12.10 runtime and the explicitly registered 3.12.16 candidate. This is local compatibility evidence only; the matching VPS 3.12.16 numerical replay remains pending.

The repository fixes for service-owned state validation, legal `+` characters
in runtime paths, and inclusion of the gravity audit pin are committed and
pushed in this branch. Regression tests cover those changes. The branch now
registers CPython 3.12.16 from a hash-pinned standalone distribution and adds a
private interpreter staging command. That new profile still requires host
installation, numerical replay, and fresh source-pin verification. The system interpreter must not be relabelled as 3.12.10. The first private 3.12.16 runtime receipt failed its installed-path identity check; the corrected versioned stager now records its final installed path. Candidate solver execution then exposed a separate hard-coded Python-version gate in the gravity and magnetic operators; explicit 3.12.16 compatibility was added, and fresh numerical replay is pending.
[Python 3.12.16 release](https://www.python.org/downloads/release/python-31216/).

## Release decision

No candidate passed the full host admission matrix. The production `current`
link and legacy site remain unchanged. The service runtime, isolated API
workflow qualification, seven host workload controls, whole-product
acceptance, and final deployment gate remain open. The convergence ledger is
still 1 failed, 18 unresolved, and 0 passed; this report does not change any
requirement verdict.
