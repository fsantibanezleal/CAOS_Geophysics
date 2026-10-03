# STEAD metadata source reconciliation

The early acquisition foundation deliberately had only a user-reported lead. The later approved phase pipeline acquired and profiled the original metadata. This extension supersedes that narrow historical limitation without changing waveform bytes, training, frozen holdouts or redistribution decisions.

- SS-01 THE ledger SHALL distinguish user-reported-unverified links from independently locally verified metadata, without turning either into a raw acquisition or mirror.
- SS-02 WHEN verified metadata is declared, THE loader SHALL require a hash-checked tracked aggregate profile, bind its schema/source URL/byte count/raw SHA to the entry and reject missing, tampered, unsafe or inconsistent evidence.
- SS-03 THE extension SHALL preserve provider-link-only rights, no raw storage key, no general fetch-host expansion, and no waveform/training/generalization claim from metadata verification.
- SS-04 THE independent main review SHALL re-hash the actual 402,560,190-byte metadata in the phase worktree, match its existing profile, and persist the verification without publishing private originals.

Gates: source-loader verified/unverified/rehashed-drift controls in tests/data/test_sources.py; unchanged source/ingestion/raw-tracking suite; independent full-file SHA-256.
