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
opens no CSV, array, magnetic value or outer partition. Missing executable,
failed process creation, incorrect refusal, unknown drain or counter failure
cannot become a PASS. No zero lifetime is invented for an uncreated process.

A new parent-context fingerprint must qualify before any cold reproduction.
The original failed launch, original numerical tolerances, solver/source
bytes, required 97 fits, earlier predictive failures and already-opened outer
status remain unchanged. Successful launch proves neither original-field
eligibility, scientific predictive validity, Linux hosting nor activation.

## Espanol

El contexto padre de un entorno virtual no es la identidad del ejecutable
cientifico. Se mide y verifica la imagen real; el trabajador fijo demuestra
la pertenencia al Job antes de rechazar el plan vacio. El rechazo esperado
prueba solamente el inicio contenido. No abre datos ni modifica los 97
ajustes, tolerancias o fallos predictivos anteriores. Los contadores ausentes
nunca se inventan y el despliegue sigue siendo una validacion independiente.
