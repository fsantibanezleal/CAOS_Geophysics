# Verified numeric replay and export / Reproducción y exportación numérica verificadas

## English

This local leaf renders a complete fitted generation, not a browser inversion.
The parent selects an owned job/dataset and supplies its independently stored
receipt. Source ID, original SHA256, configuration SHA256, generation SHA256,
job UUID and dataset UUID must all agree. Native numeric descriptors are checked
again with WebCrypto; changing a number while keeping its old hash rejects.
The API owner must verify retained NPY/member bytes before projection; response
metadata alone cannot establish original custody. The unapplied
[owner mount proposal](../../design/features/m04-survey-inversion/owner-mount-proposal.md)
defines that seam without registering a new service method or enabling online use.

Map, original flight and signed residual views retain all original row IDs,
coordinates, groups and component order. Residual is observed minus predicted
in nT, not an absolute value, interpolation or arbitrary display normalization.
Excluded data are not replaced with fabricated coordinates. The susceptibility
volume uses actual nonuniform widths, ENU origins and active Fortran index
`i+nx*(j+ny*k)`. Faces/depth slices occupy physical cell extents; susceptibility
is dimensionless SI and cell volume is m³.
The orthographic camera uses one metres-to-pixels scale on all three physical
axes, fits full mesh edges, and does not exaggerate vertical dimensions. Depth
slices likewise preserve equal horizontal metre scales, not centre-only bounds.
Its projection axes are orthonormal; screen foreshortening is camera geometry.
A zero null-control model has visible cell boundaries, not an invented body.
Rotation and slice controls alter replay
only; edited field, geometry or likelihood inputs require a new owned job.

Local point-spread is conditional linearized sensitivity/resolution around the
fitted model and the frozen regularization, not a uniqueness certificate or
field truth. A missing physical-parameter sensitivity export is explicitly
unavailable, never a zero curve. Objective history contains actual retained
iteration states, not an invented smoother convergence trajectory.

Spectrum is available only for an original group with at least three uniformly
spaced horizontal positions. It demeans the complete residual component,
applies a Hann window, and computes its one-sided DFT with cycles/m and nT² m.
The even-length Nyquist bin is not doubled. There is no resampling, hidden
thinning, absent-data interpolation or automatic physical validity inference.
Map/flight point selection retains the same original identity across views.
Shared-shell EN/ES language and light/dark tokens remain parent-owned.

Numeric export is a deterministic ZIP of the verified generation manifest and
all native NPY members; original provider bytes are excluded. Fixed ZIP member
timestamps, stored compression and regular-file modes make repeated export
byte-identical. Both export and import require explicit external destinations
and refuse overwrite. Import pins the complete bounded archive bytes once,
admits at most 65 unique safe leaf names and 128 MiB total uncompressed bytes,
and rejects paths, symlinks, special members, encryption and compression. Each
member is streamed with its declared bound, fsynced, and the manifest closes
last. Ordinary failure removes only files created in that fresh destination.
`read_bundle` then verifies every descriptor, member hash and generation seal.
This is local durability, not a privileged hostile-filesystem security claim.

The CLI is `scripts/magnetic_numeric_export.py export|import --input PATH
--output PATH --data-root EXTERNAL --temp-root EXTERNAL`. Authenticated exports
must reuse the existing owner-scoped derivative/export transaction and route;
the leaf export button exists only when its parent supplies that callback.
QA's actual download/reimport is not proof that the live parent route is mounted.

No view, successful ZIP round trip or zero-control browser gate establishes
nontrivial S2 convergence, complete field eligibility, host qualification,
physical API registration, publication or deployment. Original adverse controls,
failed candidates, solver caps and independent scientific thresholds remain.

## Selected-final saved model replay

Version1 contains recorded objective values and model hashes, not an animation
of model arrays. Its history control is labelled as objective records; training
folds, failed candidates and distinct fixed-surrogate objectives are not one
monotone final solve. Selecting a record never changes physical cells.

