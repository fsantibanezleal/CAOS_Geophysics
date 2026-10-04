# M08 resumed local review packet

This is a **tested local milestone**, not full method/platform acceptance. Work is on `task/geophysics-m08-waveform-sdd`, draft [PR142](https://github.com/fsantibanezleal/CAOS_Geophysics/pull/142) into develop. Baseline is b2611ad. First milestone9a9bc3cb1f947da0e1afce4b150f72a277d6de70 committed and pushed the original terminal seal before the separate phase request. No merge/deployment is performed.

## Ownership and complete new work

The four pre-existing dirty M08 files were preserved and their relevant fixes included in the scoped milestone, not reverted or claimed as newly authored: two ordinary modules and two tests. Additional seal changes are test-first. New files are the exact original gate, direct-window held-out test, two compact attributable waveform artifacts, current feature evidence/review docs, and the deep repository waveform chapter with its diagram. The wiki index links the chapter. No unnamed package, dependency installation, acquisition client in the scientific modules or CLI hook was added.

Waveform processing itself is unchanged from b2611ad. Existing frozen comparator, model, STEAD input/cohort/benchmark/browser assets, source ledger, canonical manifests, app/API/worker/database, frontend and native-accounting sources remain byte-for-byte outside the change. Eleven old diagnostic directories remain untracked and excluded. Native I01 WIP remains paused in its own worktree.

## Actual execution, attributable receipts

[Local evidence](evidence/continuation-local-tests-20261003.json) pins actual interpreter/version, native engine binary bytes, the three ordinary module bytes, four test files, artifacts and private XML receipts. It records **Windows local execution**, not Linux/native-host or cross-platform parity. The selected interpreter is the existing ingestion worktree's `.venv-m08-oct3/Scripts/python.exe`, CPython3.12.10, SHA0b471133e110cfb53a061cad528ce8e517d7b9ac41a0a396c39ad795a487fc14; NumPy2.2.6, SciPy1.15.2, ObsPy1.4.2, pytest9.0.3, setuptools81.0.0. No environment was modified. Ruff is the already installed, read-only MT tool, SHA672f56ff9556c15d2d84f091094f2af853cb7ec09204935ba43119735944f56e, used only on owned paths; it does not supply numerical dependencies.

The final scoped M08 command is:

```powershell
$env:PYTHONDONTWRITEBYTECODE = '1'
$env:CAOS_M08_ORIGINAL = '1'
$env:CAOS_M08_PHASE = '<explicit-private-phase.raw>'
.venv-m08-oct3/Scripts/python.exe -B -m pytest tests/data/test_waveform_input.py tests/numerics/test_waveform_picks.py tests/data/test_waveform_ridgecrest.py tests/numerics/test_waveform_heldout.py -q -p no:cacheprovider --basetemp <fresh-external-root>/tmp --junitxml <fresh-external-root>/unit.xml
```

The actually retained private evidence root is identified in the JSON receipt; no hostname, absolute source path, raw samples or traceback is copied into public evidence. XML SHA identifies each retained producer receipt. Original tests read only the exact already acquired source files and explicitly supplied catalogue; they perform no network. Without the two opt-in settings they skip, not silently acquire a replacement. Fresh-output/temp paths must be absent; existing evidence is never overwritten.

## Test-first failures and fixes

- Existing preserved baseline:63PASS. Three seal adversaries actually failed before the fix (`seal-red.xml`): matching-hash nonfinite arrays, unregistered arrays/QC physical products and oversized output. Typed registered descriptor caps precede array checks; finite values, aggregate metadata+array bytes and native request identity are rechecked. The oversized-count fixture is intentionally outside the scientific sample bounds; it is not an admitted33MiB dataset.
- Held-out first RED: a seconds-conversion oracle used division instead of the comparator's fixed index*0.01 dialect, and the new artifact was absent. The correction preserves the existing operation and exact onset indices; no epsilon or acceptance tolerance was added. The QC-rejected source row has no waveform keys; absent fields are retained rather than fabricated null source bytes.
- A final evaluation adversary actually passed for start truncation but failed for end truncation (`truncated-red.xml`). The correction implements the approved nontruncated matching policy for both flags. The original0.5s matching tolerance and greedy one-to-one order are unchanged.
- Missing ObsPy import is explicitly exercised as unavailable, fixed waveform_engine with no chained exception/decoder call; unknown rights still produce QC-only before scientific engine use. This is not a resource-supervisor gate.

## Executed science and retained field outcomes

The new authored worked artifact uses actual native response removal, SOS filtering, spectra and interval computation on identical authored integer count bytes. Gain×2 gives motion×1/2 and PSD×1/4. Filter2..10→6..10Hz changes the signal/PSD; threshold3.5→5 changes interval times without changing physical arrays; guard5→9s changes the mask and the expressly changed analysis interval. Candidate phase/uncertainty remain null. Authored burst boundaries are not analyst labels or field observations.

The already inspected, preselected STEAD display cohort is replayed read-only:23 valid same inputs, one retained QC failure, exact comparator/direct-window onset agreement and maximum CF difference4.496007975640648e-10 under the unchanged1e-9 control. Scientific failure remains2/16 P and0/16 S within0.5s, seven noise P and six noise S guesses. This is not a new untouched study, not the new response-corrected lane and not M13 inference or a rerun of all6000 records. Existing broader evidence remains separately attributable.

The selected original Ridgecrest case actually rejects its original XML declaration before any scientific engine. Eight original records contain18001 samples including the provider endpoint; none are repaired, decoded into a substituted result or cleared by adjacent-stage unit inference. After the committed terminal seal, one exact HTTPS catalogue object was bounded-read, hash-checked and kept privately. Its original ten-token header is outside the frozen nine-token admitted STP subset and remains reference_unsupported. No guessed conversion or residual is published. The one selected rejected case and unsupported reference stay in the inventory.

## Coverage and unresolved release obligations

| Requirements | This milestone | Limitation |
| --- | --- | --- |
| 001..007 | Actual exact-byte/header/XML/time/epoch/units/flags controls | Native preflight is not hostile decoder isolation or all possible instrument dialects |
| 008..013 | Actual real-format authored native calculations plus independent numerical/parameter controls | Not response-corrected field calibration |
| 014 | Authored source conversion/matching controls, immutable result seam, both truncation negatives | Original field catalogue dialect rejected; no original timing score |
| 015 | Exact original and terminal rejection actually replayed; conditional later phase access retained | Positive field gate unmet; original public redistribution still unapproved |
| 016 | Ordinary helpers contain no acquisition/filesystem/CLI hooks | CLI is unimplemented and held |
| 017 | Finite typed/read-only descriptors and seal bounds tested | Directory writer/independent reopen unimplemented and held |
| 018 | NOT_RUN/CLOSED | No crash/timeout/cancel/native process-tree telemetry or device profile |
| 019 | Frozen source checks and scoped git review | No new M13/model/cohort/manifest/host acceptance |
| 020 | Missing-engine/rights paths tested and limitations explicit | Resource/private-source release gates remain separate |

No scientific acceptance threshold changed. The full feature and platform scope remains intact: this PR must not claim acceptance by omitting CLI/export/resources/positive field work. Auth/admin/production backup are deferred by the human user, not silently replaced by a single-user application. No host access, production changes, service/controller action, model override or agent creation occurred. A compatible field source/admitted original dialect requires reviewed design/rights work; source repair or a convenient replacement is not implied by this milestone.

## Self-review boundaries

The matching/descriptor tests exercise real negative states; they do not authenticate a caller-authored seal. Compact worked hashes are deterministic for the measured Windows engine closure; this is not a Linux ABI/recomputation claim. The SVG is structurally bounded repository documentation, not a tested web widget or browser-render acceptance. Source rights remain attributed: STEAD CC BY4.0 from the upstream licence, SCSN restricted to its stated public-data terms and exact CI acquisition, never inferred from a software MIT licence. Full MAIN/independent review and promotion remain pending.
