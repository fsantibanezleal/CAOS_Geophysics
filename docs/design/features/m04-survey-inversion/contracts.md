# Closed survey, fitting and artifact contracts

This proposal defines one complete bounded protocol, not permissive defaults.
A supplied null is legal only where expressly listed. Omitted/extra keys, duck
types, coerced strings, NaN/Infinity and negative zero in geometry are rejected.
All counts/ranges precede array allocation, copy, finite scan or engine import.
This means numerical working arrays, not the bounded raw UTF8 input buffer.
The reader indexes value-array byte spans after the bounded lexical pass and
decodes only source/physical/geometry/prior/policy metadata for planning. It
does NOT json-decode the complete observation/noise lists before the geometry
seal. After sealing, separate fitting/scoring/evaluation readers materialize
only their authorized rows/components. No whole-survey object is handed to fit.

## Transport and primitive types

Public input is UTF8 JSON, at most 8388608 bytes including whitespace; reject BOM,
invalid UTF8, duplicate keys, depth>12, tokens>500000, number lexemes>64 bytes,
strings>2048 decoded UTF8 bytes and total strings>262144 bytes. A bounded stdlib
lexer counts and validates the complete document before json decoding.
Every structural punctuation, string (including each object key), number and
true/false/null literal is one token; whitespace is not a token. Depth counts
the simultaneously open arrays/objects, root depth1. Check decoded string byte
lengths as well as lexical bytes so escapes cannot bypass caps. Reject
numeric overflow/underflow-to-zero, nonfinite binary64 and non-integral integer
fields. Bounds do not rely on a user-declared content length. No external refs.

ID = ASCII [A-Za-z0-9_.-], 1..96 chars; Hash = lowercase 64-hex SHA256.
Text = UTF8 1..2048 bytes, no NUL/control except LF; nullable Text expressly
allows JSON null. Real = finite binary64 converted once from a JSON decimal
number, not bool; Int = exact JSON integral token, not bool, int64-representable.
Enums are exact case-sensitive strings. Native entry rejects object subclasses,
array-like protocols, nonnative dtype, memmap, object dtype and arrays with hooks.

F64(shape), I64(shape), Bool(shape) use closed descriptor keys
{dtype,shape,data,sha256}: dtype is respectively float64, int64 or bool;
shape is a list of Int dimensions of the exact stated count, positive for
requests. Only explicitly empty result index/history arrays allow a zero
dimension; they still have a real empty-payload hash, not a null placeholder.
data is a flat original-order list of exactly product(shape) primitives;
sha256 hashes little-endian C-order bytes after the declared conversion.
Bool bytes are 0/1; float negative zero is preserved except geometry rejects it.
Int/bool descriptors are never converted to float. Native snapshots have
explicit native dtype, own storage and write protection, not durable immutability.
Hashing metadata uses sorted-key compact UTF8 JSON, no ASCII escaping,
allow_nan=false; numeric scalars are the converted native values.

## Root document

Exactly 12 keys:

| Key | Type and exact rule |
| --- | --- |
| schema | enum magnetic-survey-inversion-1 |
| source | Source below |
| frame | Frame below |
| inducing_field | Field below |
| acquisition | Acquisition below |
| processing | Processing below |
| geometry | Geometry below |
| observations | Observation below |
| noise | Noise below |
| prior | Prior below |
| policy | Policy below |
| intent | enum local_calibrate, local_evaluate, replay_only |

replay_only requires a validated bundle, not this modelling document; passing
this root with replay_only rejects with wrong_endpoint. Evaluation uses an
existing frozen candidate/model generation, never a second tuning request.

Source exactly {id,kind,original_sha256,original_bytes,provider_url,rights,scope,
citation}: id ID; kind field or authored_synthetic; original_sha256 Hash;
original_bytes Int 1..2^63-1 (metadata, not allocation authorization);
provider_url nullable Text (http/https citation only, never fetched);
rights enum private_user_supplied, provider_link_only, redistribution_permitted,
unresolved; scope complete_acquisition or declared_subset; citation Text.
Private user-supplied bytes permit only that owner's local/owned processing,
not redistribution; unresolved permits inventory but no modelling. Provider
link-only does not authorize raw mirroring. scope never changes via a row mask.
No field truth member is permitted.

