# Local JSON boundary full-review packet

Status: design-only, draft [PR127](https://github.com/fsantibanezleal/CAOS_Geophysics/pull/127) review, no implementation permission. Related scoped [issue124](https://github.com/fsantibanezleal/CAOS_Geophysics/issues/124); broader issues39/43 stay open. Read ALL seven documents, not just the limit table:

1. [Research and inspected sources](research.md)
2. [EARS requirements and named gates](requirements.md)
3. [Architecture, pre-allocation scanner and non-goals](design.md)
4. [Exact root/history/error/resource contracts](contracts.md)
5. [Prospective numerical, negative and local resource checks](validation-plan.md)
6. [Sequenced tasks and NOT_RUN convergence](tasks.md)
7. This packet and its scope/approval decisions.

## Requested decisions before code

Approve or amend the exact bytes-to-native signature/error fields; root-only16/8-MiB structural lane; container/key/scalar accounting; pre-materialization strict UTF-8/grammar/duplicate/token/canonical scan; ordinary native int/float/Unicode semantics; exact current static metadata/history version literals; structural-versus-numerical boundary; safe errors/no decoder context; no global hooks/I/O/science imports; independent tests and measured local resource evidence.

The scanner-precount/native-encoder equality is an explicit oracle to falsify, not a claim already proven by implemented tests. A hostile input rejected before materialization must be observed as such. Root depth differs from any future shifted adapter envelope; no eligibility is inherited from parser success.

## Scope and non-claims

Current authorized paths are ONLY new docs/design/features/physical-json-boundary/{research,requirements,design,contracts,validation-plan,tasks,review-packet}.md. Baseline7e26d253ac7d3a3688cb6263f669a747681aa077. No existing tracked file, module/test, original data, dependency, API/frontend/parser/runtime/provider or other worktree changed. The previous course branch/reference remains be4ec1cea4a02c25829ec902fbc86e53d313fe30; eleven protected untracked diagnostic directories are excluded, never staged or deleted.

Future module/test paths are proposals only. No API, storage, jobs, bundle, UI, browser/device/host admission, provider/field eligibility, physical-vertical activation, method acceptance or release is authorized. The larger M01 vertical SDD hard holds remain intact; this unit is not a waiver or alternate activation route. No merge/deploy is requested.

## Current validation record

Actual docs-only validation on 2026-10-03, CPython3.12.10 Windows, with all seven new paths staged so tracked guards included them:

```text
python scripts/check_content_standards.py : PASS
python scripts/check_template_residue.py : PASS,849 tracked files
python scripts/check_ci_budget.py : PASS
python scripts/check_sdd_convergence.py : PASS, structural ledger only
git diff --cached --check : PASS
read-only PowerShell scope/link/EARS/matrix/source/exclusion audit : PASS
```

The audit checked exactly seven added Markdown paths/no existing modifications,14 unique requirements and14 Gate lines with named matrix controls,21 resolved relative Markdown links, exact inspected core/adapter hashes, absent prospective module/test, unchanged coursebe4 ref and11 protected untracked diagnostic directories excluded. The unchanged product ledger still records zero whole-requirement passes,18 unresolved and one failed: its structurally valid receipt is not parser/scientific/release acceptance. No scripts/check_sdd.py exists; none was claimed run or added.

Initial seven-doc milestone f5bb0344bc475a5ccad42f67fe327d39dcfce8f9 was committed/pushed and draft PR127 opened against develop. This follow-up records that persistence only; the exact final commit/remote pin and self-review are in the PR handoff without a self-referential source hash. All helper/negative/numerical/local resource gates remain NOT_RUN. Product/API/frontend/browser/host suites were not executed for this design-only/no-activation instruction. Prior core/adapter/MT/course receipts are not relabelled as this unit's evidence.
