# Independent ordinary gravity forward review

MAIN read the complete narrowed feature design, implementation and tests before
accepting PR122. This is acceptance of a local forward operator only, not of the
submitted-survey inverse, field workflow, online worker or full M02 requirement.

Implementation review used detached `855f6d7343fce139aaf91ad8d7b85dd0eefa5b00`.
The final head `801955d0fe5faaa5c8d928816f722f2be712d43b` changes documentation
only. Operator SHA-256 is
`46d205a453147cc18697464e4a6deda2920d0d88307e366b6fd336d9a1ac07d5`;
test SHA-256 is
`c50158f083cba3ad096ff7b17eccdcbeb0a31f6e8293d13ffdccb3f6d78624c1`.
The three producer JSON receipts remain historical, not rewritten as MAIN runs.

## Independent actual execution

Existing numerical interpreters were used read-only: CPython 3.12.10, the pinned
pipeline runtime for the operator and the separately installed M01 runtime for
the correction regressions. No dependency installation, source rewrite, field
metadata substitution or automatic model/data regeneration occurred. Bytecode
was disabled, numerical thread counts were one, and all test/cache artifacts
used fresh private directories outside the product checkout.

| Actual selection | Result | Private JUnit SHA-256 |
| --- | --- | --- |
| All 80 new forward controls plus selected source/rebuild regressions | 118 passed, two skips, 11 deselected; 6.713 s | `658c87517ad0c741071578a7ac2968e99badd398ec325c3a547368b80eb3ba7c` |
| Unchanged correction, transform and station-adapter suites with the actual retained author archive | 165 passed, zero skips; 21.112 s | `b3b177b6f601a66edc58e85cb0ebf7e757390c0368b0d1c131a16848b33d0bb8` |

The first selection skips only the opt-in source archive and the unavailable
Windows symbolic-link privilege; its junction control remains executed. The
second selection explicitly supplies the original archive to the author-source
negative gate. That physically ineligible source is not admitted by these passes.
The command selections and frozen gate policy are in the
[operator validation record](../design/features/m02-prism-operator/validation.md).
MAIN additionally verified all 20 actual module/native hashes and eight package
versions against the external source manifest, SHA-256
`a5aa08c23a80e15024e6499fab6805315d52dee185c5de1010b5f46e5c9f5819`.
This checks selected runtime identity; it does not authenticate a supply chain.

## Additional independently authored physical control

MAIN added a control outside the repository, distinct from the producer's fixed
cases. It uses an 18-cell nonuniform 3 by 2 by 3 tensor mesh:

- Origin east/north/up: (-600, -400, -500) m.
- Widths: hx=(80,120,200), hy=(150,100), hz=(90,130,70) m.
- X-fast active indices: (1,5,7,12,17); contrasts (200,-350,800,-150,500) kg/m3.
- Receivers: (-500,-200,100), (-250,-450,50), (-650,-100,-300), (100,-500,500) m.

Each active physical bound was derived independently by nested x/y/z indices,
not recovered from the production Jacobian. Choclo's upward prism function was
evaluated separately at density one for every receiver/column, then converted
from SI acceleration to mGal. A second oracle integrates
G rho (z_source-z_receiver)/distance^3 over each physical volume, with
G=6.67430e-11 SI and Gauss-Legendre orders 4, 8 and 16 in every axis.

Production upward g_z (mGal), in the declared receiver order, was
(-0.07061767694485668, -0.06367932018759405,
-0.017060869410283536, -0.012165262442002885).
Maximum Choclo prediction discrepancy was 6.166941957097549e-15 mGal;
maximum Jacobian discrepancy was 1.5175442283008045e-17 mGal/(kg/m3).
Maximum volume-oracle discrepancies at orders 4/8/16 were respectively
1.0931827276738915e-8, 6.689093723366568e-15 and
6.682154829462661e-15 mGal. The predeclared Choclo rtol1e-7/atol1e-10
and volume-oracle relative1e-5 gates passed without relaxed tolerances.
Private authored helper SHA-256:
`f23889a54412050d89d18fc553a958fc60186b653cc02b104c965200bfd77e09`.

An initial surrounding PowerShell hash-display command failed on its argument
binding after the numerical helper had passed. The unchanged helper was rerun,
then the explicit `-LiteralPath` hash command succeeded. This shell diagnostic
is not relabelled as a numerical failure or hidden by the later successful run.

## Geometry and integration limits

At very large translated origins, nominal positive widths can collapse, centres
can land on faces, or actual mesh widths/volumes can differ from requested ones.
The operator checks actual engine node/corner/centre/volume geometry using a
separate relative local-width/volume budget1e-10, not a tolerance proportional to
the absolute origin. This budget does not weaken any prediction tolerance.
The initial suspicion that pinned SimPEG calculated G from centre-plus-half-width
was rejected by reading its actual node-based implementation and executing it.
The retained evidence supports geometry-fidelity rejection, not that false G bug.

PR122 merged to `9fac552cf844bfa1ca38e5242d7f1f653abc2c92`.
CI37117384343 failed the existing base-integrity guard because two documentation
recipes contained absolute machine paths. The numerical/source receipts were
unchanged. Independently reviewed docs-only PR128 made those recipes portable;
merge `1b112bb258520a5679a865335cec30b6a97a1a0d`, CI37117994883 succeeded.
No guard, scientific threshold, source/test file or historical receipt was changed
to obtain that pass. The red integration result remains part of the record.

Only the exact Windows CPU/float64/RAM ordinary lane is accepted here. The
64-MiB maximum Jacobian is not a measured whole-process RSS ceiling. Linux,
GPU, observations/errors, L2/IRLS, holdout selection, geological recovery,
scientific eligibility, API publication and actual-host admission remain pending.
The full product ledger retains its unresolved/failed verdicts.