Frame exactly {axes,coordinate_unit,vertical_positive,crs,vertical_datum,origin,
transform_sha256}: axes exact ENU; coordinate_unit m; vertical_positive up;
crs Text explicitly identifying the projected/local ENU construction;
vertical_datum Text; origin F64(3); transform_sha256 Hash. Origin is descriptive
coordinate lineage, not an extra translation applied by the solver. P04 receivers
and mesh origin already use that same resolved frame. Geographic degrees,
mixed datums and undeclared transforms reject; no CRS conversion in this tool.

Field exactly {kind,F_nT,I_deg,D_deg,reference_epoch,provenance,source_sha256,
spatial_policy}: kind uniform_inducing_field; F_nT Real [1,1e6];
I_deg Real [-90,90], D_deg Real [-180,180); reference_epoch Text (not inferred
from row times); provenance Text; source_sha256 Hash; spatial_policy
explicit_uniform_approximation. This is a declared approximation, not an IGRF
evaluation/verified field. Per-row varying fields, inferred IGRF heights/epochs
and unknown field references reject modelling, not silently average.

Acquisition exactly {row_ids,group_ids,timestamp_policy,timestamps,geometry_basis}:
row_ids list[ID] N unique in original order; group_ids list[ID] N (flight/line/
station-group identity explicit, no signal-based regrouping); timestamp_policy
enum recorded_utc or unavailable_declared; timestamps list of N ISO8601 UTC
strings ending Z for recorded_utc, otherwise null; geometry_basis Text.
Recorded UTC syntax is YYYY-MM-DDTHH:mm:ss[.fraction]Z, valid Gregorian date,
hour0..23, minute/second0..59, optional fraction1..6 digits. No offsets or leap
second coercion; unsupported leap-second originals remain inventory-only.
No timestamp synthesis, epoch reevaluation or source license inference.

Processing exactly {nodes,final_node,quantity,background_relation,eligibility}:
nodes list 1..64 Node, unique IDs; final_node ID; quantity enum secondary_enu_nT,
linear_tmi_nT, exact_total_anomaly_nT; background_relation enum
secondary_field_declared, projection_of_secondary_declared,
total_norm_minus_declared_uniform_F; eligibility explicit_induced_assumption.
The relation must match quantity in the same order.
Node exactly {id,parents,operation,input_sha256,output_sha256,parameters_sha256,
parameters,citation}: id ID; parents list[ID] 0..8; operation enum original,
declared_external_correction, frame_conversion, background_subtraction,
linear_projection, total_norm_difference, m03_processed_eligible;
three hashes Hash; citation Text. Exactly one original root with no parents,
all others>=1 parents, parents earlier in list, all nodes ancestors of final_node.
No unknown or disconnected node. parameters is the exact tagged union below;
parameters_sha256 hashes its canonical UTF8 bytes. Upstream records are also
preserved in the original source/bundle; a hash alone is not a correction recipe.
For original, input_sha256 equals source.original_sha256. For a single parent,
input_sha256 equals that parent's output_sha256; for multiple parents it equals
SHA256 of their output hashes joined by LF in the declared parents order, no
trailing LF. Final output_sha256 equals observations.values_sha256. These bind
identities; they do not prove a conversion was physically correct. Upstream
verification checks the actual bytes/recipes, not hash presence alone.

| operation | Exact parameters keys and types |
| --- | --- |
| original | {kind: identity}; no correction inferred from this declaration |
| frame_conversion | {kind: external_frame_conversion, from_frame: Frame, to_frame: Frame, transform_sha256: Hash} |
| background_subtraction | {kind: subtract_uniform_F, field: Field}; subtract only the named F from upstream measured total intensity |
| linear_projection | {kind: projection_of_secondary, field: Field, component_order: [E,N,U]} |
| total_norm_difference | {kind: norm_total_minus_F, field: Field}; distinct from secondary amplitude or linear projection |
| declared_external_correction | {kind: external_preprocessed, record_sha256: Hash, bundle_sha256: Hash}; exact upstream recipe required |
| m03_processed_eligible | {kind: m03_approved_output, bundle_sha256: Hash, descriptor_sha256: Hash, quantity: quantity enum above, approved_epoch: Text}; exact registered M03 output required |

