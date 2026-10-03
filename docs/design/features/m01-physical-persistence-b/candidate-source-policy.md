# Isolated physical candidate path policy

Status: CANDIDATE_ONLY. Registration: UNREGISTERED. runtime=false. No runtime/production source bundle is admitted by this record.

MAIN's [pre-code path amendment](candidate-path-amendment.md) derives this NEW policy from the unchanged historical migration-source-policy.md at447f29dc0c1ac97003ff8087ee1caa1e2e05a210. Exactly one substitution: app/migrations/candidates/0004_physical_persistence.py INSTEAD OF default versions/0004. No original A/B policy/receipt is overwritten. Exact revision/down_revision unchanged; activation/path mapping later requires independent review. Missing planned native/runtime source and unmeasured hashes remain UNREGISTERED; no fake whole-bundle completeness or future build tuple.

## Exact47 candidate source paths

```
app/__init__.py
app/alembic.ini
app/auth.py
app/bundle.py
app/compute.py
app/config.py
app/database.py
app/errors.py
app/formats.py
app/main.py
app/migrations/env.py
app/migrations/versions/0001_api_foundation.py
app/migrations/versions/0002_private_storage_permission.py
app/migrations/versions/0003_processing_jobs.py
app/models.py
app/mt_bundle.py
app/mt_compute.py
app/mt_contract.py
app/processing.py
app/processing_contract.py
app/processing_storage.py
app/projects.py
app/schemas.py
app/security.py
app/server.py
app/views.py
app/worker.py
data-pipeline/edi.py
data-pipeline/electromagnetics.py
data-pipeline/geology.py
data/fixtures/edi/halfspace-100-native.edi
data/fixtures/edi/two-layer-noisy-rotated.edi
tests/api/conftest.py
tests/api/test_online_mt.py
app/migrations/candidates/0004_physical_persistence.py
app/physical_contract.py
app/physical_persistence.py
app/physical_leases.py
app/physical_recovery.py
app/physical_compute.py
data-pipeline/gravity_processing.py
data-pipeline/gravity_station_adapter.py
data-pipeline/gravity_transforms.py
tests/api/test_physical_persistence_schema.py
tests/api/test_physical_leases.py
tests/api/test_physical_processing.py
tests/ops/test_physical_recovery_contracts.py
```

## Unchanged8 ops source paths

```
scripts/ops_recovery.py
scripts/ops_source_pin.py
scripts/ops_host_fixture.py
tests/ops/mt_drill.py
scripts/ops_physical_recovery.py
scripts/ops_physical_source_pin.py
tests/ops/test_physical_native.py
tests/ops/physical_drill.py
```

Only the eight NEW implementation/test files expressly approved are writable now. Other listed paths are frozen existing source or unimplemented future gated dependencies, not authorized edits. File/hash/count/Git-blob/module/DDL algorithms and limits remain the historical v2 contract. Candidate parsers may verify explicit fixture/source bytes but cannot issue a registered policy or runtime ACK. Actual tested candidate source hashes are separate evidence after validation; they cannot populate an approved native build or missing runtime file.
