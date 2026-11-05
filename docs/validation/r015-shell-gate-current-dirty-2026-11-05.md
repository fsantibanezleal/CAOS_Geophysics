# Shell product gate on current dirty checkout — 2026-11-05

## Result

The final local production build passed the CAOS shell product gate: **1,464 measured states, 157 screenshots, zero failures, and no waivers**. The matrix covered `/app`, Introduction, Methodology, Implementation, Experiments and Benchmark at 390×844, 768×1024, 1280×800, 1600×900 and 2560×1440; light/dark themes; English/Spanish; and the configured wide-font sizes 390×844 and 1280×800.

The minimum App drawing share was 50.9% at 1280×800 (FWI_NOISY, Inversion). Minimum stage fill was 48.26% (LEARNED_CNN, Inversion). All six local shell routes and bundled JSON artifacts passed the gate checks. This is local UI evidence only; it does not establish scientific acceptance, live VPS acceptance or owner visual acceptance.

## Reproduction and source identity

- Checkout: `D:\_Repos\_Web_Projects\CAOS_Geophysics`.
- Base `HEAD`: `f0ec2fc37fdae1f0c1c7d40b6cae386a85d7e6ac`; checkout was dirty with an active merge (`MERGE_HEAD c595aeb963a612da6b73e277757a66dd4acd6d21`).
- Command: `cd frontend; npm run build`, then `npm run gate -- --out E:\_Datos\CAOS_Geophysics\validation\shell-full-final3-20261105`.
- Shared shell pin: `@fasl-work/caos-app-shell` 0.19.12.
- `frontend/src/styles.css` SHA-256 (LF-normalized): `034feff8f8796c8c121fb39e76e9b8b2d9d4d9d8b107431f334f4acc78301fb2`.
- `frontend/src/pages/Workbench.tsx` SHA-256 (LF-normalized): `44453c49ff8a2448c8c4ad555bb84627e50efb3d5345e6886bca9e0a03971907`.

## Retained external evidence

The complete gate report and screenshots remain outside the repository at `E:\_Datos\CAOS_Geophysics\validation\shell-full-final3-20261105`.

- `gate-report.json` SHA-256: `7413f5c2d0f71b60347911e348319a9d49f517e65cacd2c51bd1e5fd0523c108`.
- `artifact-manifest.json` SHA-256: `5053a3f718bbd3f5f43723bd2680026296467c138326a365665534b287496ad9` (159 gate-output files with byte counts and SHA-256).

This supplements the clean-revision R-015 receipt. The dirty-checkout run is not substituted for that formal receipt and does not change the overall replacement release verdict.