All kind/component strings are literal enums, not arbitrary text. No nested
extras, nulls or defaults. from/to frames and fields use the complete tables in
this document. An external_preprocessed or m03_approved_output reference must
resolve through the existing approved provenance validator; an unregistered
epoch cannot be made eligible by a client string. These are consumption seams,
not implementations of M03 corrections or arbitrary external code execution.
Before modelling, resolve and verify these upstream parameter bytes/typed DAG
through existing provenance infrastructure; failure is unresolved_lineage.
No correction is re-executed here. Rereferencing must cite old/new field and
typed source operations in upstream M03, not an arbitrary new scalar label.
RTP, secondary amplitude, RGB/potential grids and equivalent-source coefficients
are ineligible quantities.

Geometry exactly {receivers_m,usable,qc_reason,mesh,partition}:
receivers_m F64(N,3), finite original coordinates; usable Bool(N);
qc_reason list N enum accepted, missing_physical_metadata, invalid_measurement,
provider_qc_excluded, geometry_ineligible. usable true iff reason accepted.
Unknown coordinates must reject geometry planning until resolved; no invented
zero coordinates. Inventory-only import may retain original unparsed metadata
outside this modelling protocol.
Mesh exactly {origin_m,widths_x_m,widths_y_m,widths_z_m,active}:
origin_m F64(3); widths each F64(nx/ny/nz), each axis 1..64, width [.001,1e5],
axis span<=1e5, full cells<=4096; active Bool(nx*ny*nz), active 1..2048.
Mesh/receiver coordinates and edges within +/-1e7 m; x-fast Fortran cell index
i+nx*(j+ny*k), active columns increasing full-cell index. P04 representability,
closed full-volume receiver exclusion and local geometry tolerances apply.
All usable receivers must be exterior; unusable interior rows retain inventory
and are never passed to a kernel.
Partition exactly {name,block_width_m,buffer_m,seed}:
name magnetic-geometry-seal-1; block_width_m F64(2), both strictly positive
<=1e5; buffer_m Real [0,1e5]; seed Int exactly 104729.
Membership rules/count minima are in algorithms. Values cannot relax them.

Observation exactly {quantity,unit,values,values_sha256}:
quantity exactly processing.quantity; unit nT; values F64(N,C), C=3 for
secondary_enu_nT with fixed component order E,N,U, otherwise C=1.
Every row remains present even if excluded. values_sha256 equals descriptor hash.
For scalar observations no implicit subtract-F or linearization of measured
total intensity. Absolute total intensity and instrument-frame vectors must be
converted in verified upstream provenance, never here.

Noise exactly {kind,unit,values,basis,citation,cross_partition_dependence}:
kind diagonal_sd or full_covariance; unit nT or nT^2 respectively;
values F64(N,C) for SD, or F64(D,D) for covariance, D=N*C;
basis enum measured_gaussian, propagated_gaussian, explicit_conditional_gaussian;
citation Text; cross_partition_dependence declared_absent or possible_not_removed.
All SD strictly>0. Full covariance D<=512, symmetric bitwise values with
maximum symmetry error=0, SPD Cholesky, condition<=1e8.
No symmetrization, nugget, estimated noise floor or row subtraction.
Unusable/partition rows are selected by component-flat index row*C+component,
and each subset gets its principal covariance. Correlation across partitions
is not removed by a spatial buffer or principal extraction.

Prior exactly {lower_si,upper_si,start_si,reference_si,chi_scale_si,lengths_m,
reference_in_smooth,spatial_weights,basis}:
four F64(A) arrays, lower>=0, upper<=.1, lower<upper, start/reference within
closed bounds; chi_scale_si Real exactly .01; lengths_m F64(3) positive<=1e5;
reference_in_smooth true only; spatial_weights none only; basis Text.
No truth-derived reference, ad-hoc default start, forced nonzero start, depth
weighting or susceptibility prior imported from gravity units.

Policy exactly {name,betas,penalties,optimizer_binding,resource_profile}:
name magnetic-nested-l2-irls-1; betas list 8 Reals exactly
[.0001,.001,.01,.1,1.,10.,100.,1000.]; penalties exact list [l2,sparse_smallness];
optimizer_binding exactly {accepted_source,accepted_export,epoch}:
accepted_source nullable Hash, accepted_export nullable Text, epoch nullable Text.
All null while unbound; any inverse execution requires all nonnull verified
against the separately accepted binding, not merely user strings.
resource_profile local_bounded or online_proposed.
No optional beta cooling, randomized search, automatic field/mesh correction,
different sparse norms or learned hyperparameters.

## Preflight and canonical seal

