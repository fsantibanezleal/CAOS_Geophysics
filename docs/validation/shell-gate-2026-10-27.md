# Candidate shell browser gate, 2026-10-27

## Result

The local production build passed the CAOS shell browser gate with **1,332 measured states**, no waivers, and all six routes. The matrix covered 390x844, 768x1024, 1280x800, 1600x900, and 2560x1440; light and dark themes; English and Spanish; and wider-font probes at 390x844 and 1280x800.

The gate also served and verified 27 catalog and case artifacts by HTTP status, content type, byte count, and SHA-256. The lowest measured drawing share was 0.5023 and the lowest stage fill was 0.5307; both were above the configured minima.

The external machine-readable report is retained outside the repository. Its SHA-256 is `3675fe441d5e6981d48df6792aa4c909103db875015f1b66c3ecd67867dca46b`. The 120 route/theme/language/viewport screenshots are retained beside that report.

## Reproduction

From `frontend`, run `npm run build` and `npm run gate -- --out <absolute-directory-outside-all-Git-checkouts>`.

This is local candidate-browser evidence. It does not establish actual VPS deployment, multiple-case visual acceptance, complete owner acceptance, scientific method acceptance, or release cutover.
