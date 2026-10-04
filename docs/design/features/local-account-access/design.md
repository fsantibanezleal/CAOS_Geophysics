# Profile-aware login-only account frontend

Date: 2026-10-03. Base: d3c229656046526095c6181c4e6bf7960f9c850f.
Requirements and design precede code under the explicit user implementation
instruction. This is not another access-policy decision or full-product approval.

## Actual source inspection and retained boundaries

Read the existing account drawer, same-origin transport/lifecycle client,
gravity/MT project session-probe paths, all four prior lifecycle feature files
and project/raw design. Read actual installed shared-shell0.6.8 README/type API,
main.tsx shell composition, route/deployment contracts and applicable ADRs.
The drawer currently advertises email signup/verification/reset unconditionally
and labels every returned account a verified owner. Workbenches already hide
server operations until LifecycleApi.probe returns an authenticated account,
and clear private state on401. Public course/replay paths do not use this probe.

Reuse this existing seam rather than changing scientific workbenches or chrome.
The client-first-access feature and product-SDD amendment explicitly require
local internal DB accounts, plural accounts/projects, no SMTP/off-host backups
for the owner-tested stage and no falsely verified mailbox. Historical email
profile is explicitly retained there for compatibility, not default deployment.
No credential, owner ID or password is inferred from that instruction.

## Wire protocol and fail-closed interpretation

GET /api/auth/config uses unchanged ApiClient same-origin cookie, no-store,
redirect:error, JSON-only transport. Exact three keys:

```text
local: {mode:'local',registration_enabled:false,mail_flows_enabled:false}
email: {mode:'email',registration_enabled:boolean,mail_flows_enabled:boolean}
```

Unknown modes/keys/types or local flags other than false reject. Email signup
cannot be enabled with mail disabled because that contradicts the existing
verified-account email profile. No default email mode or fallback on404/HTML.
The parsed non-secret snapshot is immutable; no credentials/config persistence.

LifecycleApi.session returns one paired config/account snapshot: discover config,
CSRF, then /api/auth/me.401 returns signed-out; all other failures propagate.
Active local accounts need no is_verified flag. Explicit email mode requires
active AND verified. Neither parser nor policy rewrites any account flags.
Existing probe delegates to this flow so both project workbenches inherit the
same gate without renderer modifications. Unknown/unavailable profiles show
private-service failure only; public course/replay remains usable.

Login freshly discovers config, then uses original form login/CSRF/me and the
same active/profile check. Existing email methods require a fresh explicitly
enabled email profile BEFORE CSRF/POST. They remain solely compatibility for
the historical reviewed email protocol; local never invokes them. Logout uses
original cookie/CSRF route even when signed out or profile discovery is down.
Backend cookie validity, CSRF, ownership, quotas and job admission remain the
security authority. UI guards are not a replacement or authorization token.

## Account panel state and access

The existing dialog retains shell classes, labelled fields, focus/Escape/close,
scroll and exact project/upload/receipt functions. A paired session probe drives
config and account together, with abort/generation protection against stale
responses on close, language change, retry, login or logout. Unknown/loading
configuration never renders an auth action. In local mode the form is always
login; no action selector/token/reset/register/resend prompt is rendered. EN/ES
copy says accounts/password changes are operator-managed, not emailed. The
owner label says authenticated local account, not verified owner.

Only active profile-authorized accounts render project creation/list selection,
uploads, exports and processing-workbench entry. Existing workbenches already
probe on direct project URLs and hide server-run actions for guests. Their401
paths clear private state; the drawer clears its state and existing callback on
expiry/logout. Non-secret name/description/email drafts survive failure; passwords
and email/reset tokens are cleared after attempts/close. No localStorage token,
password, alternate API origin or prefilled production credential.

Returned project lists are not truncated to one; switching accounts must clear
previous owner projects/receipts. Existing validated local/replay export is public.
No local file is automatically uploaded; this feature adds no server fallback.
The deletion contract retains backup_erasure_status:'not_attempted' and now
recognizes external_backup_status:'not_configured' for the local operating
profile alongside the historical 'pending_reconciliation' state. This additive
wire union follows the explicit operating decision; unknown states still reject.
The UI describes the actual returned state, not an inferred external backup.
Neither state claims backup erasure, and the legacy state does not establish
that any external backup exists. The backend determines the profile-specific
wire state; the client never replaces an existing receipt value.

## Gates and evidence limits

Named gates are in requirements/validation. Unit and route-intercepted browser tests
exercise real production UI/client code with explicitly labelled response stubs.
They do NOT establish live API ownership or actual-host admission. The actual
config/login/multi-account API implementation is a separate integration gate; a
missing local endpoint is reported, not replaced in production with a fake.
Use existing Node/npm/Playwright and private test output, no package upgrades.
Full UI matrix screenshots are inspected; shared scientific file hashes/diff
prove no renderer/shell/palette changes. Preserve unrelated worktrees and dirty
files. This feature does not change scientific renderers or authorize a release.

## Real local HTTP integration gate

The separate local integration test uses the real backend factory, committed
Alembic migrations and installed account provisioning library, with the same
frontend build bytes. It provisions two randomized test accounts in a NEW ignored
QA database, never the existing operator database. Secrets pass through a private
child-process pipe, never public code, argv, screenshots or verification records.
The test server mounts only the real static frontend after real API routes; no
API interceptor, additional auth endpoint, SMTP sender or worker is introduced.
HTTP loopback uses cookie_secure:false only in this explicit test Settings,
matching existing local API tests. This cannot establish deployed HTTPS security.
Actual backend/frontend byte hashes are checked before/after the run. Source,
installed runtime and existing DB bytes remain unchanged; fresh QA DB/evidence
remain ignored. No backend or shared API source modifications are authorized by
this gate. Its test helper and spec live only in frontend/e2e/.

Predeclared controls: anonymous six-route access and guest project/upload/job
refusal, eight language/theme/device login renderings, two actual local accounts
with is_verified:false, two projects for one account and a separate other-owner
project, cross-account404, actual HttpOnly/SameSite cookie attributes, wrong-login
password clearing, actual logout401 and truthful local deletion receipts.
Retain every failed run. Test-owned project cleanup uses the real exact-ID API;
it never deletes the database or any operator-owned file/project.

Each integration control gets its own fresh database/server, with the unchanged
ten-auth-attempt/600-second policy. The owner control makes seven real auth
attempts, checks three further invalid attempts and the eleventh429/Retry-After.
This avoids unrelated matrix cases exhausting each other's rate windows, not
a rate-policy bypass. The static test mount rejects unmatched /api/ paths rather
than returning SPA HTML/StaticFiles405; it adds no API handler. Extracted backend
files must match the supplied immutable Git revision's actual blob bytes, and
all backend source/build bytes plus the separate existing DB are guarded.