N 1..2048, A 1..2048, full cells<=4096, all descriptors combined<=96 MiB,
scalar elements<=500000 (in addition to lexer token cap), metadata<=256 KiB.
D=N*C; allocate no covariance for diagonal noise. Require
3*N*A<=12582912 and conservative bytes

B=8*(18*D*A+6*D*D+8*A*A+64*(D+A)+8*full_cells) <=805306368.

This is deliberately conservative algebra, not a claim of measured memory.
Full-covariance count bound is additional; linear algebra workspace or vendor
peak above the measured budget still fails. checked integer arithmetic before
multiplication/allocation. The online sub-profile in design is separately
required; selecting it never opens online authority.

Geometry seal hash covers source ID/scope, frame, acquisition IDs/groups,
complete geometry/QC, mesh and partition only. It excludes ALL signal-dependent
hashes, including source.original_sha256 and processing.output_sha256, not just
array values. Configuration hash separately covers this geometry seal, field,
prior and policy. Source-record hash covers complete Source, Acquisition and
Processing declarations/recipes. Observation and uncertainty hashes separately
freeze the actual likelihood; none of these hashes seeds a scientific choice.
No field truth hash allowed. Geometry membership can therefore be computed
before observations/uncertainties are loaded, without a value-hash dependency.
The scorer/evaluator binds all five hashes. Re-import does not regenerate a seal from
rounded view coordinates.

## Result and failure descriptors

Result exactly {schema,status,identity,inventory,partition,candidates,selected,
model,prediction,metrics,history,diagnostics,claims}.
schema magnetic-survey-result-1; status enum complete, failed, ineligible;
identity exactly {seal_sha256,configuration_sha256,source_record_sha256,
observations_sha256,noise_sha256,engine_epoch,optimizer_source}:
first five Hash, engine_epoch Text, optimizer_source
nullable Hash only when not executed.
inventory exactly {row_ids,group_ids,usable,qc_reason,receivers_m}: same full
original-order types as request, never shortened.
partition exactly {unit_ids,outer_rows,development_rows,folds,sha256}:
unit_ids list[ID or null] N; outer/development I64 vectors increasing original indices;
folds list exactly 3 {fit_rows,validation_rows,buffered_rows}, I64 vectors;
sha256 Hash. buffered_rows may be I64(0); fit/validation/outer/development
vectors must meet the positive minima. unit_ids is null for each unusable
original row, otherwise ID; those rows have no invented unit membership.
Empty failed-plan partitions use null for entire partition only,
not empty arrays that pretend success. Each usable row belongs outer/development;
per-fold buffered rows remain inventoried, not a fourth hidden source subset.

Candidate exactly {id,beta,penalty,folds,status,score}:
id ID, beta Real frozen value, penalty l2 or sparse_smallness;
folds list exactly 3 FoldMetric, status complete/failed, score nullable Real.
FoldMetric exactly {fold,status,reason,n_rows,n_components,phi_d,rms_nT,
normalized_rms,kkt_inf,model_sha256}: fold Int 0..2; status converged/failed;
reason nullable Text (null only converged); counts nonnegative Int;
numeric metrics nullable Real (all null on failure); model_sha256 nullable Hash.
There are exactly 16 candidates in frozen beta-major, l2-before-sparse order.
A failed candidate has null score, never infinity or a partial-average score.
selected nullable ID: only complete candidates; failures/ineligible null.
model nullable {chi_si,active_indices,mesh_sha256,sha256}: F64(A), I64(A),
two Hash, same physical ordering.
prediction nullable {quantity,components,rows,values_nT,residual_nT}:
quantity enum as request; components list [E,N,U] or [scalar];
rows I64 of ALL usable original indices increasing; values/residual F64(M,C).
Excluded rows have no invented prediction, explicitly absent via rows mapping.
Residual = observed minus predicted, never the optimizer sign.

Metrics nullable exactly {development,outer,l2_baseline,sparse_comparison}:
first two Metric {n_rows,n_components,phi_d,rms_nT,normalized_rms};
counts positive Int, metrics nonnegative finite Real, no field model error.
l2_baseline and sparse_comparison nullable ID, not a fabricated alternate volume.
History list 0..4096 records exactly {candidate,fold,phase,outer_iteration,
inner_iteration,beta,epsilon_q,phi_d,phi_regularizer,objective,kkt_inf,
model_sha256,status}: candidate ID; fold Int -1..2 (-1 final refit); phase l2,
irls_surrogate or irls_fixed; counters nonnegative Int; beta/epsilon_q Real
(epsilon_q=0 for l2 only); objective terms finite Real nonnegative; kkt_inf
finite>=0; model hash Hash; status iterating/converged/failed. Exhausted history
fails, not silent truncation.

