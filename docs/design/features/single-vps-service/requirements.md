# Single-VPS service release requirements

Status: planned

This refines approved R-017. It does not introduce another origin, SMTP, off-host backups or a production administration requirement.

SR-01 THE release builder SHALL admit only a clean, committed source and a structurally valid convergence ledger, and SHALL preserve the exact reviewed web bytes without building, downloading or computing. Qualification bundles SHALL NOT grant activation; activation SHALL require all scientific/UI requirements plus independent actual-host admission, and final acceptance SHALL require post-activation HTTPS/browser/rollback verification. Gate: tests/ops/test_service_release.py::test_release_admission.

SR-02 THE release builder SHALL inventory bounded regular runtime and web files, reject links, unsafe names, untracked runtime files and observed source changes, and write only an explicit new release directory. Gate: tests/ops/test_service_release.py::test_bundle_integrity.

SR-03 THE API SHALL receive HTTPS requests only through the existing Nginx origin and a permission-restricted Unix socket, and SHALL NOT expose private storage, source code or service secrets through the static root. Gate: tests/ops/test_service_release.py::test_service_boundaries.

SR-04 THE worker SHALL run separately from the API, without its auth secret, as an unprivileged single worker with whole-service cgroup limits and control-group shutdown. Gate: tests/ops/test_service_release.py::test_worker_isolation.

SR-05 WHEN a release is activated, THE installer SHALL refuse unexpected paths and schema drift, stop writes and the old worker before activation, verify API readiness, and restore the previous release and site configuration if activation fails. It SHALL NOT downgrade a database or delete project data. Gate: tests/ops/test_service_release.py::test_activation_and_rollback.

SR-06 THE capacity collector SHALL measure actual filesystem free bytes, MemAvailable and application releases; current plus two rollback releases SHALL be retained after qualified activation, with all additional targets individually verified before any removal. Gate: tests/ops/test_service_release.py::test_capacity_and_retention.

SR-07 IF any release, capacity, migration, readiness or verification check fails, THE deploy workflow SHALL retain its failure evidence and SHALL NOT report full acceptance. Gate: tests/ops/test_service_release.py::test_fail_closed.

SR-08 THE runtime stager SHALL rehash a supplied immutable bundle against an explicit manifest digest before installing an API-only environment, reject existing environments or receipts, measure available installation bytes, constrain installer process time/memory/output, and record installed dependency and file inventories outside the release. It SHALL NOT activate services, mutate private projects, install global packages or grant scientific admission. Gate: tests/ops/test_service_runtime.py.

SR-09 THE initial private-state bootstrap SHALL verify the exact staged bundle and runtime, exclusively create absent application state and literal service environments, migrate to the committed schema and provision the operator-supplied initial internal account as the service user. It SHALL refuse existing state or environment files rather than replace them, preserve partial failures, never print credentials, enable scientific engines implicitly or activate a service. Additional internal accounts SHALL remain available through the existing plural-account operator CLI. Gate: tests/ops/test_service_bootstrap.py and actual-host isolated qualification.

SR-10 THE isolated API qualifier SHALL reverify the non-active installed candidate and stable private configuration, start only newly named application-specific temporary systemd socket/service units with the production unprivileged restrictions and resource ceilings, exercise the actual Unix transport, and stop its own units on success or failure. It SHALL NOT change the active release, production units, Nginx, DNS, TLS or scientific flags. Its bounded receipt SHALL preserve exact source/runtime identities and actual measured service properties without environment values, cookies or passwords. Isolated transport success SHALL NOT grant scientific or complete-release admission. Gate: tests/ops/test_isolated_api.py and actual ML VPS execution.

SR-11 WHEN authenticated candidate qualification is explicitly selected by the operator, THE qualifier SHALL read only the bounded private owner credential file, provision a new uniquely named internal qualification account through the existing unprivileged anonymous-pipe helper, and exercise separate real sessions, CSRF/origin refusal, plural projects, immutable original upload/download/export, dataset construction and cross-owner404 boundaries. It SHALL retain the new qualification account credentials privately, never rotate or overwrite an existing account, and delete only the exact freshly created test projects after successful verification. Failures SHALL preserve identifiers and private bytes for inspection. No cookie/password SHALL enter command arguments, logs or result receipts, and API workflow success SHALL NOT qualify a worker or scientific method. Gate: tests/api/test_service_workflows.py and actual ML VPS execution.
