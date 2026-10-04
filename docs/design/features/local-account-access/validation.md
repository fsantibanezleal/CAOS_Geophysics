# Local-account frontend verification

Date: 2026-10-03 (America/Santiago; final browser XML timestamp is
2026-10-04T01:59:24.414Z). This is a frontend code/test record, not hosted
admission, deployment or complete-product acceptance.

## Contract and source

The pre-code requirements/design were persisted at56f552d. Explicit local
profile discovery, no mail actions, active-account policy and immutable account
flags follow LA-01..07. LA-08 adds the requested deletion-wire union, without
inventing external backup existence or erasure. Historical email support is
available only when the returned profile explicitly enables it.

Only lifecycle.ts and ProjectDrawer.tsx change production frontend behavior.
The same-origin transport, CSRF/cookie rules, original-byte integrity, scientific
renderers, workbench ownership probes, shell, palette, routes, numerical source,
canonical data and dependency lockfile are unchanged fromd3c2296. No API code,
installed package, training, environment upgrade or deployment is part of this
verification. Account helpers do not implement backend authorization.

Final executed Windows file-byte SHA-256:

| File | SHA-256 |
|---|---|
| frontend/src/api/lifecycle.ts | 996763a34b7ccc9033fb72ef847ea67d09da7a864e675b35ea4c32325047b633 |
| frontend/src/components/ProjectDrawer.tsx | 4a753ed3216cc8b8a44127eff6e1c4f745e4438ba1de660e429df61064e8b0ca |
| frontend/src/test/local-access.test.ts | 6fa4a0042b6f7ace8bebe4b930ffe6f9ae32a2a1f8bbc72fed2f3e672d111d68 |
| frontend/e2e/local-access.spec.ts | e775906d87bef9c5c2621855c09ab6c6bc46da0389a7d1da0aadf3f7e5ae74c2 |
| frontend/package-lock.json (unchanged) | db7820b708855821124506150278af83ce1b31c3ec90e3316047dbbee48e6853 |

These are executed checkout bytes, not claims of cross-platform newline identity.
The private build copy's two production files were checked byte-identical.

## Actual tests and retained negatives

Private output is under ignored data/experiments/local-account-access/;
no password, live account, supplied credential or test cookie is published.
The browser uses randomized transient test inputs and example.invalid identities.

| Run | Actual outcome | Receipt SHA-256 / retained evidence |
|---|---|---|
| local-access-red.xml, before client implementation |16 failed,10 passed | b4529472dd0291fa8d128613faf7071664376384dbe99f22f729f5ebb962ea1a |
| client-green.xml |29 passed,0 skipped | ba79f67c03d1f73822ff26f327f9050fc06a1fcdcf4fb44d41f3952c196b8c49 |
| frontend-full.xml, before deletion union |127 passed,0 skipped | d64ccff851089049a97aa11be4e72e4b8fb67b31c9d3e45206599c0211d2970d |
| browser run1, original assertion harness |11 failed,2 passed | playwright-run1/ contexts retained; no XML produced |
| browser-run2.xml, corrected original controls |14 passed,0 skipped | 97acb6fa3c06f58ad16429eb5af723f99535ea7b2313b61be0b47ca414d4afe7 |
| browser-final.xml, additional MT selector control |1 failed,14 passed | Original wrong tab locator retained; not accepted as final |
| deletion-union-red.xml, before union source change |1 failed,30 passed | dfbec8f2dc107d6a05fcc41f43cd9049a652851a436e087ec1a4c8fea2fdf076 |
| frontend-final.xml, final full Vitest suite |132 passed,0 skipped | 76edce5717be90cedbb380a4db8062b9015be659512dd7306bfb66022b80afc5 |
| browser-union.xml, final full browser suite |19 passed,0 skipped;27.9s | 75daf3b0a3e999b23e14b36afda94428e59682314425f98f447b2fc4d8ed208e |