Diagnostics exactly {reason,resolution_kind,resolution_arrays,resources}:
reason nullable Text; resolution_kind none or local_fixed_objective;
resolution_arrays null iff resolution_kind=none, otherwise exactly
{free_indices,selected_indices,diagonal,point_spread,matrix,singular_values}:
free_indices nullable I64(F), increasing original active-column indices,
null only F=0; selected_indices I64(K), the unique evenly spaced indices from
algorithms, K=min(A,8); diagonal nullable F64(A), matrix nullable F64(A,A),
singular_values nullable F64(F), all three available only A<=64 (singular values
null also F=0); point_spread F64(A,K), dimensionless local resolution, zero
rows for bound-locked variables. All-bound F=0 gives zero point_spread and
zero matrix/diagonal when available, not a fictitious inverse. Singular values
are of stacked [W*J_q_free; sqrt(beta)*R_free]. No posterior terminology.
resources nullable {wall_s,cpu_s,peak_rss_bytes,peak_private_bytes,scratch_bytes}:
times nonnegative Real, byte counts nonnegative Int, no absent measurement=0.
claims exactly {full_method_accepted,field_source_verified,geology_truth_known,
online_admitted}: four bools, unconditionally false for this result protocol.
Future accepted claims require a versioned contract amendment and independent
acceptance references, not an omitted default or user-controlled boolean.
Synthetic truth is stored in a separately labelled evaluator
control, not in the modelling request/result or a field volume.

Failure envelope still carries identity+inventory when validated, null selection/
model/prediction/metrics and a typed reason. If parsing fails before identity,
separate closed error {schema,code,path,message}: schema magnetic-input-error-1,
code enum bytes,tokens,depth,encoding,duplicate_key,type,count,enum,hash,endpoint,
physical_metadata,lineage,geometry,partition,uncertainty,resource,dependency,
numerical,convergence,durability; path Text, message Text. No result-success
envelope for invalid input.

## Durable local bundle and hosted seam

One generation: manifest.json plus bounded uncompressed .npy numeric arrays
without object dtype/pickle, total<=128 MiB; manifest<=1 MiB,<=64 members.
Each manifest member exactly {name,dtype,shape,unit,bytes,sha256}:
name ID+".npy" with no separators or '..', dtype one of float64/int64/bool,
shape list1..3 Int, unit nT/nT^2/SI/m/1/index/bool, bytes exact header+payload
file count, hash exact stored bytes. Manifest contains the closed Result and
the typed request metadata, original-byte reference/hash, component ordering,
source rights/scope, parameter/DAG references and array member descriptors;
arrays are member references, never duplicate embedded buffers.
Manifest exactly {schema,result,request_metadata,original,members,generation_sha256}:
schema magnetic-survey-bundle-1; result is the Result above;
request_metadata is the full closed request above; all F64/I64/Bool arrays in
these two documents are replaced by exact {member: ID+'.npy'} references.
Result history is losslessly encoded as {codec,index,numeric,model_hash_words},
codec magnetic-history-table-1. For H=0..4096 records, index references I64(H,6)
columns candidate_index,fold,phase_index,outer_iteration,inner_iteration,
status_index; numeric references F64(H,6) columns beta,epsilon_q,phi_d,
phi_regularizer,objective,kkt_inf. Candidate indices use the fixed16-candidate
order; phase/status indices use their enum orders in this contract.
model_hash_words references I64(H,4): each SHA256 is decoded to32 bytes then
each consecutive8 bytes interpreted signed little-endian int64. Reversal
recovers the exact original lowercase hex hash, no truncation. This history
codec is the ONLY additional manifest-level array transformation; it is not
an alternative runtime history or an omitted inner-iteration trace.
All referenced members must exist exactly once, no unused members; dtype/shape/
unit checks are derived from their original typed positions, not client choice.
original exactly {sha256,bytes,scope,rights,included}: Hash,positive Int,
source scope/rights enums and literal false. Raw is retained separately by its
owner, never silently mirrored or copied into this bounded result bundle.
members list1..64 of the member table. generation_sha256 hashes canonical
manifest UTF8 excluding this field, binding member hashes and complete metadata.
External paths/URLs, archives/symlinks, pickle and oversized NPY headers reject.
Read each header with cap65536 bytes before allocation; enforce member bytes,
shape product, dtype, hashes and original ordering.

