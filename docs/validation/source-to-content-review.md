# Source-to-content review: M01–M13 methods wiki

**Review date:** 2026-10-25

**Scope:** repository wiki chapters for methods M01–M13 and their links to the approved product SDD, implementation, tests, and method-specific requirements.

**Status:** bilingual structural and token-parity review passed; scientific/source-rights/product acceptance remains open.

## What was checked

`python scripts/check_docs_matrix.py` requires the English and Spanish M01–M06 and M07–M13 chapters, every method heading exactly once per language, displayed equations, assumption/limitation language, reproducibility and reference sections, implementation/test path density, valid local Markdown targets, and exact translation parity for equations, code, technical identifiers, links and numeric tokens. This is an executable completeness floor for navigation and traceability, not an automated science reviewer.

At this review the structural command passed for English and Spanish M01–M13 chapters. Spanish companions preserve display equations, fenced code, inline technical identifiers, link targets, and numeric tokens exactly; those parity checks run in the command. Both languages were inspected for explicit evidence boundaries, equations and units, eligibility or rejection controls, implementation and test pointers, reproduction commands or `UNAVAILABLE`, limitations, and primary-source links. The chapters distinguish authored synthetic cases from field data and mark unavailable acquisitions or workflows directly. The second chapter records M04's absent survey inverse, M05's QC-only Clear Lake `cl061`, M12's failed comparator result, and M13's remaining rights and product-release limits.

## Evidence that remains outside this check

- Correctness of every scientific derivation and parameter interpretation requires domain review and independent numerical or physical oracles.
- A repository path and a passing test do not establish complete user workflow, field accuracy, user-provided-data support, or host behavior.
- External links can change or be unavailable; URLs are not proof that a dataset was acquired, legally accepted, or correctly interpreted.
- The SDD's method and release gates remain authoritative. The current convergence ledger has unresolved requirements; this review does not mark any of them accepted.

## Reproduction

```powershell
.venv-pipeline\Scripts\python.exe scripts\check_docs_matrix.py
.venv-pipeline\Scripts\python.exe -m pytest tests\test_sdd_convergence.py -q
```

Record a new review when chapters, methods, source decisions, or the SDD change. A structural pass alone must never change the convergence verdict to accepted.