The explicit version2 result/view adds the closed
`magnetic-selected-final-model-states-1` member. The original driver's bounded
closed audit is read only AFTER a complete final refit has stopped. The extractor
keeps the selected candidate's final-refit initial model and actual accepted
native arrays, not trial steps or training models. Repeated stage-entry arrays
must equal the preceding final array exactly and are not duplicated. Every
retained array matches its exact original history index, q-model SHA256,
objective values, native source/epoch and final physical model. The complete
source inventory and audit byte hashes are retained. No new solve, callback,
fit clock or native allowance is introduced.

The physical conversion is $\chi=0.01q$, with dimensionless SI susceptibility.
The bundle declares separate little-endian float64 q/SI arrays and int64
history indices as ordinary hash-checked NPY members. Before reading or
materializing them, the extractor enforces the complete64MiB audit,16MiB line,
4096 record,2048 active parameter,201 saved state and8MiB numeric payload
capacities. The unchanged64 numeric-member/128MiB bundle limits also apply.
An oversized or incomplete sequence refuses publication rather than selecting
a subset or fabricating missing states. Legacy version1 remains closed.

The protected browser verifies each native descriptor and independently hashes
every q row against its mapped history hash. Saved-model selection is discrete:
only the chosen recorded SI array supplies the cell values, without interpolation
between geologies. The final saved model is initially selected. A one-state null
control has a disabled model scrubber and explicitly reports zero accepted
moves; it does not pretend to animate. Objective history remains a separate
control. Opacity uses the fixed0..0.1 SI range across states/cases, never a
per-case maximum or an uncertainty interpretation.

The genuine retained null audit verifies one selected-final seven-cell array.
This is extraction/replay evidence only. Authored two-state consumer controls
exercise index and hash grammar, not a measured nonzero fit. New complete
nonzero final-refit precision, frozen adverse cases, multi-state temporal
evidence, authenticated service assembly, shared-shell instrument occupancy
and native resource/cancel/crash qualification remain separate scientific and
product gates. No historical failed fit is relabelled by version2.

## Español

La vista local reproduce una generación ajustada completa; no invierte en el
navegador. El padre selecciona un trabajo y conjunto propios y entrega su recibo
persistido independientemente. Deben coincidir los seis identificadores: fuente,
SHA256 original, configuración, generación, UUID de trabajo y conjunto. WebCrypto
verifica otra vez los descriptores numéricos; cambiar un número con su hash antiguo
rechaza. El dueño de la API verifica primero los NPY retenidos. La propuesta de
montaje no registra un método público ni habilita procesamiento online.

Mapa, vuelo original y residuo firmado conservan IDs, coordenadas, grupos y orden
de componentes completos. Residuo significa observado menos predicho, en nT.
Volumen y cortes usan anchos no uniformes, origen ENU e índice Fortran real; la
susceptibilidad es SI adimensional y el volumen de celda, m³. La cámara ortográfica
usa una escala común en metros para los tres ejes, ajusta las aristas completas
y no exagera la vertical; los cortes conservan escalas horizontales iguales.
Rotar o cambiar
un corte sólo modifica la reproducción. Cambiar campo, geometría o verosimilitud
exige un trabajo nuevo; no se fabrica un cuerpo para el control nulo.

La dispersión puntual es resolución linealizada local y condicionada, no prueba
de unicidad o verdad de campo. Sensibilidad física no exportada figura como no
disponible, nunca como cero. La historia contiene estados realmente retenidos.
El espectro requiere un grupo original completo con al menos tres posiciones
horizontales equiespaciadas: residuo sin media, ventana Hann y DFT unilateral,
en ciclos/m y nT² m. No se duplica Nyquist par ni se interpola o diezma.

El ZIP numérico determinista contiene manifiesto y todos los NPY verificados,
sin originales del proveedor. Destinos externos explícitos y nuevos: no se
sobrescriben generaciones. Importación fija una vez los bytes completos acotados,
limita 65 nombres únicos y 128 MiB, rechaza rutas/enlaces/cifrado/compresión,
sincroniza cada miembro y cierra el manifiesto al final. Verifica después todos
los hashes y el sello de generación. Fallar limpia sólo sus archivos nuevos.
Una descarga local y reimportación no demuestra montaje autenticado, validez
física de campo, convergencia S2 no trivial, admisión del host o despliegue.
