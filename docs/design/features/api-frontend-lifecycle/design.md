# Authenticated project/raw frontend design

Date: 2026-09-28. Implements `requirements.md` under the approved parent SDD. Live release 0.04.001 remains a static curated research workbench; this branch does not deploy it.

## Boundary and selection

The six shell routes remain fixed. A project drawer in App holds account, project, upload, and receipt/export actions. The existing synthetic/curated case selector remains the guest-readable science workbench. A private raw project is not silently turned into the selected scientific dataset; the drawer explicitly says format/metadata-envelope checks are not scientific QC and no processing/job API is available. This avoids an inert seventh page or misleading run button.

The `single-origin` build mode alone enables the drawer. The legacy build stays unchanged for current Pages production. On opening the drawer, a same-origin CSRF/`me` probe distinguishes signed-out, verified, and unavailable service; it never presumes that a static HTML response is API success. No alternate API origin, bearer token, localStorage credential, fake response, or unversioned asset adapter is allowed.

## Wire and state

`frontend/src/api/contracts.ts` mirrors `app/views.py`: explicit `geophysics.source-record-view/v1` and `geophysics.raw-asset-view/v1`, nested source, nullable citation/DOI, private-storage permission, physical metadata, receipt/download path, `raw_metadata_checked`. The parser rejects private/internal keys and unknown version. `storage_key` remains solely an internal Python field, never an owner-view requirement. An owner-view JSON fixture is checked in, validated against the API's Pydantic view by a Python test, and parsed with negative drift cases by a TypeScript test. Other future dataset/job/result mirrors remain separate.

The typed lifecycle client uses only relative `/api/` paths resolved against `window.location.origin`, `credentials: same-origin`, `redirect: error`, `cache: no-store`. It obtains `/api/auth/csrf` before unsafe actions and includes `X-CSRF-Token`. Cookie login uses URL-encoded `username`/`password`; upload sends the exact `File` bytes with matching `Content-Type` and bounded `X-Asset-Metadata` JSON; downloads/export use authenticated blob requests and only server-returned URLs matching the owned project/asset path. The client parses API problem bodies (including field paths), FastAPI Users `detail` errors, empty 204 responses, and binary failures; it never treats a network or parse error as success.

The UI state is transient in memory: account state, selected project, returned asset views, busy/error/success. Refresh re-reads owner state. Login never persists a password. Account registration explains the verification email; the user pastes the token into the verification form. Password reset is supported by the same API but has no custom token service. Logout clears owner state. An expired session returns to signed-out without exposing stale owner data. No privileged data is rendered for guest read.

## Scientific upload and destructive operations

The upload form has required, labelled fields for source rights and physical metadata. Format controls map the API's ten supported raw envelopes, allowed MIME, units, component frames and geometry keys; channel orientations and station companion ID are explicit. File size/extension and rights are checked client-side as guidance; the API remains authority for MIME, envelope, geometry, CRS and quota. File SHA-256 is computed from bytes before submission and placed alongside expected byte count. No metadata value is guessed from a file, and the form does not pre-claim a datum, valid dataset, or eligible solver input.

The receipt labels the verdict “raw metadata checked — scientific QC not performed,” shows SHA-256, bytes, source rights/attribution, and direct owner download. Project export obtains the API ZIP. Project deletion requires typed project name confirmation and explains that the API refuses unresolved backups or unexpected bytes; the successful response records `receipt_id`, `backup_erasure_status` and `external_backup_status`, never claims backup purge. Since no individual asset-delete endpoint exists, no such action is shown.

## Visual and accessibility rules

The drawer is an App-local overlay, with labelled close/Escape/focus return and scrollable content, not a shell replacement. Product layout uses only existing shell tokens and control classes; no new font, colour literal, global palette or seventh top-level tab. It is usable at desktop and phone widths in EN/ES. Rendered QA must inspect account, project, upload, receipt and deletion states, not just the landing page. Browser QA against a local real API fixture is preferred; any mock-only check is labelled unit-level, not live integration.
