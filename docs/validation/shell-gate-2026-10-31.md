# CAOS shell browser gate — 2026-10-31

The current dirty checkout at `9f022aae8d178211b4c77730b722723fc3345a3b` passed the installed CAOS shell gate on 2026-10-31. At capture the checkout had 73 changed paths. The measured production build used shell `@fasl-work/caos-app-shell@0.19.9`; `frontend/dist/index.html` was 670 bytes with SHA-256 `06c49bbe04ed753a5fbd07a9713118f1f38f06341f8603580e226b2c9ff15180`. The complete built artifact tree is 1,045,868,078 bytes.

## Gate result

| Measurement | Result |
|---|---:|
| Browser states | 1,442 |
| Screenshots | 157 |
| Viewports | 390×844, 768×1024, 1280×800, 1600×900, 2560×1440 |
| Themes and languages | light/dark; EN/ES |
| Waivers / failures | 0 / 0 |
| Minimum instrument share | 50.23%, `/app`, 1280×800 light EN, recovery view |
| Minimum stage fill | 53.07%, `/app`, 1280×800 light EN, FWI cycle-skip question view |

The raw `gate-report.json`, served `index.html`, and 157 captures are at `E:\_Temp\CAOS_Geophysics\validation\shell-gate-20261031`. This is shell/layout integration evidence for a dirty local build. It does not establish scientific acceptance, complete frontend fixture acceptance, API/worker or actual-host acceptance, or user design acceptance. The outer workbench label is legible in the tested phone captures; the exact report records the full route, viewport, locale and theme matrix.
