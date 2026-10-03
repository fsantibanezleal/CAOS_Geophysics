# MT bundle residual identity requirements

Scope: strict private M06 bundle re-import only. The original Linux receipts are immutable and remain private. No solver, canonical result, resource admission or release gate changes.

- BP-01 WHEN an independently computed forward prediction differs only in binary64 rounding, THE verifier SHALL verify the stored prediction against physics and the residual against the exact stored prediction, not a second platform's prediction.
- BP-02 WHEN a prediction or residual is scientifically altered and all content hashes are recomputed, THE verifier SHALL reject it.
- BP-03 THE verifier SHALL retain existing model bounds, uncertainty, ownership, canonical-byte, tensor and hash checks.
- BP-04 THE implementation SHALL independently re-import all five actual Linux control ZIPs without publishing private artifacts or substituting fixture successes for host evidence.

Gates: tests/api/test_online_mt.py near-zero residual and rehashed corruption controls; existing API regression; independent actual-host ZIP verifier invocation.
