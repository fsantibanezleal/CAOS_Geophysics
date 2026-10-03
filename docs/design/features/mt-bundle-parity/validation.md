# MT bundle parity verification

Windows Python 3.12.10, read-only existing pinned MT environment. No environment, original export, solver or canonical artifact was changed. Before the fix, the new one-ULP near-zero regression failed with the same `M06 predicted or residual array mismatch` as the actual Linux export. After the fix, the near-zero and existing full bundle controls pass (2 tests, 25.41 s). Rehashed prediction-plus-matching-residual corruption, residual-only corruption, nonfinite and wrong-shape variants reject; ownership, uncertainty and units controls are unchanged.

Full command: `.venv-online-mt-oct3/Scripts/python.exe -m pytest tests/api -o addopts= -q --tb=short`, using the explicit interpreter in the existing ingestion worktree and cwd this isolated parity tree. Result: **84 passed, 2 opt-in skips, 194.27 s**; upstream TestClient deprecation warning remains. The opt-in local benchmark and original privately downloaded field control are not silently counted as passes. Ruff and scoped whitespace checks pass.

Independent actual-Linux controls are retained privately in `D:/_worktrees/geophysics-host-admission/data/raw/host-admission/mt-controls-65132e9`. All five original ZIPs now pass `app.bundle.verify_bundle` on Windows. Exact source/size/ZIP hashes are persisted by the separately reviewed host-admission evidence. The test imported stored bytes only; it neither regenerated Linux source bytes nor relabelled runtime identities.

The prediction check still uses the existing `1e-7` relative and `1e-19` absolute allowance. The residual check still uses that allowance but verifies the actual contract `observed - exported_prediction`. The independently checked prediction prevents substituting a different physical response while the exact subtraction prevents platform cancellation from masquerading as corruption. The fix is a verifier correction, not an observational-noise tolerance or improved inversion efficacy claim.

This unit has not merged or deployed. The complete host gate remains failed on disk headroom and full product convergence remains open.
