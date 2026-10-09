# Read-only ML host state checkpoint

Date: 2026-10-03, approximately11:27 UTC. MAIN used the authorized SSH connection
to the ML host solely for filesystem/memory readouts and the existing release
symlink. No write, compression, removal, service, package, listener, key, database,
DNS or deployment operation was performed. This record persists those observed
values; it is not authenticated public HTTPS or an actual calculation receipt.

| Observed quantity | Bytes / exact value |
| --- | ---: |
| Root filesystem total | 80290492416 |
| Root filesystem used | 53362098176 |
| Root filesystem available | 23600791552 |
| Available/total | 29.394254340501366% |
| Memory total | 8127717376 |
| Memory available | 5173080064 |
| Available/total memory | 63.6473910777874% |
| Swap total | 4294963200 |
| Swap used | 654835712 |

The current symlink still selected
`/var/www/geophysics.ml.fasl-work.com/releases/20260926235216`.
Filesystem available bytes are the tool's reported available quantity, not an
assumed total-minus-used value; filesystem-reserved blocks may differ. No new
application-version, TLS, user-job, isolation or resource-capability assertion.

The unchanged admission threshold is30% available root disk. This checkpoint
therefore cannot open admission. The earlier separately retained40-job run
failed at29.42%; its calculations, timing and control outcomes are not relabeled
as this read-only inspection. See the
[actual-host calculation record](actual-host-mt-2026-10-03.md).

No older release or failed evidence was deleted. Any lossless obsolete-release
compression/removal requires the pending owner's scoped decision, retaining the
active release plus two newest rollback releases. Other projects are outside
scope. Recovery/latest off-host deletion authority, mail/identity and native
worker/platform admission remain separate unresolved release gates.
