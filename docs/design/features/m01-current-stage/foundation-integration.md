# Physical dataset foundation integration

The integrated foundation contains immutable root/child dataset relations,
correction and transform producers, retained-result accounting, project-wide
custody checks, writer participation and startup observation. These modules are
implementation components; their presence does not activate an online method.

The default migration remains `0004_waveform_artifacts`. The proposed
`0005_physical_forest` successor and historical alternative physical migration
are isolated candidates. An alternative `0004` is never placed in the default
registry. Project ownership and retained native records must survive the final
combined migration before that registry changes.

## Executed integration checks

The first integrated startup, incomplete/successful archive, accounting,
participation, security and project-route selection executed 131 tests with no
failures, errors or skips. A separate candidate/successor schema selection
executed 68 tests with no failures, errors or skips. Both used fresh external
test directories; neither opened a deployed database.

The incomplete-archive tests consume the hash-checked historical native recovery
receipt at its original source revision. They create new portable fixture copies
and do not reinterpret those copies as native filesystem qualification. The
startup observer rolls back its transaction and is not a lasting admission token.

These checks do not establish the final combined schema, all-writer native
assembly, bounded scientific child execution, complete uploaded-data workflows,
browser interactions or deployment acceptance. Those require the actual merged
runtime and separately executed release gates.

## Reproduction

Use the repository API dependency lock and a repository-local ignored environment.
Set the external authentic recovery receipt and the declared scientific test
interpreter using the fixture environment variables documented in the tests.
Keep test data, caches, XML reports and native records outside Git.

```text
python -B -m pytest -p no:cacheprovider -x \
  tests/api/test_physical_startup.py \
  tests/api/test_profile_incomplete_custody.py \
  tests/api/test_profile_incomplete_delete_barrier.py \
  tests/api/test_profile_archive_custody.py \
  tests/api/test_profile_archive_accounting.py \
  tests/api/test_physical_participation.py \
  tests/api/test_security.py tests/api/test_projects.py \
  --basetemp <fresh-external-directory> --junitxml <external-report>

python -B -m pytest -p no:cacheprovider -x \
  tests/api/test_physical_persistence_schema.py \
  tests/api/test_physical_successor.py \
  --basetemp <another-fresh-external-directory> --junitxml <external-report>
```

The source repository retains portable commands and explicit claim boundaries.
Machine-specific source pins, receipt locations and integration coordination are
kept in the private management repository.
