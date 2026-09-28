# M13 real-waveform task gates

- [x] Pin and hash-verify the STEAD metadata; reject its published trace-level split for event/station independent claims.
- [ ] Finish waveform download, verify exact bytes and SHA-256, and record HDF5 format/source receipt.
- [x] Select event/station-disjoint quake and station-disjoint noise inventories by fixed metadata-only hash rule; validate the full manifest and report exclusions. This is metadata-only: 60,000/5,000 training quake/noise, 5,000/1,000 each for dev and untouched test. Of 1,265,657 rows, 498,116 passed strict manual-label/noise and split eligibility; 44 had unsupported identity/slice and 275,132 candidate quakes lacked two manual picks. No waveforms were opened.
- [ ] Verify bucketed HDF5 reader against real source traces and an independent SeisBench read.
- [ ] Train an actual GPU model from scratch with recorded seed, configuration, environment, optimizer, losses and checkpoint hash; choose threshold on dev only.
- [ ] Run M08 and M13 on identical untouched real test traces, preserving misses and noise false alarms; report stratified timing and degradation.
- [ ] Export that exact checkpoint for the browser; verify local/browser probability and peak parity on the same held-out traces.
- [ ] Approve source and derivative rights, then release a small attributed real-trace case only if all gates pass.

The PhaseNet 100-trace sample is an engineering fixture, never training or benchmark evidence. No box after the first is checked by a static build or metadata profile.
