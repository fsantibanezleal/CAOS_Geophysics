# Local production-shell gate, 2026-10-28

## Result

The current branch's production build passed the CAOS shell browser gate with **1,332 measured states**, zero failures, and zero waivers. The matrix covered all six routes at 390x844, 768x1024, 1280x800, 1600x900, and 2560x1440, in light and dark themes and English and Spanish. Wider-font probes ran at 390x844 and 1280x800.

Source commit at execution: `6d3709e82089287cf631b723e983268ee50ad078`.

The gate served and verified 27 catalog/case artifacts by HTTP status, content type, byte count, and SHA-256. Minimum drawing share was 0.5023 and minimum stage fill was 0.5307, above the configured thresholds. Representative phone and desktop captures were visually inspected after the gate.

The report and 152 screenshots remain outside Git at `E:/_Datos/CAOS_Geophysics/visual-gate-20261028T104336/`. `gate-report.json` is 7,704 bytes with SHA-256 `ef0ae4ca90f84d8d6a5055831a589b37ea54d13ef935ea27a18da88cf6f40d73`.

## Reproduction

From `frontend`, run `npm run build` and `npm run gate -- --out <absolute-directory-outside-all-Git-checkouts>`.

This is local candidate-browser evidence. It does not establish owner acceptance, multi-case scientific visual acceptance, method correctness, VPS deployment, or release cutover. The six-route release remains gated by the outstanding SDD requirements.
