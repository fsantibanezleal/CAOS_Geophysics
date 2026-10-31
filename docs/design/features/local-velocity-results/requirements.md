# Local straight-ray velocity result inspection

This is a separate public local-file channel for the actual velocity user-data
producer, not a project upload, server job, inverse or training implementation.

LVR-01 WHEN original result.json and manifest.json are selected, THE reader SHALL
check finite byte metadata before reading, strict UTF8/JSON depth/node/duplicate
keys, exact result SHA/length, closed schema, dimensions, units and identities.
Gate: frontend/src/test/velocity-local.test.ts malformed and hash controls.

LVR-02 IF validation or the selection lifetime changes, THEN THE view SHALL
discard that read, retain the last admitted result and label rejection; THE
channel SHALL make no API writes and require no account. Gate:
frontend/e2e/local-velocity-results.spec.ts public open/reject/reselect controls.

LVR-03 THE instrument SHALL link original ray IDs/endpoint geometry/declared
sigma, observed/final predicted/signed and standardized residuals, velocity
and path-length coverage on the explicit16x16,50m,positive-depth-down grid.
Gate: velocity-local.test.ts exact selected values and actual browser downloads.

LVR-04 WHERE a learned result exists, THE selector SHALL show its actual returned
model, checkpoint protocol/hash and domain flags, retaining the frozen negative
matched benchmark and all false field/heldout/online claims. Missing learned
arrays SHALL not be substituted with classical values. Gate: the same named
unit/browser gates with actual original and physics-v2 producer generations.

LVR-05 THE view SHALL distinguish byte binding and scalar consistency from
independent ray-operator/optimizer replay, coverage from uncertainty, clipping
from certified bounded optimum and cell/bilinear predictions from field truth.
Gate: velocity-local.test.ts false claims/metric/residual controls and browser
label/export assertions. The producer verify_generation remains the physics gate.

LVR-06 THE adapter SHALL reuse existing shared-shell/workbench/Heatmap/Plot
components, EN/ES, light/dark, physical readouts, pointer/keyboard controls and
local exact inspection export at1280x800,1600x900,2560x1440,390x844. Gate:
local-velocity-results.spec.ts complete viewport matrix; full Vitest/TypeScript/
build/content/artifact/phase/single-origin gates. No styles, course or engine edits.
