# Combined FWI and refreshed MT assembly audit

Date: 2026-10-03. Before implementation, following the READY contract in
[handoff](handoff.md). Develop `afac8ab` and PR100 `0970a09` have been integrated
conflict-free into this task branch only. The external candidate is read-only.
Its handoff document is now read from the exact merged PR100 bytes because the
provided MT checkout no longer contains that document; its candidate remains
available. No previous candidate or canonical receipt is replaced.

## Selection and fail-closed controls

The wrapper will accept an explicit MT input directory and independently pinned
receipt SHA `76ef56e96c4d287906bfeade956e04099c26bd3fa19c4a06b048438180744fd2`.
Before copying, validate the receipt, 24 unique expected paths, partial catalog,
release, original reference hashes and actual current-source fingerprints.
Verify all seven relevant producer/checker sources against the combined tree.
The MT producer's unrelated seismic hash intentionally differs; record this
difference, never substitute it. Producer Torch 2.12 CPU and independent replay
Torch 2.14 CUDA runtimes must remain separately attributed.

Only MT with this verified fresh contribution may bypass the unchanged-family
reuse rule. Select 72 unchanged conditions with baseline module/byte proofs,
24 previously executed precision-10 FWI conditions and 24 fresh MT conditions.
Do not reconstruct provenance, solve settings, seeds, metrics or verdicts.
The frozen plan rechecks all inputs/tools immediately before assembly, and
the original full catalog builder and artifact gate remain unchanged.

Verify fresh cl061 and manifest bytes against the pinned receipt and actual EDI
parser. Require the manifest outside `field_screens` to equal the validated
baseline manifest. Copy the supplied manifest only with that equality proof;
retain all original synthetic fixture/calibration/model bytes. Those historical
auxiliary receipts are reuse, not newly executed calibration. The full pipeline
tests independently exercise their present-source physics. Never redistribute
the measured original cl061 file, which is read for independent screening only.

## Independent acceptance

Create `data/experiments/fwi-mt-full-candidate-20261003-run1` and sibling receipts;
refuse existing output/plan/report paths. Run the unchanged full artifact gate
on this explicit destination, all pipeline tests (API host is separate), the
original nominal-reference solves plus new FWI/assembly/MT tests, 48 CUDA FWI
replays, and the unchanged MT condition and field replay functions against the
full candidate. MT's existing CLI intentionally requires a partial catalog, so
a separate full-candidate orchestrator will check 20/120/348 and call those
same numerical functions, including 3,072 actual conditional bootstrap refits.
No partial-catalog gate is weakened. Record source hashes, commands, runtime,
full inventory, objective-state counts, all scientific nonpasses, and canonical
tree digest before/after. Add adversarial fresh-MT assembly guards.

Compatibility metadata remains 0.04.001, unpublished, not an assigned release.
The scientific source correction requires the next release version during the
owner's actual release, not an overwrite of the old main claim. Main owns
canonical import, independent review, release readiness and convergence notes.
R008 failure and 18 unresolved requirements remain historical/product scope.
