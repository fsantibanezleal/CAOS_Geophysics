# M03 dependency-ordered executable plan

Status: planned. Date: 2026-10-03. No product task below is implemented by this branch. The complete packet consists of [research](research.md), [requirements](requirements.md), [design](design.md), [contracts](contracts.md), [algorithms](algorithms.md), [validation](validation.md) and this plan. Parent approved SDD remains authoritative; BL-013/issue45 remains unfinished until actual scientific/product/field acceptance.

## Stop gate and ownership

T00: MAIN FULL-reads all seven documents, own primary retrieval receipt and packet-check receipt at the exact commit/PR pin; records explicit approval or required changes. No product code, new dependency, provider measurement acquisition, DB migration, worker admission or deployment before this gate. Documentation checks and a draft PR are not approval. This independent slice does not duplicate MAIN's gravity/persistence/course implementation, change production/DNS/Pages, synchronize a fleet or promote main.

Review decisions required: physical/datum and IGRF evaluator receipt strategy; proposed 400-row/26-fit resource envelope and useful scientific resolution; heldout/calibration/provider-product interpretation; exact typed/local/online CLOSED schemas; conditional microlevel/RTP boundaries; field source/rights and provider-comparator availability. Approval of the local algorithm does not activate online or approve full-survey acquisition.

## Local vertical, after T00

T01 (M03-001..004,020; depends T00): implement data-pipeline/magnetic_line_contract.py loader/parser/schema/kind/rights/byte preflight and original-order inventory. Add tests/data/test_magnetic_lines.py named gates. Include actual retrieved metadata as identity-pinned small documented fixtures only if rights permit; originals remain separately identified. No fabricated flight lines from grids. Implement auxiliary correction-input arrays within the bounded sidecar/request policy, not an arbitrary additional file/URL loader. Finish boundary tests before numerical imports.

T02 (M03-013,018; depends T01): implement magnetic_line_validation.py::make_partitions and contract::preflight. Geometry-only outer/inner full-line manifests, buffered ties, explicit source/grid/segment/26-fit counts and support domains. Implement leak test by perturbing outer values and proving identical training-derived choices. Freeze prospective environment/runtime/native/transitive source hashes and verify already available engine versions; stop if missing, do not install dependencies under this approval.

T03 (M03-005..007,016; depends T01,T02): implement immutable instrument/reference DAG in magnetic_lines.py, synchronize actual nav/base/calibration records and exact masks. Produce independently evaluated IGRF receipt only using a separately reviewed available evaluator with resolved height semantics/source rights. No locally compiled NOAA routine/dependency addition is implicit. Add exact sign/epoch/basis/duplicate-correction/weak-versus-exact/RTP refusal tests. Unknown provider processing remains inspection-only for those corrections.

T04 (M03-008,009; depends T02,T03): implement segment/crossover and component/gauge offset QC, preserving rejected pair inventories and interpolation weights. Add independent geometric/QR controls, height gradient and disconnected/heldout-calibration refusals. Do not apply inferred training offsets to uncalibrated test lines. Preserve original/derivative arrays in all tests.

T05 (M03-011..015; depends T02,T04): implement pinned one-sensor equivalent-source and geometric comparator paths, independent augmented QR oracle, explicit source geometry/scaling/weights, candidate selection and final one-time evaluation. Add sampling/support masks and separate higher-plane/FFT continuation under source-free/datum/grid constraints. No source coefficient is labelled geological susceptibility. Record candidate failures and coverage denominators. All parameter bounds and no-thinning gates precede solver entry.

T06 (M03-010,017; depends T05): implement qualified complete-rectangle spectrum, exact normalization/units and explicit directional microlevel diagnostic. Add periodic mode, Parseval, holes, stripes and geological-loss controls. Export removed/retained/transfer arrays, do not automatically publish filtered field corrections. Unsupported nonparallel/RTP/downward cases remain typed refusals.

T07 (M03-011..019; depends T03..T06): implement tests/fixtures/magnetic_lines/generate.py original recorded acquisition family S1..S6 and independent dipole truth. Author and pin fixture rights explicitly; publish no provider-looking license assumptions. Add positive/negative gates, h/source refinement, repeat manifest tests and standalone cold resource profiling. Algorithm-control failure requires investigation and reviewed change, not retrospective weakening of acceptance. Commit validated thematic milestones with human-only authorship and exact scoped path staging.

T08 (M03-019,020; depends T07): implement paired scripts/magnetic-lines.ps1 and scripts/magnetic-lines.sh plus magnetic_lines.py::export_run. New destination only; original/request/environment/results/masks/lineage/rights members and replay receipt. Tests/data/test_magnetic_line_export.py verifies deterministic replay, denied member custody, mismatched hash/runtime and no overwrite. No network retrieval inside scripts or replay.

Prospective CLI after implementation (not executed or claimed available now):

```text
pwsh -File scripts/magnetic-lines.ps1 -Csv <original.csv> -Metadata <sidecar.json> -Request <request.json> -OutputDirectory <new-directory>
sh scripts/magnetic-lines.sh --csv <original.csv> --metadata <sidecar.json> --request <request.json> --output-directory <new-directory>
python data-pipeline/magnetic_lines.py validate --csv <original.csv> --metadata <sidecar.json> --request <request.json>
python data-pipeline/magnetic_lines.py run --csv <original.csv> --metadata <sidecar.json> --request <request.json> --output-directory <new-directory>
python data-pipeline/magnetic_lines.py replay --bundle <allowed-export-directory> --output-directory <new-directory>
```

