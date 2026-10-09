# M12 protocol launcher tasks

- [x] ML-01/ML-02: implement closed selector and unchanged scientific argv.
- [x] ML-03: expose selector in both existing launchers.
- [x] ML-04: correct repository-output reproduction instructions.
- [ ] Run actual CLI refusal and authored forwarding controls under frozen source/runtime bindings.

No new training or learned-advantage acceptance is inferred from these gates.

## Actual verification and retained failures

The original 25-control source-frozen gate passed, report SHA-256
`46ce244d3c6be0c0e01be39424240fd8aca04f4740a2d03d3ecee9bdfbd8f0df`.
An additional actual PowerShell verify/epochs control then exposed a missing
forwarded epoch argument. The wrapper correction is covered by 26 passing local
controls, zero failures/errors/skips, 5.936 seconds, JUnit SHA-256
`a2ea3f993ae0adf32e1c7cc419825626a621fc99d1dcd6f2df994a475b6dcc82`.

The first frozen follow-up failed because its minimal Windows environment omitted
PATHEXT; actual PowerShell did not execute Python normally. A three-case native
check reproduced the failure with the declared environment and reached the
expected frozen-protocol refusal after adding PATHEXT alone. The original failed
receipt remains retained: report SHA-256
`7b1096ce63a76c9a2b06862e12ef27a3d9658eff85055a004b0d70c6f2c038f1`.
The corrected declaration preserves Windows execution/path variables. Its
inventory then raised MemoryError before executing tests; no new frozen PASS,
runtime acceptance or scientific result is inferred. No assertion was relaxed.
