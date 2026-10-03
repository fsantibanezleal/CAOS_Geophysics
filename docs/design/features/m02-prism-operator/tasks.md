# Pure forward amendment tasks and ownership

Status: planned, awaiting main's complete amendment read. No code authorization.

- [ ] Main reviews [typed protocol/design](design.md), [requirements](requirements.md),
  [locked gates/cases](validation.md) and [runtime/source pins](runtime-pins.json).
  Review 1..2048 receiver / 4096-cell cap, whole-box strict outside policy,
  float64 RAM engine, exact six-key result, Jacobian units and no-I/O provenance.
- [ ] Explicit main authority for ONLY `data-pipeline/gravity_forward.py` and
  `tests/numerics/test_gravity_forward.py`, plus this feature's own evidence/docs.
  Main owns source/runtime verification tooling outside the pure callable; no
  new source-audit tool or environment edit is authorized by this amendment.
- [ ] After authority: implement strict in-memory arrays/geometry, actual official
  engine call, copied immutable result and literal errors. No filesystem, CLI,
  GUI, callback/backend hook, legacy kernel or inverse integration.
- [ ] Execute all proposed gates locally and persist scoped actual receipts,
  source/runtime hashes, deterministic cases and negatives. No current numerical
  PASS label exists. Main independently repeats/reviews before code promotion.

This branch changes only `docs/design/features/m02-prism-operator/*`. PR120 head
`395459bb82cf221be132479358725ce76268ca93`, merged at
`bc0c573daa511ba897dd0b21e315b8c1eef67413`, remains unchanged. This is a separate
new review unit, not an appended change to PR120. Source pin acquisition was
read-only; no package or scientific execution occurred.

Broad [M02 plan](../m02-survey-inversion/tasks.md) survey key/types/enums/asset
binding, seeds/candidates/epsilon/null inverse policy and pinned optimizer stops
are still unresolved. Completing the ordinary forward operator would NOT
complete inverse, terrain/field admission, uncertainty, holdouts, UI/API/course,
host/GPU performance, full M02 or release. No main/deploy/canonical writes.
