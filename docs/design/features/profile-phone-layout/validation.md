# Protected profile layout and verification

The profile workbench composes the public shared shell's `WorkbenchLayout`,
`PlotCard` and measured `Stage`. The existing method selector is the sole
cross-method navigation control when the shared owner workbench is mounted.
Standalone consumers retain their callback buttons. No product fonts, theme
overrides, reserved-class overrides or replacement shell are introduced.

## Physical drawing contract

The result displays the returned native triangular cells, not an interpolated
raster. Both axes use the same physical scale in metres. Selected acquisition
sensors are noninteractive overlays, so they cannot intercept cell selection.
The keyboard arrows inspect adjacent native-cell indices. Colour limits only
change the display; they do not change the solved model or its uncertainty.

Native mesh and measurement curves are alternative instrument views. Processing,
resource and export controls live in the rail's disclosure. Row, cell, fit,
coverage, display and inspection controls live in a separate disclosure. A new
result SHA remounts the inspection state. Original observed/predicted arrays and
signed residuals remain available, as do QC and held-out test records.

The replay lane describes browser inspection of a stored result, including a
result originally computed by a protected server worker. It does not claim that
the solve runs in the browser. Real-source provenance does not establish field
geology or measured error covariance.

## Executable verification

`frontend/src/test/project-instrument-mount.test.tsx` verifies one owner rail,
the common method selector and retained standalone callbacks.
`frontend/src/test/foundation-routes.test.ts` verifies the exact shared-shell
consumer pin, product metadata, containment and the single-origin route contract.

`frontend/e2e/protected-profile-results.spec.ts::owned_result_roundtrip` uses
the actual authenticated API with explicitly supplied external ERT/traveltime
snapshots and producer records. It does not intercept API responses or rerun
solvers. It exercises both methods, EN/ES, light/dark and desktop/phone sizes:

- The exact native-cell count, pointer-centroid selection and keyboard selection.
- Original measurement-row inspection and exact inspection JSON export.
- Verified result ZIP download and reopening against the selected job.
- Cross-method navigation with project identity retained.
- No page errors or horizontal overflow.
- The installed shared gate's unchanged drawing floors: painted bounding extent
  at least 30% of the clipped stage, and qualifying drawn-view union at least
  50% of the viewport.

The last measurement is an enclosing instrument area, not coloured-triangle
coverage. A physically shallow profile remains shallow on a narrow phone;
stretching or cropping geology to pass a drawing-area gate is not permitted.
The test writes screenshots, drawing measurements, inspection JSON, ZIPs and
outcomes to the required external evidence path. Configure all case, build and
output paths through the `GEOPHYSICS_PROFILE_*` environment variables named in
the test. Never store private snapshots or generated QA evidence in the repo.

These controls qualify this consumer layout, not solver correctness, crash
recovery, other viewport/font combinations, every result state or deployment.
Those retain their own independent acceptance gates.
