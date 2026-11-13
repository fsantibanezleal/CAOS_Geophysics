# Verify served release identity and account boundaries

## English

Use the completed frontend build that was independently tested. Invoke the repository interpreter with explicit absolute paths:

```text
python scripts/verify_single_vps_release.py --origin https://YOUR-CANONICAL-HOST/ --build ABSOLUTE-BUILD-DIRECTORY --output ABSOLUTE-NEW-PRIVATE-RECEIPT.json
```

The command performs read-only HTTPS GETs. It compares every build member's byte count and SHA256, all six SPA route documents, the local-account discovery response and anonymous401 on the private project API. Certificate/hostname validation stays enabled, redirects are refused, and responses are bounded. It sends no password, cookie, upload or compute request. It neither deploys nor deletes anything. An already occupied output path is rejected.

An optional `--host-inventory ABSOLUTE-PRIVATE-INVENTORY.json` checks the exact capacity contract in [the design](../design/features/single-vps-verification/design.md): a fresh operator-reviewed measurement, current plus two distinct rollback releases, and disk/RAM reserves for additional release and active jobs. The checker does not collect or authenticate that host measurement. Existing occupied project/release bytes are already reflected in measured free capacity; no arbitrary percentage or off-host-backup requirement is added.

Successful byte/access verification is not scientific, browser, worker or full-release acceptance. These four receipt flags remain false. Complete acceptance requires separately measured method, user-data, ownership, UI, real worker containment/admission, retired-publication and rollback evidence. A remote API fallback to HTML, missing account policy, wrong artifact or failed transport stops verification. Keep the private failed observation and investigate its cause; do not replace it with the legacy static-only verifier as an acceptance shortcut.

## Español

Use el mismo build del frontend que fue validado independientemente, con rutas absolutas para el directorio y un recibo privado nuevo. El comando anterior solo realiza solicitudes GET por HTTPS: compara bytes y SHA256 de todos los archivos, las seis rutas de la SPA, la configuración de cuentas locales y la respuesta401 de proyectos sin autenticación. No envía contraseñas, cookies, archivos ni cálculos; no despliega ni elimina datos. Rechaza redirecciones, respuestas demasiado grandes y destinos ya existentes.

El inventario opcional comprueba un registro reciente revisado por el operador: versión actual, dos versiones distintas para reversión y capacidad real de disco/RAM para la publicación y los trabajos activos. No mide ni autentica el servidor. No exige correo externo, respaldo externo ni un porcentaje arbitrario de espacio libre.

Una comprobación positiva de bytes y acceso no valida los métodos científicos, el navegador, el worker ni la publicación completa. Los cuatro indicadores de aceptación permanecen falsos. Se requieren pruebas independientes de métodos, datos del usuario, propiedad, interfaz, límites reales del worker, ausencia de la publicación retirada y reversión. Un fallo conserva su significado; no se convierte en éxito mediante una comprobación estática más limitada.
