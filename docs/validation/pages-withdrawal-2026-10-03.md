# Secondary publication withdrawal, 2026-10-03

Scope: implement the owner's approved single-ML-VPS hosting decision, without replacing the current VPS release, deleting retained releases, changing DNS, changing other services, or claiming the incomplete replacement accepted.

## Actual external operation

The legacy GitHub publication workflow (ID 356985425) was disabled through the GitHub repository API. The repository Pages publication was then removed through the repository Pages DELETE endpoint. These operations succeeded; no VPS release operation was performed.

The subsequent checks at 2026-10-04T00:03:59Z (2026-10-03 in the owner's timezone) showed:

- Workflow state: `disabled_manually`.
- GitHub repository Pages GET endpoint: HTTP 404.
- Former public project-site URL: HTTP 404.
- Existing `https://geophysics.ml.fasl-work.com/`: HTTP 200; entry title `Inverse Earth Studio | Geophysics`.

These checks establish withdrawal of the observed secondary publication, not the health, correctness or acceptance of the legacy or replacement product. Existing historical release receipts are preserved, not edited to imply that only one origin existed then.

## Source/build policy

The obsolete publishing workflow, active hosting instructions and route-specific duplicate asset generator are removed. All frontend build entry points use the sole root-relative Vite build. The shared route manifest and six routes remain unchanged; the VPS SPA fallback supplies deep links. The runtime no longer selects a legacy project-site prefix or hides the submitted-data workbench behind a special build mode.

The stdlib source guard and its local negative controls cover renamed publishing actions/permissions, retired paths/CNAME, relative/conditional/project bases, runtime fallback, alternate build commands, active secondary links, and generated duplicate assets. This is a source-policy gate, not the full R-012 browser gate or R-017 release gate.

The legacy static uploader is gated before reading credentials, creating an archive or contacting the host. It requires both the source/build policy and whole-product release acceptance. It is not a new API/worker deployer.

## Local source/build checks

The complete current frontend suite passed 101 tests in 18 files. The normal root-only production build passed TypeScript and Vite, then the built-asset source guard passed. These checks run locally; CI only performs the cheap source/build guard. Eleven stdlib positive/negative deployment-policy controls passed. No numerical test was skipped or reclassified by this source cleanup, and no scientific producer or canonical array was edited.

## Unclosed release requirements

Whole-method acceptance, submitted-data integration, complete scientific documentation and visual QA, actual-host admission, account email delivery, durable backup/deletion authority, Linux restore/rollback and live API/worker acceptance remain open. The application has not been redeployed by this withdrawal operation. Issues 61 and 80 must not be closed from this receipt alone.
