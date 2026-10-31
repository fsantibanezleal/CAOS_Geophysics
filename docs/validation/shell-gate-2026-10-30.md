# Full CAOS shell gate — 2026-10-30

## Result

The rebuilt working copy passed the full product shell gate with **1,442 measured states, 157 screenshots, zero failures, and zero waivers**. The run exercised all product routes and catalogued App cases at 390×844, 768×1024, 1280×800, 1600×900, and 2560×1440; light and dark themes; English and Spanish; and the declared wide-font checks at phone and desktop sizes.

The run covered the current dirty checkout and completed with no failures or waivers. The 157 screenshots are retained outside the repository at the path below.

## Source and reproduction

- Product checkout HEAD: `221d031ca366410ca36066da37d302b9832008b1` (detached; working tree had 96 changed paths during this run).
- Frontend production `dist/index.html` SHA-256: `fb2e2c66601e11402001fbae0c0dce332761719db82f43511e9cd7cc144b49c8`.
- A fresh production build after the gate produced the same `dist/index.html` SHA-256.
- Command: `$env:GEOPHYSICS_GATE_OUTPUT='${TEMP}\geophysics-shell-gate-current-20261030'; npm run gate`.
- Gate report SHA-256: `bd399d3fd7b56f18c33c5c0c5314dc7551524c42b32a17eb8edea9ee8e84034b`.
- Capture index SHA-256: `b7a23c8c5821754b179b0cf12421b8baea15d917cf25944a0dcbeda2140a30a4`.
- The raw report and all 157 captures are retained locally at `${TEMP}\geophysics-shell-gate-current-20261030\`.

This is full shell integration evidence for the measured working copy. It does not replace scientific convergence, actual-host user-data acceptance, owner design acceptance, or release/deployment gates.
