# MT uploaded-workbench browser validation

Date: 2026-11-06. This is local, isolated browser evidence for the uploaded MT
workbench. The API and worker ran from the read-only product checkout at
`7d5c9de24cbf05fdb56eade50b4d955f8dd5016f`; only the test harness and test
assertions changed in this validation work. `GEOPHYSICS_MT_ONLINE_ENABLED` was
enabled only for loopback QA. No public or VPS admission was enabled.

## Results

Five distinct browser cases passed across two recorded runs. They were not all
green in one invocation:

- The full five-case run at `E:\_Datos\CAOS_Geophysics\validation\mt-workbench-current-20261106-release`
  passed the owner upload/M05-M06 calculation, layered-parameter sensitivity,
  plot interaction, and the EN/ES light/dark 4-viewport screenshot matrix (618
  evidence files). Its Clear Lake case reached and passed the pinned-byte check,
  the real QC-only job, and the disabled-inverse assertion, then failed on a
  test that expected an undocumented chart `data-y-max` attribute.
- After replacing that assertion with the actual UI contract, the focused run at
  `E:\_Datos\CAOS_Geophysics\validation\mt-workbench-current-20261106-qc-final2`
  passed its four selected cases: upload plus M05/M06, layered parameter effect,
  pointer/keyboard/zoom and unit controls, and the real Clear Lake QC-only,
  malformed-input, cancellation, status-recovery, and logout path. The Clear
  Lake comparison screenshots cover EN/ES, light/dark, and 1280, 1600, 2560,
  and 390 pixel widths. Its `run-receipt-enabled.json` records four passes and
  zero browser errors.

The full run receipt preserves its one harness assertion failure; the focused
receipt preserves the later passing Clear Lake run. Read them together and do
not report this as a single clean five-test run.

## Scientific and data boundary

The synthetic layered EDI jobs exercise the actual API and worker. The test
checks method output, parameter-dependent models, result export verification,
frequency/period navigation, signed residual display, and accessible layer
selection. They do not establish geological model recovery. The Clear Lake
original was read from the private local data root and verified as 16,411 bytes
with SHA-256
`90c5c96cd69d6d29c866a768097cb3b38bc20e8b9c143e24bf10b2d253261e83`. Its
actual full-tensor screen fails; the browser confirms QC-only output, no inverse
model view or job admission, and no change to that QC result when marginal SD
bars are hidden. The data remains outside Git.

All test databases, screenshots, ZIPs, traces, and JSON receipts were directed
to `E:\_Datos\CAOS_Geophysics\validation`. These are local QA results, not
independent scientific review, host acceptance, public activation, or
product-wide uploaded-method acceptance. R-005 remains unresolved for complete
browser coverage of every supported uploaded modality and hosted execution.
