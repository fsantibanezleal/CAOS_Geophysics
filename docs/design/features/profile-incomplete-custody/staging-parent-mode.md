# Staging-parent producer/recovery parity

Pre-code focused repair, base428ee8c. Actual private q12 reached observer pidfd
kill and ordinary failed-row stage retention, then refused recovery because
the producer created `.job-staging` with default0755, while the unchanged
recovery correctly requires ordinary-owned private directories. Q12 remains
FAILED, with original stage/root records preserved; no crash acceptance.

## Requirements

Before allocating a new Linux profile stage or privileged process, create the
ordinary staging parent with requested0700 beneath a held no-follow data root.
Whether new or already existing, open/validate its descriptor as a directory,
owned by the current ordinary UID and with no group/world permission bits.
Reject links, substitutions, foreign owners and group/world-accessible parents.
Do not chmod or migrate unknown existing debt. Existing0755 q12 is retained and
refused, not repaired in place. Newly created child stages have the same private
ownership/mode validation and the parent descriptor stays held through execute.

## Design

Add one constructor in the ordinary Linux worker, using anchored mkdir/open and
fstat checks. Execute invokes it after input/installation admission, before stage
mkdir and subprocess creation. Close its descriptor in existing finally. Keep
the existing missing-receipt recovery private-directory predicate unchanged;
there is no successful execution, cancellation or custody schema amendment.
No changes to root helper/config/installed closure, shared controller, quotas,
originals, job owner, live flags or MAIN checkout.

## Tasks / gates

1. Commit pre-code before repair.
2. Portable red-to-green constructor/order/negative controls.
3. Actual POSIX filesystem producer-parent/stage -> unchanged recovery private
   predicate and partial evidence inventory, under permissive umask. Keep real
   group/world, links, owner and substitution negatives. This mode integration
   is not the privileged observer-kill/SQL/guardian/archive qualification.
4. Run selected unchanged adapter/recovery regressions, Ruff/diff and push pin.
5. Parent runs fresh changed-source q13 full private queue/crash/archive; do not
   touch q12 debt or independently repeat privileged host qualification.
