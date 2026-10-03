# Prediction and residual are separate identities

Observed halfspace Linux-to-Windows prediction differences are at most 2.78e-17 ohm (relative 1.52e-16); layered differences are at most 8.33e-17 ohm (relative 5.11e-16). A halfspace residual is close to zero, so comparing it against observed minus another platform's rounded prediction amplifies cancellation under the existing 1e-19 absolute allowance. The stored prediction and residual are internally consistent.

Validate the stored real/imaginary prediction against the independent layered recursion with the unchanged existing tolerance. Then compute observed minus the already-validated stored prediction and check the stored residual with the unchanged tolerance. This verifies the actual exported residual definition and does not broaden the physics tolerance or replace it with observational uncertainty. Shape/finiteness validation must happen before subtraction. No refitting, rounding or mutation of stored outputs is permitted.

The test constructs one-ULP shifted exported predictions and their exact residuals from an actual locally computed API result. It then rehashes separately corrupted predictions/residuals to establish semantic rejection, not just hash rejection. Actual Linux ZIPs provide separate cross-platform evidence.
