# Supplied ERT and first-arrival profile workflow

This implements the approved M07/M09 other-data path without changing the
accepted provider-specific numerical engines, original studies or field rights.
An explicit local original and bounded JSON metadata enter a portable pipeline;
no URL is fetched, file uploaded, scientific fallback selected or raw published.

## Closed input and physics

`geophysics.supplied-profile/v1` has exactly schema, method, source, frame and
weights. Method is `ert.topographic-profile/v1` or
`traveltime.first-arrival-profile/v1`. Source has source_id, kind
(`user_upload`, `field`, `synthetic_control`), citation, rights, sha256 and bytes.
Rights has exactly holder, processing_allowed=true and redistribution_allowed
boolean. Those are explicit declarations, not proof of third-party permission.
Frame has horizontal_reference, vertical_datum, coordinate_unit=m,
vertical_positive=up and profile_axes=distance,elevation. Strings are nonempty
bounded256 UTF-8 characters; exact booleans/integers, no unknown/duplicate keys,
nonfinite JSON or subclass hooks. No automatic CRS/foot/time conversion.

Weights explicitly select the existing `provider-example-conditional/v1` policy:
ERT sigma_R=max(0.03 abs(R),0.001 Ohm); traveltime
sigma_t=max(0.03 t,0.0001 s). They are assumed, not measured errors or calibrated
uncertainty. Measured covariance is not silently replaced by this policy.
Only the declared supported `.ohm` Wenner-profile or `.sgt` source/pick grammar
is admitted. Existing strict parsers retain geometry/count/order/duplicate and
unit/sign failures. This is not support for every acquisition format.

Bind the exact original through bounded8MiB hash/count and no-link regular-file
checks before parsing. Metadata64KiB, result32MiB. Retain file identity and
rehash after calculation; a changed original prevents completed publication.
Trusted local directories are a precondition, not hostile same-user isolation.
Call the actual existing topography-aware ERT or Dijkstra tomography engine
and both unchanged train/held-out challenges, plus its physical oracles and
sensitivity runs. Fixed numerical settings are explicit output configuration,
not user callbacks or Python import paths. Predictive failures remain failures.

## Portable result and exclusive publication

Output `geophysics.supplied-profile-result/v1` contains method, admitted metadata,
original hash/bytes, original geometry/row identities, actual engine report,
code hashes, numerical settings and scope plus content SHA256. Synthetic truth
is not inferred from source kind; truth stays unavailable. A source_id in an
engine's legacy teaching template is replaced only with the admitted input
identity, never used as a claim that supplied bytes are the provider object.
Provider-link-only/raw-publication labels do not grant rights to a user original;
the supplied rights declaration and private-local scope govern this result.
ERT residuals explicitly retain prediction-minus-observation convention from
the frozen engine; the presentation must not label them observed-minus-predicted.

One explicit new output directory gets exclusive result.json and manifest.json;
no raw copy by default. Each file is fsynced; the final manifest binds result
bytes/SHA and method/source/config identities. A failed/racing write is retained,
never overwritten or removed. Re-import rechecks bounded members/content hash,
metadata, source and result identities. Exact numerical replay additionally
requires the external original matching its hash. An exported array is not an
independent physical oracle by itself.

The path-invoked CLI takes explicit input, metadata and output paths. Python
packages/engines remain in repository-local ignored environments. It reports
fixed safe status and result digest, not private filesystem paths or raw values.
Any rejected/nonconverged/unverified scientific run returns a nonzero exit while
retaining its diagnostic artifact; QC-only must not be called inverse success.

## Validation and boundaries

Tests precede implementation: duplicate/unknown metadata; false processing
permission; units/sign/weight mistakes; original hash/byte/type/link/size drift;
counts/geometry/duplicates; real homogeneous physical oracles; supplied actual
field-file execution without source relabelling; exclusive export/re-import and
tamper; failed numerical verdict retention. Independent full provider tests and
fresh-process repeatability keep their original thresholds. Actual commands,
runtime and source hashes are measured, not inherited from older receipts.

This local extension does not register a VPS worker, provide hard resource
preemption, change shared styles or accept all M07/M09 field geology. Actual
method-specific host resource admission and browser views are separate required
integration work. No SMTP, project backup or second deployment is introduced.
