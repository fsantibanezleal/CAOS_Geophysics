# Geophysics continuation checkpoint, 2026-10-03

Observed at 19:30 UTC. Status: INCOMPLETE, NOT RELEASED, NOT DEPLOYED.
This is a preservation and validation checkpoint, not product acceptance.

## Integrated repository state

Live `git ls-remote` verification during this checkpoint found product develop
at `e8a2971b5a8d0f2578c434616be902d2afce3893` and main at
`39813230478ed53bf5eb29cc21f07ed568767c64`.
[Product PR144](https://github.com/fsantibanezleal/CAOS_Geophysics/pull/144)
and [management PR798](https://github.com/fsantibanezleal/CAOS_MANAGE/pull/798)
were merged as scoped documentation checkpoints earlier in this continuation.
Neither merged checkpoint marks the replacement product complete. The approved
destination remains one ML VPS, with no duplicate final deployment.

## Independent course numerical execution

MAIN independently executed the committed course tests in a separate detached
checkout of `47efb36f72be02ca297b5096a0681ab5e47b857c`, using the existing
course owner's exact scientific environment read-only. Test-source SHA-256:
`556231885c49005ddf2a6f15804df96ed2db6f508b809a70cbef6272dff4fd81`.

```text
python -B -m pytest -q -p no:cacheprovider tests/test_m01_scientific_course.py
  -k 'not explanatory_controls_not_physical_jobs and not shared_shell_and_scoped_mount'
  --basetemp <new-private-QA-directory>/pytest
  --junitxml <new-private-QA-directory>/numeric.xml
```

Actual result: 12 passed, 0 failures, 0 errors, 0 skips, 32.680 seconds.
The two frontend source gates were explicitly excluded, not passed. The private
JUnit receipt is 1,725 bytes, SHA-256
`2b8f370a83056ba26149e849915828f8cd54e3dffe7ffb81cea2da49309dd160`,
last written at 16:41:37 UTC. Bytecode and pytest cache were disabled; numerical
threads were one and the numerical cache/test outputs used the new private
directory. The reviewed source tree remained clean after execution.

These tests check correction formulas, supplied datum/terrain and covariance,
independent prism integration, equivalent-layer kernel/regularization,
training-only selection, masks/continuation/residual sign, exact three-case
record identity and replay, user-file identity, bilingual document/figure
structure, negative inputs and authoring boundaries. They do not establish
integrated browser acceptance, original field validity, full M01 acceptance,
native online admission or deployment. The original exporter bytes and failed
historical gates were not rewritten.

## Preserved implementation snapshots

The following are LOCAL committed snapshots observed during the preservation
audit. Their dirty successors remain in their respective isolated working trees;
they were not swept into a commit or merged as accepted code.

| Slice | Local committed snapshot | Remaining working-tree content / acceptance |
| --- | --- | --- |
| M01 course | `47efb36f72be02ca297b5096a0681ab5e47b857c` | Four new frontend files, updated course tests and three new QA receipts; source review, serving/mount integration and rendered QA unfinished. |
| M02 bounded L2 | `80db6294602d252a9c7f1c164fabf821faa7be4a` | Two modified test files for the approved binding-set policy; actual cpu-3 implementation and complete acceptance unfinished. |
| M03 magnetic lines | `4eeed075f10f56d95919be30afe6cee424a10515` | Initial parsing/geometry authority recorded; local scientific implementation not accepted. |
| M08 waveform | `b2611adcd702f704486590f5c00bfc57c25ecedd` | Four modified scientific/test files after the committed candidate; full stable independent review unfinished. Eleven older MT diagnostic directories remain protected. |
| Physical persistence | `94272ff9d0ecf4f49700b068aed102f1619dc34f` | Five new B-data source/test files, modified environment evidence and a new regression receipt; WAL/native/recovery and full implementation gates remain closed. |
| Native controller | `4ecb0e605cebede8f51be5d246624249cf22f1c7` | Modified own contract and three new deterministic test files; core/probe source, compiled execution and platform admission not accepted. |

The exact-zero cpu-2 L2 milestone remains known incomplete: the supplemental
24-start controls produced 23 passes and one genuine near-zero-free-gradient
failure. The separately approved cpu-3 binding-set proposal does not convert
that failure into a pass before new execution and independent verification.

The persistence owner's new API environment regression receipt reports
120 passed, 3 failed and 4 skipped in 1,117 seconds, with no exclusions. This
producer report was read but not independently replayed. Its three failures
include two missing PID files in unchanged timeout controls and one M05
job-timeout failure. Skip applicability was not captured by that command.
Do not describe the full API baseline as green. SQLite3.49.1 has not been
admitted to the new physical WAL profile; its supported registry remains empty.

[M04 PR147](https://github.com/fsantibanezleal/CAOS_Geophysics/pull/147)
contains the seven-document induced-prism specification at
`67e38a190e5d0fac141a91e92361b14828354918`. Independent scientific peer review
and forward implementation remain pending; the draft is not a release.

## Operational observations and external holds

MAIN made read-only SSH observations of the ML VPS during this continuation.
The selected compiler/header/libc hashes and cgroup inventory are inputs for a
later native review, not an approved delegation, loaded-runtime or ABI proof.
The Geophysics application unit queried was not registered. Root free space was
23,599,362,048 of 80,290,492,416 bytes, below the unchanged 30% threshold.
No service, nginx, DNS, Pages, live release or production private state changed.
Headroom remediation authority, production SMTP and trusted off-host deletion
authority remain separate unresolved release prerequisites.

All six parallel workers returned an account usage-limit error at the final
coordination check. No replacement workers were spawned to evade that limit.
Their source, dirty changes, ignored environments, raw originals, failed
receipts and private QA outputs remain in place. A later continuation must
review each exact final source/test/evidence pin and preserve dirty successors
before resuming; it must not infer completion from this document, a draft PR,
file presence or the passing twelve-test course subset.
