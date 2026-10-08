# Original station-column input control

The protected direct-source codec compares actual station CSV rows to the
closed magnetic request, not just two matching hash strings. Its numerical
test input is produced by `tests/data/test_magnetic_original_csv_control.py`.
It writes an authored 288-row ENU null acquisition, binds its original SHA/count
and exact column declaration, then calls the real supplied-file CLI with the
public original-noise binding and unchanged scientific caps. It does not write
a prebuilt successful generation. Source/optimizer failures cannot become a
replay fixture or a skipped test.

The explicit files are `original.csv`, `request.json`, `binding.json` and
`physical-columns.json`. The exact declared columns are row, line, E_m, N_m,
U_m, bE, bN, bU. Output is a complete actual local numeric generation plus its
retained optimizer audit. All data/scratch/pytest outputs must use supplied
external device roots. This test changes no optimizer or scientific policy.

This is intentionally a null seven-active-cell codec/custody control. Its actual
241 native solves over the unchanged eight-beta L2/IRLS nested workflow do not
qualify the original NONZERO 528-cell case, field truth, native-host resource or
online admission. The original complete-firstfit wall-cap failure remains
failed; unchanged-source prerequisites refuse before launch. Protected custody
and client tests consume these genuinely produced bytes but cannot promote
their false full-method/field/geology/online claims.

Portable invocation, with the approved M04/public-original/line source roots
configured in PYTHONPATH and a one-thread scientific environment:

```text
python -B -m pytest tests/data/test_magnetic_original_csv_control.py -x -q
  -p no:cacheprovider --basetemp <external-new-test-directory>
  --junitxml <external-new-directory>/actual-csv.xml
```

The test tool deadline is 120 seconds; it is not an extension of any scientific
fit cap. Exact source/control receipts and device paths are operational evidence,
not fields embedded into the public scientific protocol.
