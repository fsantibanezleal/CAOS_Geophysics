# Fixed native launch boundary

The interpreter that supervises a worker and the interpreter executing the
scientific worker are separate identities. An installed virtual-environment
redirector may establish a Windows Store package context for its parent, but
must not be reported as the scientific Job's executable. The executing image
is measured with `GetModuleFileNameW` and hashed independently. Paths are
operator arguments, not repository defaults or downloadable executables.

The fixed worker invocation remains `-B -S <fixed sibling worker> --packages
<installed packages> --job-handle <inherited Job> --plan <owned plan>`.
No application alias, submitted script, import hook, shell command or client
callback supplies scientific execution. The controller creates a suspended
process, assigns its single-process Job before resuming, and retains actual
CPU, committed memory, RSS, disk and terminal process counters.

## Value-free prerequisite

`scripts/run_m03_native_context.py` requires the shared dispatcher's actual
process ancestry. Its parent-executable argument must match the registered
redirector digest. The native parent must be CPython 3.12.10 and have the
registered real-image digest; the same digest binds the scientific child.
The native worker receives only the literal empty JSON plan. It must prove
Job membership before returning `invalid_contract` at `seal`, exit 2.
That expected refusal is a component prerequisite, not scientific success.

| Boundary | Enforced prerequisite ceiling | Required observation |
| --- | --- | --- |
| Scientific child | 10 CPU seconds; 30 wall seconds | Positive measured CPU, terminal exit 2 |
| Native supervisor | 10 CPU seconds | Measured parent CPU, no excess |
| Memory | 512 MiB RSS and committed memory | Both measured and within the ceiling |
| Owned scratch | 16 MiB | Exact positive measured bytes, including terminal receipt |
| Process containment | One scientific child | Total one; active zero after drain |

The bootstrap has a separate 45-second deadline. Its wall time, exit and
receipt digest are retained separately; it is not subtracted from a later
native lifetime or counted as the scientific Job's child. The prerequisite
launches the Store parent from its external owned output directory before
interpreter initialization. Platform activation caches therefore cannot land
in the source checkout. The version-2 bootstrap drain separately inventories
all bytes in that directory, including its own serialized receipt and any
platform cache. An exact serialization fixed point and an independent final
inventory must agree within the existing 16 MiB prerequisite ceiling.
This outer inventory is not substituted for scientific-child scratch.
The prerequisite
opens no CSV, array, magnetic value or outer partition. Missing executable,
failed process creation, incorrect refusal, unknown drain or counter failure
cannot become a PASS. No zero lifetime is invented for an uncreated process.

A new parent-context fingerprint must qualify before any cold reproduction.
The original failed launch, original numerical tolerances, solver/source
bytes, required 97 fits, earlier predictive failures and already-opened outer
status remain unchanged. Successful launch proves neither original-field
eligibility, scientific predictive validity, Linux hosting nor activation.

## Closed reproduction bootstrap

The dispatcher continues to execute ordinary CP313. Its existing refusal of a
Store virtualenv as a node executable is preserved. The reproduction driver
may invoke only the registered redirector as an internal native-parent
bootstrap in the same inherited dispatcher Job. The scientific child is still
the original explicit native image, suspended and assigned to its own unchanged
single-process Job before resume. There is no breakaway or separate dispatcher.

Before bootstrap, the driver validates the actual value-free startup receipt,
expected refusal, complete drain, native and redirector identities and frozen
scientific source pins. Before science, the native parent measures its own
image and exact Python version. The bootstrap seal binds the fixed argv,
receipt digest, actual shared-lock ancestry and wrapper source digest. Its
terminal exit and wall time remain separate from both native fit and cold
verification lifetimes. A 1750-second bootstrap deadline sits inside the
unchanged 1800-second dispatcher ceiling; original native caps are unchanged.

Reproduction requires all 97 original identities, exact complete Result byte
equality and cold selected-model verification. It is explicitly reproduction
of an already-opened authored diagnostic, never a new untouched outer test or
an owner job created by rewriting that diagnostic's run ID.

## Espanol

El contexto padre de un entorno virtual no es la identidad del ejecutable
cientifico. Se mide y verifica la imagen real; el trabajador fijo demuestra
la pertenencia al Job antes de rechazar el plan vacio. El rechazo esperado
prueba solamente el inicio contenido. No abre datos ni modifica los 97
ajustes, tolerancias o fallos predictivos anteriores. Los contadores ausentes
nunca se inventan y el despliegue sigue siendo una validacion independiente.
El padre se inicia desde su directorio externo antes de activar el interprete.
El recibo version 2 cuenta todos los bytes del inicio, incluidas las caches
de plataforma y el propio recibo, con el mismo limite de 16 MiB. Este conteo
no reemplaza los contadores independientes del trabajador cientifico.
