# Independent recovery fixture and selected-source review

Main reviewed the Linux-only fixture harness, selected-source verifier, requirements/design, producer extensions and their tests at `5bc20eb3253c88c0cd903ccf06fc42aeb2a26b77`. A detached review checkout and a separate fresh clean runtime checkout at `59f46c5a945531e573ae6db611a1f860237e3ba5` were used. No existing runtime environment, private original, API/worker/migration or core recovery code was modified.

The existing online-MT interpreter was used read-only with `-B` and `PYTHONDONTWRITEBYTECODE=1`. All keys, database/raw/result state, copied source, selections, archives, caches and receipts were generated in one new short external temporary directory. No pre-existing key, backup or user state was deleted. The fixture's deliberate deletion exercises only its newly created disposable API project, retaining exact surviving hashes.

## Independent result

`python -B -m pytest tests/ops -q --override-ini=addopts= --tb=short --basetemp <new-external-root>/p -o cache_dir=<new-external-root>/cache --junitxml <new-external-root>/ops-review.xml`

Result: **180 passed, two Windows symlink-privilege skips, one upstream Starlette/TestClient deprecation warning, 282.70 s**. The independent private XML has SHA-256 `20f7bf3f9deadf7060248fc77afdbf62e40f19d32e15a53b57f67e657eca9179`. Afterwards the fresh runtime's tracked, untracked and ignored Git status remained empty.

This includes original gravity/security/strict-MT recovery, real same-platform API fixture creation/deletion, source/DB identity controls, bounded orchestration failures, selected USTAR/header/member/tree/hash/commit/path/link controls and archive-mode preparation/audit. Explicitly controlled Linux/systemd responses in local tests are not relabelled as an actual Linux drill.

## Preserved operational boundary

The harness never installs code or binaries, mutates services, changes Git trust, activates production or lowers headroom. It requires a new private fixture root, exact pre-masked dummy units, pinned age binaries and either clean reviewed Git or an independently trusted selected-source manifest. The archive route rejects undeclared source and unsupported tar metadata, rechecks code before/after child work and keeps interpreter/environment provenance separate.

PR #112 was promoted to develop after this independent local review. **Actual-host execution is not run.** The unchanged 30% free-disk threshold remains unmet by the measured 29.42% receipt. Dummy-unit checks do not establish production quiescence. Local fixture tombstone authority is not independently latest or externally durable production authority. Production key escrow, deletion acknowledgement durability, actual-user restoration, resource/service admission and complete product release remain open.

The subsequent Git-blob-only source-bundle builder is a separate feature and was not part of these 180 tests. Its design approval cannot be used as a built/installed source archive or Linux execution receipt.
