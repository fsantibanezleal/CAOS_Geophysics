# Launch the two frozen M12 protocols

Add one literal protocol selector to the existing external-output shim.
Historical-v1 remains the default and retains its existing argv. Physics-v2
selects velocity_physics_refinement.py, whose CLI fixes forty training epochs
and has no epochs argument. A supplied non-forty epoch count fails before child
execution, including verify mode, rather than being silently discarded.

The shared path check remains before scientific import. The shim does not
import NumPy, Torch or either module, modify their source, normalize receipts,
train during tests or fabricate evidence. Verify forwards only --verify;
training forwards device and optional fixture, never an unsupported parameter.
Both scientific modules preserve source-bound historical receipt verification.

PowerShell exposes a closed Protocol parameter and POSIX forwards M12_PROTOCOL
to the same parser. A checkpoint, output directory and compute environment
remain operator inputs, not committed repository artifacts. The existing
physics-v2 negative held-out comparator remains explicit.