Wrappers invoke the same entrypoint/flags and explicit configured existing Python runtime, never auto-install or silently switch system environments. Validate may emit structural/eligibility diagnostics but never a numerical success. Replay validates custody before computation; it cannot fetch missing denied raw data.

## Actual data review, independently gated

T09 (M03-001,002,004,014,020; depends T00; acquisition separately approved by MAIN): review provider original identity/rights, Charleston attachment notices/actual bytes/dictionary/report and scalar channel/reference/geometry/correction metadata. Initial metadata/docs only are permitted now; no measurement bytes acquired by this packet. Resolve actual full file size rather than trust advertised transfer quantity. If a bounded subset is separately approved, retain its parent raw identity, explicit selected IDs/policy and limited coverage; never call it full survey. Verify a numeric provider comparator separately; Charleston RGB cannot meet it. Bartlett remains a grid-kind negative/context case, not fallback line data. If rights, row metadata or comparator cannot resolve, record concrete source questions and leave field acceptance unresolved, not synthetic-complete.

T10 (M03-014,019,026; depends T08,T09): execute eligible private new user data and, if actually admitted, genuine provider field lines. Retain commands/results/blocked metric/coverage/comparator/source pins and source-cited worked interpretation. Predeclare any field acceptance thresholds from actual objective/measurement evidence. No known sigma -> no chi-square/confidence interval. No untreated/calibration channels -> no independently sealed processing claim. Commit accepted permitted artifacts only after rights member review.

## Future online interface and owner-controlled activation

T11 (M03-021; depends T00,T01): implement typed CLOSED capability port app/magnetic_contract.py and frontend/src/api/magnetic-contracts.ts after integration owner review. Exact local recipe, required metadata/bounds/reasons; zero dispatch and no replay masquerade. Preserve existing gravity registry/contracts and storage inventories. CLOSED interface completion is not new-data online acceptance.

T12 (M03-022; depends T08,T11 and MAIN native-worker/accounting owner approval): implement app/magnetic_compute.py restricted invocation of unchanged local core, attempt-bound custody and reviewed worker integration. Native Windows/Linux profiles verify cold useful-resolution headroom, tree CPU/kill reserve/RSS/scratch/wall and controller budget, source/native/runtime pins, real fresh input and cancellation. At least thirty cold runs per profile plus worst/negative tests; no supplied/mock accounting positive substitute. Failure leaves CLOSED. No production host mutation is authorized by this plan packet.

T13 (M03-023; depends T12 and MAIN persistence owner's FULL-read approved extension): add precisely reviewed app/database.py/app/bundle.py method inventory, atomic artifact/DB publish, owner-scoped export/import/recovery and deletion authority. Tests/api/test_magnetic_recovery.py covers every crash/tombstone/hash/cross-owner boundary. This slice does not propose parallel gravity schema rewrites or unreviewed migrations. OPEN registry change needs T12 and T13 exact receipts plus explicit MAIN admission, not only successful tests in isolation.

## Scientific instrument, documentation and convergence

T14 (M03-024; depends T08,T11; coordinate existing Workbench owner): implement MagneticLineInstrument.tsx and magnetic-view-data.ts using ADR-shell components, one selected run and actual map/line/tie/residual/power arrays. Literal units/masks/partition/geometry and stable linked selection; scientific changes generate requests rather than display-only fakery. Local replay lane remains visibly different from CLOSED/OPEN online. Render full EN/ES/theme/phone/keyboard/negative matrix and compare readouts to numerical arrays.

T15 (M03-025; depends T08,T10,T14; coordinate MAIN course owner): author docs/methods/magnetic-processing/01_lines-and-grids.md, MagneticLineCourse.tsx, magnetic-lines.svg and architecture.ts integration with equations, worked local/user/field eligibility, exact commands and source citations. Do not duplicate broader course framework or redesign the shell. Verify rendered equations/theme diagram arrows and six-route integration; unsupported field examples stay unresolved.

T16 (M03-026; depends all applicable tasks, with explicit unresolved records): implement scripts/check_magnetic_artifacts.py and feature convergence.json with literal per-requirement evidence. Execute all gates, review scientific limits and record unresolved source/native/durability separately. Issue45/BL-013 completion needs actual eligible field evidence, full local and admitted fresh online workflow, durable import/export and rendered scientific/course acceptance required by the parent SDD. A narrowed bounded subset or CLOSED-only method cannot silently close the parent scope. MAIN integrates accepted verticals and decides later scoped develop/main release plus single-ML-VPS deployment; this branch remains docs-only draft.

## Packet persistence now

Current delivered scope is the seven fully specified documents and own metadata/docs retrieval receipt plus cheap guard receipt. The raw retrieved bodies live in ignored data/raw/m03-primary-20261003 with exact recorded hashes; no provider measurements, new dependency, product code or production state is added. Stage only this feature directory and the two named research receipts. Create a human-only scoped commit, push task/geophysics-m03-lines-sdd, open draft PR to develop and attach it. Send MAIN exact commit, all files, guards and authoritative source findings; stop for FULL-read/explicit approval. Do not merge, update parent acceptance or claim deployment.