Local writer creates a fresh sibling generation, flushes/closes files, verifies
a readback and uses same-volume atomic pointer replacement. Never overwrite
original or prior successful generation. Unsupported filesystem fsync/directory
semantics remain explicit durability limitations, not invented Windows proof.
Crash, disk-full and interruption tests must prove old generation/recoverable
new data and no successful partial pointer. Hosted persistence/ownership belongs
existing product infrastructure and requires its own gates. Off-host backups,
restore and provider SMTP are not owner-tested-stage prerequisites under current
product SDD section8; retain their historical failed receipts unchanged.

## Geometry-only foundation closure

Before optimizer binding, parse_request(bytes) returns a private bounded handle.
Its metadata() returns a fresh stdlib document with observation/noise data omitted
but their closed dtype/shape/hash retained. The original raw bytes and deferred
token spans remain private. All number types/counts/hashes, including likelihood
tokens, are validated by streaming without a likelihood list or numerical array.
plan_geometry(handle) receives metadata only; it cannot access likelihood values.
It returns a fresh closed magnetic-geometry-plan-1 document with exact keys
{schema,identity,inventory,partition,final_refit_rows,eligibility,preflight,claims}.
Identity has exactly the five Hash keys seal_sha256,configuration_sha256,
source_record_sha256,observations_sha256,noise_sha256. Inventory and partition use
the Result tables above. final_refit_rows is I64 of increasing original indices.
eligibility exactly {local_processing,redistribution,lineage_verified,reasons}:
three bools and list of literal reasons rights_unresolved,raw_mirror_forbidden,
unresolved_lineage,optimizer_unbound,likelihood_not_validated,online_not_admitted.
Original identity lineage is declared, not verified field correction. Non-original
operations remain unresolved_lineage until the upstream validator is actually
bound; no parameter-hash-only acceptance. Likelihood SPD/SD scientific validation
and optimizer execution are not foundation claims. preflight exactly
{rows,components,active_cells,full_cells,descriptor_bytes,scalar_elements,
conservative_bytes}: nonnegative Int counts. claims are the four false Result
booleans. This plan is never a magnetic-survey-result-1 or an inverse success.

Foundation export is a separate closed magnetic-geometry-export-1 JSON with keys
{schema,request_sha256,request_bytes,request,plan,generation_sha256}: Hash,
positive Int, full closed original request, exact geometry plan, Hash respectively.
The request is embedded as its original UTF8 string, bounded by the 8MiB transport
cap, preserving exact lexical bytes; no provider original is embedded. Export is
private-owner local only (no publication API), capped at 16MiB. The generation
hash covers canonical export excluding itself. Import validates the complete
request anew and recomputes the full plan and all hashes before returning it.
Writer uses exclusive creation of a caller-explicit new local file, flush/fsync,
readback verification, never overwrites a prior export; partial failure unlinks
only the newly created file. A foundation export proves neither the future NPY
result bundle nor crash-recovery/host durability. No external path is accepted
inside this document. No solver, likelihood load or claim upgrade on reimport.
The ordinary module's local command is exactly magnetic_survey.py validate
--request PATH --export NEW_FILE (both mandatory). Unknown commands/flags reject.
Exit0 means complete geometry validation/export only,2 invalid input/partition,
5 file/durability failure. It reads at most8MiB request bytes and never the
provider original, so source.original_sha256 remains unverified raw provenance.
It never advertises calibrate/evaluate. Those full tools remain R-414 scope.

API adapter uses existing owner-scoped source/job IDs, not client-supplied owner.
Submit a hash-bound config plus source ID; return existing queued/running/
succeeded/failed/cancelled state with this method result reference. Until actual
optimizer+native/profile+ownership acceptance, return ineligible with local
recipe. No invented endpoint path or auth protocol replaces MAIN's existing ABI.

## Internal physical operator and actual-displacement certificate

