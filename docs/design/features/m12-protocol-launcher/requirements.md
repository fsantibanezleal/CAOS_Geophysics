# Explicit M12 protocol launch

Status: planned. Scientific protocols and retained checkpoints are unchanged.

ML-01 THE launcher SHALL select only the literal historical-v1 or physics-v2 module, after explicit external output validation and before scientific imports. Gate: `tests/ops/test_m12_launcher.py::test_actual_cli_refuses_before_science` and `tests/ops/test_m12_launcher.py::test_exact_physics_protocol_forwarding`.

ML-02 WHEN physics-v2 training is requested, THE launcher SHALL preserve its fixed forty-epoch protocol and refuse an alternative epoch count instead of silently ignoring it. Gate: `tests/ops/test_m12_launcher.py::test_physics_epoch_change_is_refused_before_science`.

ML-03 THE Windows and POSIX launchers SHALL expose explicit protocol selection without changing the historical default or allowing repository output. Gate: `tests/ops/test_m12_launcher.py::test_powershell_requires_explicit_output` and `tests/ops/test_m12_launcher.py::test_bash_requires_explicit_output`.

ML-04 THE instructions SHALL retain negative comparator findings and distinguish real GPU training from launcher validation. Gate: `tests/ops/test_m12_launcher.py::test_physics_documentation_uses_external_launch_and_keeps_negative_verdict`.
