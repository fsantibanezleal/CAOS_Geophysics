# Independent local recovery-adapter review

Reviewed ops source: `fb3895effc7de04c35aa1bed9c3295a354952729`, detached read-only worktree. Reviewed MT runtime: `59f46c5`, separate read-only parity worktree. Main independently ran the complete ops suite using the existing isolated MT interpreter, a newly allocated external private temporary root, no bytecode output and an external test cache. No user key, production state, existing backup or other environment was modified.

```powershell
$env:GEOPHYSICS_OPS_MT_CHECKOUT='D:/_worktrees/geophysics-mt-bundle-parity'
$env:PYTHONDONTWRITEBYTECODE='1'
# $opsPinnedTemp was a NEW short external directory, never reused.
D:/_worktrees/geophysics-ingestion-foundation/.venv-online-mt-oct3/Scripts/python.exe -B -m pytest tests/ops/test_backup_mt.py tests/ops/test_backup.py -q -ra -o addopts= --tb=short --basetemp "$opsPinnedTemp/p" -o "cache_dir=$opsPinnedTemp/cache" --junitxml "$opsPinnedTemp/ops-pinned-review.xml"
```

Measured result: **122 passed, one skipped, 157.22 s**, exit 0. The skip is ordinary Windows symlink-creation privilege; no MT or deletion scenario was skipped. The existing upstream TestClient deprecation warning remains. Restricted JUnit SHA-256 `0780bbcbbb62dfce7a370acfd387d8a12fafbf198dd995efe93013e4069ec695`. Reviewed `scripts/ops_recovery.py` SHA-256 `e3ccf805d3eb1e2979923f7a58fbd5e465ad7090a2710fb52dc067a285ce42a4`; pinned `tests/ops/mt_drill.py` SHA-256 `11c74f89f3b22259a8672c6fde60224110c012da6d127023e0e89955265c9d60`.

The tests use actual authenticated original EDI uploads, actual M05/M06 worker outputs and gravity QC, then native age encryption and new-target restore. After actual API deletion, the latest cumulative authority prevents that project from returning from its older snapshot, preserves survivor hashes and runs the application's candidate startup audit. Rehashed hostile schema/ownership/parser/method/parameter/shape variants are rejected independently of byte-integrity checks. Main reviewed strict exact DDL, bounded inventory, tar preflight, private path checks, coherent maintenance and independently latest-authority requirements.

An earlier independent run against the active ops worktree also passed 122/one skip in 160.37 s, but its fixture producer was being legitimately extended for the next host unit. It is not used as the pinned acceptance run above. That extension remains separately owned/reviewed; no mutable-source result is substituted for exact-source verification.

This accepts the local standalone adapter in [PR #102](https://github.com/fsantibanezleal/CAOS_Geophysics/pull/102), not whole-product release. Actual-Linux new-target recovery remains pending. The current deletion API has no synchronous independently durable off-host authority; loss after deletion but before checkpoint remains an explicitly open release gate. The actual MT host admission still fails its unchanged disk requirement. No new API activation, nginx/DNS/Pages change or deployment occurred.
