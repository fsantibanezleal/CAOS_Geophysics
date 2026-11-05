# M02 result inspection tasks

Status: approved scope; local native projection and its strict TypeScript wire
parser are implemented and focused gates pass. API, worker, UI, refit/evaluation,
browser, host, and activation gates remain open. Do not represent these leaf
gates as full inspection or product acceptance.

1. Review wire, normalized dataset and existing worker/result dispatch with the
   controller; agree method IDs and explicit source/host admission. MV-06/07/12.
2. Implemented local `gravity_survey_view.project_verified_calibration`: whole
   native calibration replay precedes projection; L2, legacy IRLS stage books,
   and corrected CPU2 pooled fits retain actual frame history, all 8 candidates
   and 24 folds, physical bounds/units, development-only predictions/residuals,
   explicit hashes and false scientific claims. Five focused native tests pass
   on actual authored workflows, including no-optimizer inspection and tamper
   refusal. This remains a local leaf; bounded worker integration is pending.
   MV-01/02/03/04.
3. Added closed TypeScript wire parsing and six adversarial parser tests; focused
   Vitest and `tsc --noEmit` pass. Python/TypeScript shared actual-packet parity,
   altered source/geometry replay controls, and browser UI tests remain pending.
   MV-05.
4. Integrate source admission, existing queue child dispatch, stored identities
   and owner view/export; test two real owners, expired sessions, cancellation,
   byte tampering, resource rejection and host-closed submission. MV-06/07/12.
   Measure separate replay/projection limits and source/runtime-bound cache
   invalidation before mounting any GET; no replay in the API event loop. MV-13.
5. Compose isolated shared-base workbench/course and actual linked graphs,
   physical density, failure and fixed-stage readouts; supply reviewed mounting
   patch without modifying other modes. MV-08/09/11/12. Partial UI progress:
   added `GravityDensityView.tsx`, a Three.js volume composed from actual active
   cell bounds and signed returned densities, with orbit/zoom/pan, elevation
   slicing and explicitly display-only vertical exaggeration. It is mounted in
   the existing authenticated M02 result instrument; the 2D response/residual
   plots remain alongside it. The Three.js payload is lazy-loaded on opening the
   view. Focused physical-array tests (4), TypeScript, production build, and
   authored-fixture desktop/mobile WebGL checks pass; the canvas orbit responds
   to keyboard arrows and retains its camera when view controls change. Browser
   screenshots with an actual uploaded M02 result and the complete theme,
   viewport, linked-chart, and keyboard acceptance matrix remain open, so
   MV-08/09/12 remain open. The result now also replays the actual recorded
   accepted density states, with φ and normalized KKT diagnostics; its terminal
   frame must equal the returned inverse exactly. Focused browser evidence uses a
   synthetic two-state fixture and is recorded in `ui-volume-qa-2026-11-01.md`;
   uploaded-result replay on a real child result is documented below, with the
   complete UI and scientific acceptance matrices still open.
   The uploaded-survey starter now uses a 4 × 4 × 3 (48-cell) mesh with
   easting/northing/elevation controls bounded by the 4,096-cell contract.
   Regeneration preserves physical extents and the common feasible prior
   interval, activates the new mesh, and resets per-cell initial/reference
   values. Nine focused frontend tests and the production build pass. The
   existing full 48-cell frozen synthetic calibration also passes; preflight
   estimates 628,684,560 bytes for 144 source/fitting rows, below the 2 GiB
   allocation ceiling. This is not measured RSS or uploaded-data acceptance;
   details are recorded in `docs/validation/m02-48-cell-mesh-2026-11-01.md`.
   A subsequent isolated owner-workbench browser run uploaded an authored
   144-station Choclo prism CSV through the API, bound its local-metre frame and
   hash, ran the actual M02 child, rendered the returned converged 48-cell
   result and held-out diagnostics, and verified the exported ZIP. The loopback
   QA lane was explicitly opted in and used the local gravity environment; no
   production setting or host was changed. Focused browser run: 2/2 selected
   tests pass; child receipt: 37,015 ms wall, 205,414,400-byte peak RSS,
   549,774-byte scratch, 36 withheld stations. See
   `docs/validation/m02-uploaded-prism-browser-2026-11-01.md`. This closes only
   the authored local-frame desktop/light/EN browser slice. Field-data
   admission, complete UI matrix, cross-language parity, adversarial and
   multi-owner controls, host gates, and full scientific acceptance remain
   open; all convergence verdicts remain unchanged.
6. Replay all actual noise refits and separate frozen evaluation before
   projecting their views; test unavailable/failed data and conditioning labels.
   MV-04/10.
7. Actual-data browser gate across EN/ES, light/dark, desktop/phone, keyboard,
   zoom/pan/brush, chart data/table parity, geometry/frame reactivity, stale owner
   isolation and measured drawing share. MV-08/09/11/12.
8. Convergence audit lists each requirement, named gate and factual result.
   No activation by this unit; deployment belongs to the serialized controller.
