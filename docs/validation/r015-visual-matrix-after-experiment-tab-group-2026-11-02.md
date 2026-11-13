# Current visual matrix after experiment navigation grouping : 2026-11-02

The current production bundle was tested with the declared 16-combination browser matrix: EN/ES, light/dark, desktop/phone and normal/reduced motion. **16 passed; zero failed, skipped or flaky.** The run traversed all declared routes and navigation dialogs and produced 112 screenshots (11,169,838 bytes).

An initial current-build run failed all 16 combinations because the Experiments page exposed seven peer tabs. The shared shell reported the ADR-0071 limit of six. The page now uses the shell's `TabGroups`, grouping experimental-design controls (case, acquisition, noise, regularization) separately from method evidence (learning, MT/EDI, Long Valley). The test then passed all 16 combinations, including pointer and keyboard navigation, with no shell console errors.

## Evidence

- Base checkout: `f0ec2fc37fdae1f0c1c7d40b6cae386a85d7e6ac`, dirty direct checkout.
- `frontend/src/pages/Research.tsx` SHA-256: `c868349e8c0aaa342dfb7110b396856aa9dac03f123bdd7cb6b5a9bdc2341384`.
- `frontend/e2e/visual-matrix.spec.ts` SHA-256: `110a62bfd630ec9028463c35947ff4ef07f03a85e547b1b08225b1a161e206b2`.
- Playwright JSON report SHA-256: `0ba1859995b10ee67a3d2b755eb841f48e83747f12d26619a43a94538e8b80d0`.
- Screenshot manifest SHA-256: `cbf183f17dfbed03a078ec35c910cb2ed85a196218cacbf861eb1383c9efcae1`.
- External artifacts: `E:\_Datos\CAOS_Geophysics\validation\visual-matrix-grouped-20261102`.
- Production build passed after the change (1,944 modules). Vite continues to report a 549.96 kB Workbench chunk warning.

This closes the local 16-combination navigation/viewport gate for these source bytes. It does not establish scientific acceptance or VPS release acceptance.