These are trusted in-process scientific functions, not new upload/HTTP endpoints
or callbacks accepted from users. They implement the already defined equations;
they do not supply an accepted nonlinear optimizer or completed fit by themselves.
data-pipeline/magnetic_inverse.py build_operator(raw,rows,deadline=...) parses
the same bounded original bytes and seals metadata before engine import. rows
is an exact built-in tuple of1..2048 strictly increasing original usable row
indices (exact int, no bool); geometry-only prediction may include outer
coordinates but never reads their observations. deadline is an explicit finite
native monotonic float. Unresolved rights or non-original unresolved lineage
rejects. No field/original-source verification claim follows from this kernel.

MagneticQuantity is the internal native-kernel composition: actual Gchi
F64(3N,A), B0 F64(3), direction F64(3), F native float[1,1e6], quantity one
of the three declared quantities. Metadata/counts precede scans/copies;
N<=2048,A<=2048,3N*A<=12582912. Store rounded A_b=.01*Gchi once, including
its exact payload hash, not separate unrounded scale multiplication. Native
q F64(A) must be finite and in[0,10]. Returned evaluate(q) has exactly
{prediction_nT,jacobian_nT_per_q,secondary_enu_nT,total_norm_nT}; shapes are
(N,C),(N*C,A),(N,3),(N,) respectively, owned C-order write-protected arrays.
Native point norms use isolated Decimal80/from_float on retained B0 and native
b, full delta0 rational numerator and positive denominator, not the old P04
expression. The analytic Jacobian uses the actual total-vector direction;
all inverse T/F>1e-8 guards apply without fallback. Hash-bound operand snapshots
are owned/write-protected, not tamperproof process memory.

data-pipeline/magnetic_inverse_precision.py MagneticCertificate owns that
operator's fixed native operands and explicit observed F64(N,C), noise exactly
{kind,values} (diagonal_sd/F64(N,C) or full_covariance/F64(D,D)), reference_q,
lower_q,upper_q F64(A), beta positive native float and a tuple of0..7 fixed
regularization terms. Each term is exact{alpha,weights,derivative}: alpha
nonnegative native float, weights positive F64(K), derivative canonical float64
CSR(K,A),K<=2A,nnz<=8A with native int32 indices/indptr, no duplicates or
foreign hooks. These are actual vendor component W diagonals, derivative
coefficients and multipliers, not a pre-rounded normal matrix or copied solver.
Skip alpha0 terms without changing them. All metadata and a conservative live
interval-vector/copy byte bound must pass<=805306368 before snapshots; domain,
CSR/order/finite, SD positivity and SPD checks follow. Full covariance D<=512,
exact symmetric positive-definite C, condition2<=1e8, no jitter; factor this
already principal C and bind the actual retained binary64 Cholesky L. Whiten
by native/interval triangular solves, never a constructed inverse.

certify(q,qt,native_gradient,native_phi,native_phi_trial,iteration,trial,deadline)
uses the actual projected chord, not an unprojected search vector. Exact native
F64(A) models/gradient, finite native phi floats, iteration int0..199,trial
int0..19, explicit finite monotonic deadline. Its exact14 return keys are
iteration,trial,native_phi_current,native_phi_trial,displacement_inf_q,
precision_digits,slope_interval,delta_interval,armijo_margin_interval,
arithmetic_domain,slope_domain,decision,cause,passes. Domain is
fixed_native_operand_magnetic_norm for exact magnitude or
fixed_native_operand_quadratic for the two linear lanes; slope domain is
recorded_native_gradient. This DIFFERENT norm domain cannot be submitted to a
quadratic-only M02 validator or relabelled accepted nonlinear execution.
precision_digits nullable34/50/80;passes exact int0..3. Intervals nullable exact
tuple(str,str) of finite ordered Decimal endpoints, each<=192chars, exponent
range[-9999,9999]. unavailable metadata is None, never fictitious zero.
decision enum certified_accept,certified_reject,unresolved,not_run; cause enum
armijo,non_descent,zero_displacement,precision_limit,range_unsupported,wall_cap,
native_failure. Accept ONLY certified negative slope upper and strict negative
Armijo-margin upper for actual real native-operand objective difference minus
the exact retained binary64 coefficient1e-4 times slope. Reject certified
non-descent lower>=0 or margin lower>0. Exhaust all three precisions with a
straddling interval ->unresolved/precision_limit. Expired/unsupported/incomplete
arithmetic ->not_run with all partial intervals/precision cleared and passes0.
Bounds, nonfinite native values and zero chords never create acceptance.