The initial10 negative tests passed because missing parser functions themselves
threw; this is red chronology, not evidence of an implemented strict parser.
Later green runs execute the real parser. Browser run1 used getByLabel on select
elements whose actual accessible roles/names were present; role-based locators
corrected the harness. Export requires selecting Replay. MT guest status text
shares a node with its retry button, so the assertion checks the actual load-state
region. The added public MT control corrected its real tab name to
"MT forward and EDI evidence". No assertion, access gate or source tolerance
was loosened to hide these failed runs.

The final19 browser tests use the actual production build with intercepted API
protocol responses. They establish frontend behavior, NOT real cookie security,
server ownership, uploads, jobs, mail delivery or operating-host admission:

- Eight EN/ES × light/dark ×1440×900/390×844 cases exercise login-only prompts,
  truthful local-account label, two-project selection, keyboard Enter login,
  focus/Escape restoration, no horizontal dialog overflow, authenticated-only
  upload-form visibility, logout, secret clearing and absence of mail calls.
- Failed login preserves email but clears password; separate accounts replace
  the project list;401 clears private controls and prompts reauthentication.
- Anonymous six-route navigation and replay remain open even when config fails.
  Direct gravity and MT project links stop before project or unsafe API requests.
- Anonymous layered MT forward sliders remain interactive with no API calls.
  M13 loads the unchanged reviewed model and performs actual WASM inference,
  enabling its scores export with no API calls. This is an access/operation
  regression, not a new numerical-parity or accuracy study.
- Closing a pending profile probe prevents stale restoration; inactive accounts
  get no project requests; only explicit email flags reveal historical actions.
- Four EN/ES deletion controls retain both recognized wire states, remove the
  selected project from the intercepted list, and show state-specific nonclaims.

All16 run2 guest/owner screenshots were inspected; final source reruns retain
their own16 screenshots. The unchanged shared styles provide readable phone
wrapping and vertical scrolling, not a new palette or renderer.

## Runtime and reproducible commands

Existing Node24.14.1/npm11.11.0, TypeScript5.9.3, Vite7.3.6, Vitest4.1.11,
Playwright1.63.0, shell0.6.8 and ORT Web1.30.0. The checkout's old dependency
directory lacks ORT, so its original npm run build failed withTS2307. No package
was installed or replaced. A private source copy uses a read-only junction to an
already installed dependency tree with the exact same lockfile SHA above.
That copy initially omitted imported spatial-calibration.json and failed; after
copying that unchanged file, full TypeScript plus Vite builds passed, including
the final deletion union. Both harness/dependency failures remain reported here.
The final built index.html SHA is
1ba774a7f049b185bdf4a5d64934771b8cdd174a7231b0d5bca78e226ad43624.
Vite's existing >500kB chunk warning remains; no warning threshold changed.

Portable test commands fromfrontend/, using already installed dependencies:

```powershell
npm test -- --reporter=default --reporter=junit --outputFile.junit=../data/experiments/local-account-access/frontend-final.xml
# Build in the private byte-checked source copy with its existing runtime.
npm run build
npm run preview -- --port $LocalReviewPort --strictPort
$env:GEOPHYSICS_QA_URL = $LocalReviewOrigin
$env:GEOPHYSICS_QA_EVIDENCE = '../data/experiments/local-account-access/browser-union'
$env:PLAYWRIGHT_JUNIT_OUTPUT_FILE = '../data/experiments/local-account-access/browser-union.xml'
npx --no-install playwright test e2e/local-access.spec.ts --workers=1 --reporter=line,junit --output=../data/experiments/local-account-access/playwright-union
```

Use fresh private output paths on replays; do not overwrite historical receipts.

## Guards and limits

Actual check_artifacts.py passes20 truths/120 conditions/348 method results with
all hashes/sizes; check_phase_assets.py passes unchanged M13 asset identities.
Content, template, CI-budget and single-origin source guards pass. Base-integrity
checks find no tracked environment/native/heavy-data or leaked machine paths.
The requirement ledger remains structurally valid with1 failed/18 unresolved
whole requirements. No scientific/product/release success is inferred from it.

Real combined API/browser cookies, CSRF, plural-account ownership and the actual
operating-host are separate acceptance gates. These local controls neither run
heavy server jobs nor establish deployment, durability or geological validity.
