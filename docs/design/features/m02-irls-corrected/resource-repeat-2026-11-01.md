# Corrected CPU2 resource repeats : 2026-11-01

## Scope and evidence

The approved current-source CPU2 recipe completed 20 cap controls and 20
nominal selected-case controls. The runner's `summary.json` reports 20/20 passed
in each group and complete process sampling for all 40 selected trials. Its
SHA-256 is
`ff2860f1182c8088e1f8bf8776ee7586ae9a19ff962ae25acc782ca665ec7dd9`.
Immutable per-trial JSON, log, and resource receipts are retained under
`E:\_Datos\CAOS_Geophysics\validation\m02-irls-corrected-resource-20261101`.

The measured nominal peak-RSS p95 is 308,944,076.8 bytes (294.7 MiB), with a
maximum of 309,006,336 bytes. Nominal wall-time p95 is 892.8912 seconds and the
maximum is 895.859 seconds. The cap group peak-RSS p95 is 285,847,347.2 bytes
(272.6 MiB), maximum 286,076,928 bytes; wall-time p95 is 137.1935 seconds and
maximum 140.281 seconds. These are local Windows process-tree samples for this
fixed workload.

The first cap-12 sampler receipt is retained with `sampling_complete=false`
and Windows error 1455. The resumed `cap-12-retry-1` sample is complete. The
nominal 00, 08, and 13 receipts also use explicit retry names after interrupted
parent runs; only complete, successful selected receipts enter the 20-per-group
summary. No failed or incomplete receipt was rewritten.

Runtime identity is
`m02-survey-irls-cpu-2-terminal-certificate-exact-q-replay-legacy-init-1`.
This closes the local fixed-workload repeat gate only. It is not a proof of a
resource upper bound, does not qualify a VPS memory/disk allocation, and does
not establish host admission or release acceptance. The summary explicitly
sets `resource_upper_proof=false` and `host_accepted=false` for both groups.

## Validation boundaries

The bounded current-source unit receipt remains 40 passed tests (JUnit SHA-256
`05c7acfb292ea331455b72a46cd7a2e3aeeaa68563d7aed5dcd2f7b1ce8a7d6c`). The
separate [24-case source-bound matrix](exact-q-preserved-init-original24-2026-11-01.md)
and [32 fixed-recipe noise refits](exact-q-preserved-init-original24-2026-11-01.md)
are recorded alongside that evidence. Six seeded condition-3 nuisance controls
remain poor under declared noise, and family 4 has no truth prism for a model
RMSE. No negative result is promoted to a successful fit.

The CPU2 numerical/resource work does not close the broader M02 workflow SDD,
independent review, product requirements, live-host checks, or release gates.
Retain the current release and two rollback releases. Deployment remains only
at the canonical ML VPS origin after all product and host release gates pass.
