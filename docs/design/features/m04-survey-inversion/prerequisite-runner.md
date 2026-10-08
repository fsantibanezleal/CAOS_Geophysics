# Original nonzero prerequisite runner

Status: planned

R-449 IF the applicable public original terminal/optimizer sources match a
retained failed complete-firstfit receipt, THEN THE runner SHALL refuse all
dependent jobs without rerunning that unchanged failure.
Gate: tests/data/test_magnetic_prerequisite_gate.py::test_unchanged_public_failure_stops_before_launch.

R-450 WHEN a changed public source is explicitly pinned, THE runner SHALL run
only firstfold followed by complete-firstfit, halt on the first failure and bind
cache receipts to exact public/scientific/test source fingerprints.
Gate: tests/data/test_magnetic_prerequisite_gate.py::test_fail_first_sequence_and_exact_cache.

R-451 IF a source changes during the run or a cache is incomplete/altered, THEN
THE runner SHALL refuse reuse and SHALL not unlock a full matrix.
Gate: tests/data/test_magnetic_prerequisite_gate.py::test_changed_source_and_incomplete_cache_refuse.

The existing actual pytest numerical prerequisites remain authoritative. This
runner executes them, not a replacement optimum or model. The original120s,
200accepted,200CG and20LS scientific budgets remain inside the actual fitting
functions; an outer test-process timeout is not numerical acceptance. Whole
native containment/resource admission is still a separate prerequisite.

Input includes the external failed receipt and its exact SHA256, three explicit
local source roots (M04/public/M03) and external output/cache root. The public
proof-source change, not a client/wrapper/test edit, is required before launch.
Every actual source byte is hashed. Interpreter/thread settings are fixed for
the local gate; no fallback interpreter, relaxed tests or retry loop exists.
New jobs use fresh output paths, retain XML/log/result bytes and stop at failure.
Cache reuse requires exact inventory plus all retained output byte hashes.
Success only establishes the two local prerequisites, never field/full matrix,
native-host admission, method acceptance or deployment.
