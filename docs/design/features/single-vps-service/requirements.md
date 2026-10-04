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
