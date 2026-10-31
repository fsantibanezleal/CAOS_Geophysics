# M11 retained instrument provenance audit, 2026-10-31

## Finding

The retained M11 input fixture and the archived solver output do not form a
replayable pair. The browser and archive tests must not treat the archived
output as a valid state instrument or scientific result.

The selected input-matrix manifest has SHA-256
`946ca7904d5d9d063d0c3f57e1e78ffeb96453f04e4e9f25ff14601a746c659d`. Its
`joint-control-00` development input compiled to development identity
`56d8c70997a6e42e57b9533c7397e7b28f3fb7689c310b3119afd64ce429b2a4`.
The archived `workflow.json` beside the retained output binds a different
development identity, `99d074fcaf4ee6185ff52aeab318e9fc280176ced7877a3c3ca32b76a7a142a5`.
The retained output therefore cannot be paired with the selected input case.

The post-freeze instrument validator independently refuses the archived
calibration with `calibration: reviewed source/allocation drift`. No bypass,
refit, or compatibility exception was introduced. The failed and unresolved
state remains explicit: this is not a valid solver replay, field result, or
scientific acceptance.

## Reproduction and controls

- The 24-case retained intake manifest is external to the repository. Its
  exact file hashes were preserved when one case was copied to the configured
  external data root for replay; all 605 files and 386,672 bytes matched.
- The exact external intake configuration passed the frontend joint-input
  suite: 31 passed, 0 failed.
- With the retained failed Python API custody export also configured, the
  joint-input and custody suites reported 50 passed and 1 failed. The remaining
  test requires an actual successful native instrument archive, which is not
  present.
- The default full frontend run reported 380 passed, 23 skipped, and 36 failed
  because the external fixture environment was not supplied. This is not a
  passing suite.
- `scripts/export_joint_survey_instrument.py --help` is the supported CLI
  entry point. The underlying scientific module remains byte-identical to its
  pinned source so opening the CLI does not invalidate historical solver
  provenance.

The 2026-10-25 solver matrix records completed command workflows, but completion
does not repair the input identity mismatch or establish numerical precision.
Its scientific precision, field eligibility, and public activation flags remain
false. Rebuild the output from the exact current input and reviewed source set
before using this case as a state-instrument fixture. Until then, M11 and the
product release gate remain unresolved.

## Scope boundary

This audit changes no solver output and does not authorize native physical
worker integration, API activation, VPS deployment, or scientific acceptance.
