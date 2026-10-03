# Bounded native metadata accounting clarification

Status: proposed for MAIN read before exact accounting code change, 2026-10-03.
The seven reviewed files at48245d1 and first8acab62 numerical receipt stay unchanged.
No cap, scalar-count or numerical-tolerance change is proposed.

MAIN independently executed the source8acab62 counterexample
`x = (((),) * 32768,) * 5`: an inexpensive shared input representing163840 empty
child containers. The old private metadata walker charged neither empty containers
nor punctuation, so returned None despite the compact metadata exceeding262144
UTF-8 bytes (actual491531 bytes). Wrapped as source.citation, semantic rejection was delayed until
after avoidable structural work. This is a real pre-admission bound defect, not
a forward/J/physics failure. The existing134-pass receipt is historical evidence,
not proof of a full resource gate.

Proposed exact meaning of the already-frozen256KiB metadata limit: the compact
UTF-8 canonical native-digest descriptor representation in contract.md, with
ensure_ascii=False and compact separators. Count dict/tuple delimiters, commas,
colons, JSON-escaped keys/strings and canonical primitive representations.
Arrays contribute their declared dtype/shape/SHA descriptor; the64-character
SHA length is known without reading/hashing/copying any array. Scalar negative
zero normalizes exactly as the digest. No actual digest or whole-tree encoding
is performed to decide admission.

An incremental metadata-only walker charges each container's punctuation BEFORE
visiting children and stops at262144 bytes. Every empty container costs at least
two bytes, bounding structural visits independently of MAX_SCALARS. Preserve
MAX_SCALARS32768 counting only original keys/primitive scalar nodes, NOT containers
or generated array-descriptor scalars. Depth8, axis/fullcell/receiver/storage caps
and exact-type-before-hook rules stay unchanged. Shared aliases are charged on
every logical occurrence as they are in serialization; no identity shortcut.

Tests authored BEFORE the fix: the bounded shared-empty counterexample both
direct and source-wrapped, forbidden finite/copy/count/hash/engine/semantic spies,
exact JSON string-escape/punctuation boundaries, scalar-count independence and
normal declared requests unchanged. No giant input, added type coercion,
matching-array traversal or serialization-based allocation of the full rejected
tree is permitted. Fresh source/tests require a new receipt after correction;
first-milestone receipts are not rewritten. Public early exact-shape rejection
can supplement the walker but must not leave the generic resource accounting
unbounded for later admitted native-result trees.

Private whitening indices also require unique strictly ascending aligned rows;
the public observation/noise contracts remain compact ordered identities. A
separate tiny negative preceded that correction: duplicate, reordered, negative
and out-of-range identities in both noise modes failed with value scans and
factorization denied. The private WIP correction now rejects those rows before
noise-value scans. No repeated-row covariance or variance floor is introduced.
Full optimizer/selection/resource/24-case
acceptance is still pending, not conferred by this clarification.

## Actual pre-fix and independent evidence

The [new independent review receipt](evidence/main-planner-tiny-review-20261003.json)
retains MAIN's separate134-pass replay, signed six-cell oracle and confirmed
resource defect at8acab62. MAIN is the coordinating independent agent, not a
claim of Felipe-supplied measurements or owner acceptance. Only the JUnit bytes
and counterexample were additionally inspected/replayed by this producer; the
separate oracle results and private-helper hash are MAIN-reported evidence.

Producer bounded pre-fix run, tool chunk aed9b1, on2026-10-03 at12:41 UTC:
14 failed,2 passed,54 deselected (16 selected). Two empty-container failures,
four prospective exact-byte boundary failures and eight invalid-row failures.
Test-only reduced byte/scalar budgets exercise boundaries; production constants
are unchanged. The current implementation still leaves the metadata controls red.
The two positive scalar-accounting controls passed. The red JUnit SHA is
5f74e890e3fb9ed86fdfa3cd6187fd1dd6f893d9d8b7ee28bc2b3a828240bd39.

After the private row correction, tool3b0d45 passed149, zero skips,7 deselected
in4.39s. Those seven exclusions are deliberate pending metadata-review controls,
NOT acceptable as final coverage. Its JUnit SHA is
0ef70c09f3574349c8957f01b64df182911bf426636cef0e23b5390bf2576109.
Both runs include uncommitted optimizer work; neither is a full L2 acceptance.
Initial earlier red controls and fixture correction remain contemporaneous
history: tool2f9df1 had4 failures,1 pass,54 deselected; an earlier40000-entry
single tuple incorrectly exceeded the existing per-container cap and was corrected
to four10000-entry tuples without altering production caps. No historical receipt
is rewritten. Prospective accounting code has NOT been implemented or approved.

Review request: read this whole clarification, then explicitly approve or revise
the exact existing256KiB interpretation BEFORE the production accounting patch.
No change to the seven frozen files, scalar-count cap or physics thresholds is
needed. This review does not authorize any additional callable or environment.
