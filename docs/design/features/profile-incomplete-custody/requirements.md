# Incomplete profile custody requirements

Status: implemented candidate; portable controls validated, native/integration gates open

This additive repair does not change successful execution, cancellation, paired
result validation or profile-retained-stage/v2. A missing execution receipt is
not evidence of successful execution, cancellation, resource enforcement or
original-input re-verification.

1. WHEN launching a new owned profile, the root supervisor SHALL persist an
   exclusive, immutable, fsynced custody intent before making its UUID directory,
   binding the already-held ordinary stage identity, complete installation and
   owned request/input identities. Gate: prelaunch ordering and drift controls.
2. BEFORE starting the guardian or submitting science, the supervisor SHALL
   persist a separate closed custody manifest of held root directory and known
   copy identities. Gate: manifest-before-launch source and failure controls.
3. WHEN recovering missing-receipt debt, the supervisor SHALL accept only a
   canonical UUID, the original historical authority and current independently
   checked owned failed/cancelled relations with the same installation. Gate:
   closed-schema, foreign relation, installation and legacy-plan negatives.
4. BEFORE inspection, before unlink and before returning recovery evidence, the
   supervisor SHALL freshly prove both deterministic service/scope inactive and
   both kernel groups absent or recursively unpopulated with no direct processes.
   Recovery SHALL NOT stop, signal or adopt live work. Gate: either-group negatives.
5. WHEN any identity, owner, link, member, hash or scratch check fails, recovery
   SHALL retain debt unchanged. It SHALL remove only manifest-declared root
   copies and empty pinned directories, journalling intent before mutation.
   Gate: replacement, extra member, nonempty scratch and interrupted replay tests.
6. WHEN the same pinned ordinary stage survives, ordinary recovery SHALL archive
   its bounded declared partial evidence (including an empty stage), with a new
   closed incomplete schema, exclusive intent, fsync and no-replace rename under
   the existing worker singleton. It SHALL preserve job state, original data and
   derived results. Gate: empty/partial stage, identity and rename replay tests.
7. WHEN historical debt lacks the new authority or a crash precedes the complete
   custody manifest, recovery SHALL refuse without retrofitting authority. Gate:
   all incomplete prelaunch windows and historical v1 plan controls.
8. The M01 descriptor consumer SHALL distinguish this incomplete schema and exact
   ownership/installation/manifest/member charge from execution-v2. Unknown
   integration SHALL refuse before deleting originals. Gate: parent integration;
   not established by this leaf's portable tests.
9. WHEN the ordinary recovery helper times out or its caller is cancelled, the
   caller SHALL retain its singleton/common-lease lifetime and held descriptors
   until the exact created helper is confirmed exited and both bounded streams
   drained. Repeated cancellation SHALL NOT interrupt that barrier. Overflow
   SHALL be discarded without unbounded retention while draining, then refused;
   no receipt or successful cleanup is invented. Gate: actual bounded child,
   singleton exclusion, timeout/repeated cancellation and overflow controls.

Actual privileged observer-kill, both-group extinction, ordinary archive/restart
and independent resource/cancel qualification remain separate native gates.
