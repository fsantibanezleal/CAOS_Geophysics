# M03 streamed acquisition and global-result contract

Revision1. This is a distinct offline contract, not an increase to the ordinary
magnetic-lines/1, magnetic-request/1, magnetic-result/1 or local320 limits.
Read [operator choice](full-survey-operator-proposal.md),
[algorithm and capacity](full-survey-algorithms.md) and
[verification requirements](full-survey-validation.md). All tables are closed:
every named key is required, including nulls; missing, extra and duplicate keys
fail. No general dictionaries, expression, callback, URL fetch or archive loader
is accepted. Source rights and field eligibility are independent of structure.

## Primitive rules and byte domains

ID, Hash, Text, UTC, F64, Pos, Nonneg, Permission and Bool retain the exact
primitive grammar in [ordinary contracts](contracts.md). Int remains a native
JSON integer, not bool or float. Float64 may originate from finite native JSON
int/float only, with explicit conversion; overflow, underflow to zero from a
nonzero measurement, nonfinite, string coercion and unrepresentable coordinate
differences refuse. Original int-versus-float JSON bytes are retained; replay
does not claim a normalized object was the original. Negative zero changes only
in explicitly canonical derived identities, never original byte hashes.

JSON documents are UTF-8, depth<=16, nodes<=200000, key<=128bytes,
text<=8192bytes, numeric token<=128bytes. Scan duplicate keys and depth before
materialization; bounded reads use remaining allowance+1 and count actual read
bytes, not just stat. Metadata+request originals together<=4194304bytes;
each<=2097152. Every manifest page<=4194304bytes and<=2048entries, each
manifest root<=2097152bytes. No unbounded root containing millions of row IDs.

The original CSV is the exact ordinary14-column header, optional recorded BOM,
strict UTF-8, no quoted multiline fields, no alternate header/delimiter. Every
physical record<=4096bytes including delimiter/newline; numeric token<=128,
IDs<=64ASCII bytes, ordinal native decimal integer0..2^63-1. Blank magnetic,
height, time, sigma and heading fields are missing, never observed zero.
Geometry-only pass reads/hashes original bytes and validates nonmeasurement
tokens; measurement tokens remain opaque until the committed geometry seal.
It does not assert finite measurement eligibility before the second pass.

Bounded external arrays and dictionaries are generated derivatives in a fresh
owned directory. They are never trusted merely because the caller supplied
their hashes. Their original inputs and all chunk bytes must independently
verify before numerics/replay. Symlinks, reparse points, hardlink substitutions,
absolute paths, traversal, nested paths from requests, case-insensitive name
collisions and any undeclared file refuse. No pickle, object dtype, np.load,
compressed input, whole-file CSV read or executable deserialization.

## Exact streamed input objects

| Object | Complete keys and types |
| --- | --- |
| SurveyInput | schema:"magnetic-line-survey-input/1"; dataset_id:ID; revision:ID; source_kind:Enum(field_acquisition,original_synthetic_acquisition,provider_grid,provider_image); original:SurveyOriginal; rights:Rights; quantity:Quantity; coordinates:Coordinates; acquisition:SurveyAcquisition; channel_state:List(SurveyState,0,64); reference:Nullable(SurveyReference); uncertainty:Nullable(Uncertainty); subset:Nullable(SurveySubset); authored_control:Nullable(AuthoredControl); arrays:List(ArrayRef,1,128); auxiliaries:List(SurveyAux,0,16). |
| SurveyOriginal | csv_sha256:Hash; csv_bytes:Int(1,4294967296); source_url:Nullable(Text); provider_identifier:Nullable(Text); retrieval_utc:Nullable(UTC). Actual streamed CSV must match bytes/hash. |
| SurveyAcquisition | line_dictionary:TableRef; sensor_dictionary:TableRef; timestamp_basis:Enum(UTC,absent,unknown); declared_precision_s:Nullable(Pos); max_segment_gap_m:Pos; max_time_gap_s:Nullable(Pos); height_consistency_tolerance_m:Nullable(Nonneg). Dictionary row schemas are unchanged LineDefinition/SensorDefinition; exact coverage, unique sorted IDs, line-kind equality. |
| SurveySubset | parent_raw_sha256:Hash; parent_row_count:Int(1,8000000); selected_ids:ArrayRef; reason:Text; selection_policy_sha256:Hash; coverage_limitations:Text. Selected source-order IDs match every input row; subset never becomes full-provider label. |
| ArrayRef | array_id:ID; role:ArrayRole; shape:List(Int(0,16000000),1,2); dtype:DType; unit:Unit; chunk_rows:Int(1,4096); manifest:FileIdentity; ordered_ids_sha256:Hash; mask_array_id:Nullable(ID). Flattened counts are profile-bounded. Zero length only for explicitly empty calibration/anchor/exclusion arrays. |
| TableRef | table_id:ID; row_schema:TableSchema; rows:Int(1,8000000); manifest:FileIdentity. Closed row key sets below or ordinary referenced table; per-schema limits are mandatory. |
| FileIdentity | name:ID; bytes:Int(1,4194304); sha256:Hash. Name is a role-generated basename, never a user path. |
| ArrayManifest | schema:"magnetic-line-array-manifest/1"; array_id:ID; shape:List(Int(0,16000000),1,2); dtype:DType; unit:Unit; pages:List(PageIdentity,0,512); content_sha256:Hash. content is concatenated source-order chunk bytes. Only zero-length arrays have zero pages and SHA256 of empty bytes. |
| TableManifest | schema:"magnetic-line-table-manifest/1"; table_id:ID; row_schema:TableSchema; rows:Int(1,8000000); pages:List(PageIdentity,1,512); content_sha256:Hash. content hashes length-prefixed canonical ordered row objects. |
| PageIdentity | sequence:Int(0,511); first_row:Int(0,15999999); rows:Int(1,16000000); file:FileIdentity. Sequences contiguous, no overlap/gaps; pages cover exact array/table rows. |
| ManifestPage | schema:"magnetic-line-manifest-page/1"; owner_id:ID; sequence:Int(0,511); entries:List(ChunkIdentity,1,2048). |
| ChunkIdentity | sequence:Int(0,32767); first_row:Int(0,15999999); rows:Int(1,4096); bytes:Int(1,8388608); sha256:Hash; name:ID. No gaps/overlap/duplicate chunks; actual bytes=rows*row-width for binary arrays. Table chunk bytes are independently bounded canonical JSON lines, not binary object pointers. |

Chunk basenames are exactly `array-ID-00000000.bin` or
`table-ID-00000000.jsonl`; IDs are producer-selected collision-free ASCII IDs.
Array/table identifiers additionally have length<=32, preserving the64-byte
generated-basename bound. Page/root names similarly
`array-ID-page-000000.json`/`array-ID.json` and table
equivalents. The typed identifier is verified against the generated filename;
changing name/role/shape without byte changes is still a custody error.
All numeric binary payloads are little-endian C-order, without headers.
DType=Enum(float64,uint8,uint32,uint64,int64,ascii64,ascii30). Unit=Enum(m,nT,nT^2,
nT*m,nT^-2,1_per_m,s,degree,decimal_year,dimensionless,identity,UTC,
cycles_per_m,rad_per_m). String cells are ASCII padded with NUL only after the
end; interior NUL, nonzero padding and length truncation refuse. No NUL enters
decoded IDs/text. Byteorder/dtype/units cannot be inferred from filenames.

ArrayRole=Enum(row_id,line_index,sensor_index,ordinal,utc,easting,northing,
upward,terrain_upward,clearance,magnetic,uncertainty,heading,missing_mask,
qc_mask,partition_index,source_position,source_block_member,source_scale,
coefficient,predicted,residual,reference_east,reference_north,reference_up,
reference_F,reference_date,navigation,base,crossover,offset,grid_coordinate,
grid_value,grid_mask,spectrum_axis,spectrum_power,microlevel_removed,
microlevel_retained). Role-specific type/shape/unit checks are mandatory:
row_id ascii64[N]/identity; UTC ascii30[N]/UTC; line_index uint32[N], sensor
uint8[N], ordinal uint64[N]; eight coordinate/heading/value/sigma scalar
columns float64[N] in their original m/degree/nT units; masks uint32[N].
Missing bits0..8 mean UTC/upward/terrain/clearance/magnetic/sigma/heading/
reference/date; unused bits zero. Masked float cells store +0 solely as a
binary placeholder; decoded/public value is null and no computation may use
that placeholder. QC reason bits follow the ordinary Mask enumeration order,
not the missing bits. Diagnostic duplicate-location flag alone does not exclude.
Source positions float64[M,3]/m, scales float64[M]/1_per_m and coefficients
float64[M]/nT*m. Partition and source membership indexes uint64/identity
refer to original row positions, never renumbered selected rows.
All physical scalar output roles retain float64 with their explicit unit;
reference dates use decimal_year; spectrum power uses nT^2. An ArrayRef's
shape has the original N for row-indexed roles, auxiliary length for auxiliary
roles, M for source roles or the exact declared grid shape for grid roles.
Source membership is uint64[N,2] (original row, source index); signed block
indices belong to the geometry table, not a silently unsigned encoding.
Navigation xyz is float64[N_aux,3]/m, base float64[N_aux]/nT; separate UTC
and line-index roles are mandatory. Structured crossover/offset records use
TableRef instead of binary ArrayRole(crossover,offset), which are reserved and
refused in revision1. Source-free grid coordinates are float64[P,3]/m,
grid values float64[ny,nx]/nT and masks uint32[ny,nx]; FFT axes/power have exact Q
dimensions and explicit cycles_per_m or rad_per_m/nT^2 units.

SurveyState has exactly ordinary StateRecord keys; its parameters are the
SurveyOperationParameters union, or null only in the original unknown branches.
SurveyOperationRequest has exactly operation, input_channel_sha256, parameters.
Names/sign/units/dependencies and main_field XOR rereference remain unchanged.
The extended union changes NavigationSeries, BaseSeries, Reference,
IndependentOffsets and calibration_row_ids into explicitly typed array/table
references; all other coefficients/policy literals remain ordinary types,
except microlevel spectrum_policy is the explicit SurveySpectrum extension.
Complete parameter keys are ordinary LagParameters, DiurnalParameters,
HeadingParameters, MainFieldParameters, RereferenceParameters,
LevelingParameters and MicrolevelParameters, with typed substitutions
navigation=SurveyNavigation, base=SurveyBase, calibration=SurveyCalibration,
evaluated_reference/old_reference/new_reference=SurveyReference,
heldout_calibration=Nullable(SurveyOffsets), spectrum_policy=SurveySpectrum.
No other field is added, omitted or renamed.

| Object | Complete keys and cross-object requirements |
| --- | --- |
| SurveyAux | aux_id:ID; kind:Enum(navigation,base,calibration,independent_offsets,reference); identity:AuxIdentity; payload:SurveyAuxPayload. Payload is closed tagged union below; no unreviewed adapter. |
| SurveyNavigation | schema:"magnetic-line-navigation-stream/1"; identity:AuxIdentity; clock:Clock; coordinates:Coordinates; row_ids:ArrayRef; utc:ArrayRef; line_index:ArrayRef; xyz:ArrayRef. Length2..16000000, xyz[N,3]/m; strict UTC per line; original navigation IDs distinct namespace. |
| SurveyBase | schema:"magnetic-line-base-stream/1"; identity:AuxIdentity; clock:Clock; station_id:ID; quantity:"scalar_total_intensity"; unit:"nT"; utc:ArrayRef; intensity:ArrayRef. Length2..16000000, strict UTC, float64/nT, no missing endpoint averaging. |
| SurveyCalibration | identity:AuxIdentity; partition:"independent_calibration"; calibration_row_ids:ArrayRef; coefficient_receipt_sha256:Hash. Row IDs do not intersect validation/outer; identity branch rules unchanged. |
| SurveyOffsets | calibration:SurveyCalibration; values:TableRef; reference_gauge_id:ID. Closed OffsetValue rows1..65536, row_schema=offset_value, sorted unique line IDs. |
| SurveyReference | kind:Enum(igrf_evaluated,authored_constant); model_generation:Text; coefficients_sha256:Nullable(Hash); evaluator:Evaluator; epoch:SurveyEpoch; coordinates_sha256:Hash; input_height_definition:Text; input_height_unit:Enum(m,km); datum_transform_evidence_sha256:Nullable(Hash); original_basis:Enum(NED,ENU); output_basis:"ENU"; vector_east_nT:ArrayRef; vector_north_nT:ArrayRef; vector_up_nT:ArrayRef; scalar_F_nT:ArrayRef; direction_tolerance_deg:Pos; receipt_sha256:Hash. Exact N corrected rows, original ID order, same admitted datum; F>0. |
| SurveyEpoch | date_mode:Enum(survey_reference,row_utc); date_decimal_year:Nullable(F64); row_date_decimal_year:Nullable(ArrayRef); survey_epoch_evidence_sha256:Nullable(Hash); row_utc_sha256:Nullable(Hash). Original mutually exclusive branches and Gregorian rules unchanged. |

SurveyAuxPayload is SurveyNavigation, SurveyBase, SurveyCalibration,
SurveyOffsets or SurveyReference selected by kind. Navigation/base/calibration
identity must equal the containing Aux identity; no aliases with different
rights or source status. An old/new Reference is a SurveyReference value in
MainField/Rereference parameters, not an arbitrary external receipt dereference.
IGRF remains closed without independently reviewed evaluator/datum/actual
evaluated-array custody. F matching a user hash is not an IGRF evaluation.

## Exact request and geometry seal

| Object | Complete keys and bounds |
| --- | --- |
| SurveyRequest | schema:"magnetic-line-survey-request/1"; dataset_version_sha256:Hash; channel_sha256:Hash; sensor_id:ID; operations:List(SurveyOperationRequest,0,6); geometry_policy:GeometryPolicy; grid:SurveyGrid; equivalent_sources:SurveySources; split:SurveySplit; spectrum:Nullable(SurveySpectrum); export_policy:ExportPolicy; profile:"m03-offline-stream/1"; solver:SolverPolicy. |
| SurveySources | source_geometry:SurveySourceGeometry; depth_candidates_m:List(Pos,2,2); damping_candidates:List(Pos,4,4); damping_unit:Enum(dimensionless,nT^-2); weights_policy:WeightPolicy; weight_multiplier:1; dtype:"float64"; parallel:false; fit_intercept:false; column_scaling:"unweighted_population_std_no_mean"; candidate_order:"depth_then_damping_ascending"; tie_break:"larger_damping_then_depth". Ordinary numeric depth/damping ranges unchanged. |
| SurveySourceGeometry | version:"half_open_training_blocks_stream/1"; origin_e_m:F64; origin_n_m:F64; block_e_m:Pos; block_n_m:Pos; representative:"unweighted_xy_mean_fsum_sorted_row_ids"; edge_policy:"floor_half_open_positive_side"; vertical_policy:"minimum_training_upward_minus_depth"; max_sources:Int(1,65536). Blocks1..10000m, no coarsening to satisfy cap. |
| SurveySplit | version:"full_lines_buffered_ties_stream/1"; outer_line_ids:ArrayRef; heldout_blocks:TableRef; buffer_m:Nonneg; anchor_line_ids:Nullable(ArrayRef); inner_folds:List(SurveyFold,3,3); geometry_manifest_sha256:Hash; sealed_values_sha256:Hash; tuning_candidate_order:"depth_then_damping_ascending"; maximum_outer_evaluations:1; minimum_supported_fraction:Pos. ID refs ascii64, blocks exact SpatialBlock rows; buffer>=support radius, fraction<=1. |
| SurveyFold | fold_id:ID; validation_line_ids:ArrayRef; validation_blocks:TableRef. Distinct complete-line groups, no outer/anchor overlap, every nonanchor training flight validates once. |
| SurveyGrid | origin_e_m:F64; origin_n_m:F64; spacing_e_m:Pos; spacing_n_m:Pos; nx:Int(2,1048576); ny:Int(2,1048576); plane_upward_m:F64; datum:Text; support_radius_m:Pos; continuation_delta_m:Nullable(Pos); boundary_policy:SurveyBoundary. Total exported plane cells<=1048576, not per-plane. |
| SurveyBoundary | mode:Enum(periodic,zero_pad,reflect_pad); pad_e_cells:Int(0,1048576); pad_n_cells:Int(0,1048576); detrend:Enum(none,remove_mean); taper:Enum(none,hann); crop:"original_extent". Axis pad<=2*original, total internal FFT<=4194304. |
| SurveySpectrum | rectangle:SurveyRectangle; window:Enum(rectangular,hann); mean_policy:"subtract_arithmetic_mean"; normalization:"full_two_sided_bin_power"; axis_unit:Enum(cycles_per_m,rad_per_m); direction_sectors:List(DirectionSector,0,16). Fully supported geometry-sealed rectangle only. |
| SurveyRectangle | e_start:Int(0,1048575); n_start:Int(0,1048575); nx:Int(2,1048576); ny:Int(2,1048576). In grid, total cells<=1048576. |
| SolverPolicy | schema:"m03-lsmr-policy/1"; atol:0.000000000001; btol:0.000000000001; conlim:100000000; maxiter:2000; stationarity_relative:0.000000001; chunk_rows:4096; chunk_sources:128; threads:1; initial_guess:"zero"; damping_map:"sqrt_lambda"; stop_policy:"code_and_independent_gradient". Exact literals, no supplied looser tolerances. |
| GeometrySeal | schema:"magnetic-line-survey-geometry/1"; original:SurveyOriginal; coordinates_sha256:Hash; acquisition_sha256:Hash; request_geometry_sha256:Hash; rows:Int(1,8000000); lines:Int(1,65536); sensors:Int(1,4); segments:Int(0,7999999); crossover_candidates:Int(0,8000000); source_counts:List(Int(1,65536),4,4); arrays:List(ArrayRef,1,128); dictionaries:List(TableRef,1,16); capacity:CapacityRecord; value_access:"not_opened". Source counts final/A/B/C; geometry ID excludes magnetic/sigma bytes but binds raw source identity and all geometry/config. |

TableSchema=Enum(line_definition,sensor_definition,aux_identity,operation_state,
offset_value,spatial_block,crossover_geometry,crossover_value,source_block,
candidate_fit,line_evaluation,level_component,sector_power). LineDefinition/SensorDefinition/
AuxIdentity/SurveyState/OffsetValue/SpatialBlock have their exact named keys.
Line/offset/block/component/evaluation dictionaries<=65536rows; sensors<=4,
aux<=16, states<=64, candidate_fit<=24, sectors<=16; crossings<=8000000.
source_block rows<=8000000. SourceBlock rows
exact row_index:Int(0,7999999), block_e:Int(-2147483648,2147483647),
block_n:Int(-2147483648,2147483647), source_index:Int(0,65535).
CrossoverGeometry rows exact crossover_id:ID, flight_segment_id:ID,
tie_segment_id:ID, a:Nullable(F64), b:Nullable(F64), easting_m:Nullable(F64),
northing_m:Nullable(F64), height_difference_m:Nullable(F64),
time_separation_s:Nullable(Nonneg), disposition:Enum(admitted,rejected),
reasons:List(CrossoverReason,0,16), shared_endpoint_group_id:Nullable(ID),
constraint_representative:Nullable(ID), tolerance:IntersectionTolerance.
CrossoverValue adds flight_minus_tie_nT:Nullable(F64),
difference_variance_nT2:Nullable(Nonneg); rejected records retain null values.
LevelComponent has exactly component_id:ID, line_ids:ArrayRef,
gauge_line_id:ID, rank:Int(0,65536), singular_values:Nullable(ArrayRef),
condition:Nullable(Pos), absolute_datum:false, rank_method:
"incidence_connected_component", rank_receipt_sha256:Hash. The connected
incidence rank is independently proven from graph/gauge; no fabricated full
dense singular spectrum. A requested singular diagnostic exceeding resources
refuses, not an arbitrary replacement of null by1. Leveling result points at
component/offset tables and before/after residual arrays via its manifest.
No schema field is guessed from context. The parser must implement this union.

Seal is generated before fit/candidate value access. Navigation supplied as a
lag correction changes geometry BEFORE seal; its independent clock/custody is
required. Calibration fitted from values never changes sealed geometry. Empty
fold crossover calibration still refuses, without gauge/label patch. Complete
segmentation/split/gap/support/index arrays are covered by the seal. No outer
value access for source/scales/tie/candidate/resource selection. The original
S1 and opened100/50m seals/thresholds are not reused as new untouched tests.

## Streamed result, export and safe errors

SurveyResult exact keys: schema="magnetic-line-survey-result/1", run_id:ID,
lane:Enum(local_synthetic,local_user,field_provider_product), input:InputReceipt,
request:FileIdentity, environment:Environment, geometry:GeometrySeal,
inventory:InventoryReceipt, channels:List(ChannelReceipt,1,8),
crossovers:Nullable(TableRef), leveling:Nullable(SurveyLevelingReceipt),
partitions:PartitionReceipt, fit:FitReceipt, grid:List(SurveyGridReceipt,1,3),
spectrum:Nullable(SurveySpectrumReceipt), evaluation:EvaluationReceipt, rights:Rights,
artifacts:List(SurveyMember,0,192), verdict:SurveyVerdict. No online-owned lane.

InputReceipt exact keys: dataset_sha256:Hash, original:SurveyOriginal,
metadata:FileIdentity, arrays:List(ArrayRef,1,128), auxiliary_identities:
List(AuxIdentity,0,16). InventoryReceipt: original_rows:Int(1,8000000),
retained:Int(0,8000000), invalid:Int(0,8000000), excluded:Int(0,8000000),
disposition:ArrayRef, reasons:ArrayRef, flags:ArrayRef. Counts are disjoint/
exhaustive, reason bits may overlap. ChannelReceipt: channel_id:ID, kind:
Enum(scalar_total_intensity,scalar_total_field_anomaly), role:Enum(original,
derived,diagnostic_removed,diagnostic_retained), data:ArrayRef, state:
List(SurveyState,0,64), parent_sha256:Nullable(Hash),
reference_receipt_sha256:Nullable(Hash).

SurveyLevelingReceipt exact keys: offsets:TableRef, components:TableRef,
before_residuals:ArrayRef, after_residuals:ArrayRef,
uncalibrated_line_ids:ArrayRef, scope:"training_only",
gauge_policy:"lexicographic_first_tie_per_component". offset_value/
level_component tags required; residuals correspond to admitted representative
crossings, nT units. Empty uncalibrated IDs use an explicit empty array.
SurveyGridReceipt: grid_id:ID, config:SurveyGrid,
quantity:"scalar_total_field_anomaly", easting_axis:ArrayRef,
northing_axis:ArrayRef, values:ArrayRef, support_mask:ArrayRef,
role:Enum(fitted_plane,continued_plane,microlevel_diagnostic). Axes float64/m,
values float64[ny,nx]/nT, mask uint32[ny,nx]; role/height not inferred from
position. All grids together obey total-cell limit.
SurveySpectrumReceipt: config:SurveySpectrum, power:ArrayRef,
east_axis:ArrayRef, north_axis:ArrayRef, window_mean_square:Pos,
mean_removed_nT:F64, parseval_sum_nT2:Nonneg, sectors:Nullable(TableRef),
microlevel:Nullable(SurveyMicrolevelReceipt). SectorPower rows exact
sector_id:ID, bin_count:Int(0,4194304), power_nT2:Nonneg.
SurveyMicrolevelReceipt: parameters:SurveyMicrolevelParameters,
transfer:ArrayRef, removed:ArrayRef, retained:ArrayRef,
removed_power_nT2:Nonneg, retained_power_nT2:Nonneg,
clipped_removed:Nullable(ArrayRef), geological_preservation_claim:false.
SurveyMicrolevelParameters has ordinary MicrolevelParameters keys with
spectrum_policy=SurveySpectrum; promotion remains diagnostic_only.

PartitionReceipt exact keys: seal_sha256:Hash, final_training:ArrayRef,
outer_validation:ArrayRef, exclusions:ArrayRef, inner:List(FoldReceipt,3,3),
evaluation_count:Int(0,1). FoldReceipt: fold_id:ID, training:ArrayRef,
validation:ArrayRef, exclusions:ArrayRef, source_members:ArrayRef.
FitReceipt: solver:SolverPolicy, candidates:TableRef, selected_depth_m:Pos,
selected_damping:Pos, sources:ArrayRef, column_scales:ArrayRef,
coefficients:ArrayRef, solve:SolverReceipt, fit_count:Int(1,26).
TableRef adds candidate_fit with exact CandidateFit rows: fold_id:ID,
depth_m:Pos, damping:Pos, solve:SolverReceipt, scored:Int(0,8000000),
excluded:Int(0,8000000), rmse_nT:Nullable(Nonneg), verdict:SurveyVerdict.

SolverReceipt exact keys: istop:Int(0,7), iterations:Int(0,2000),
normr_estimate:Nonneg, normar_estimate:Nonneg, norma_estimate:Nonneg,
conda_estimate:Nonneg, normx_estimate:Nonneg, data_term:Nonneg,
regularization_term:Nonneg, objective:Nonneg,
objective_unit:Enum(nT^2,dimensionless), stationarity_inf:Nonneg,
stationarity_relative:Nonneg, gradient_denominator:Nonneg,
coefficient_error_bound_nT:Nonneg, operator_forward_calls:Int(0,10000),
operator_adjoint_calls:Int(0,10000), timing:TimingRecord,
verdict:Enum(pass,nonconverged,resource_refused,cancelled).
TimingRecord: cpu_s:Nonneg, wall_s:Nonneg, peak_rss_bytes:Int(0,9223372036854775807),
peak_committed_bytes:Int(0,9223372036854775807), scratch_bytes:Int(0,9223372036854775807),
stop_cpu_s:Nullable(Nonneg), stop_wall_s:Nullable(Nonneg).
Resource estimates and actual terminal counters are not interchangeable.
Counter ranges preserve an actual over-limit measurement; profile limits are
separate acceptance checks, not serialization ranges that erase the failure.

EvaluationReceipt exact keys: observed:ArrayRef, predicted:ArrayRef,
residual:ArrayRef, scored:Int(0,8000000), excluded:Int(0,8000000),
coverage:Nonneg, signal_rms_nT:Nullable(Nonneg), rmse_nT:Nullable(Nonneg),
per_line:TableRef, comparison:Nullable(ComparisonReceipt), verdict:SurveyVerdict.
per_line tag line_evaluation adds exact rows line_id:ID, scored:Int(0,8000000),
excluded:Int(0,8000000), rmse_nT:Nullable(Nonneg), signal_rms_nT:
Nullable(Nonneg). ComparisonReceipt: provider_identity:AuxIdentity,
quantity:Quantity, coordinates:Coordinates, values:ArrayRef,
residual:ArrayRef, rmse_nT:Nullable(Nonneg), verdict:SurveyVerdict.
Same channel/datum/height is mandatory; disagreement is not field truth.

SurveyVerdict exact keys: overall:Enum(pass,fail,unresolved,ineligible,
nonconverged,cancelled,resource_refused), gates:List(SurveyGate,1,64),
numerical_success:Bool, reasons:List(Text,0,64). SurveyGate: gate_id:ID,
verdict:Enum(pass,fail,unresolved,ineligible,nonconverged,cancelled,
resource_refused), evidence_sha256:Nullable(Hash), reason:Nullable(Text).
Unique gate IDs; overall pass requires all applicable gates pass, while method/
field/admission gates remain separately unresolved. A structural-only result
cannot set numerical_success=true.

SurveyMember exact keys: role:ID, name:ID, bytes:Int(0,34359738368),
sha256:Nullable(Hash), permission:Permission, disposition:Enum(included,
denied,unresolved), reason:Text. Included requires actual nonnull hash and
fsynced bytes. Denied retains no bytes/hash, and exports no data-bearing root,
ID list, derived mask or figure that violates its permission. Public derivative
permission does not imply raw or location publication. Replay without required
permitted originals is unresolved; no silent private-to-public reconstruction.

CapacityRecord exact keys: profile:"m03-offline-stream/1", rows:Int(1,8000000),
sources:Int(1,65536), auxiliary_rows:Int(0,16000000),
crossover_candidates:Int(0,8000000), exported_cells:Int(0,1048576),
fft_cells:Int(0,4194304), raw_bytes:Int(1,4294967296),
auxiliary_bytes:Int(0,4294967296), fit_buffer_bytes:Int(0,4294967296),
geometry_buffer_bytes:Int(0,4294967296), transform_buffer_bytes:
Int(0,4294967296), scratch_bound_bytes:Int(0,34359738368),
kernel_pair_bound:Int(0,1000000000000000),
resource_state:Enum(unmeasured,measured_pass,refused).

AttemptResult is a closed union: successful SurveyResult or Error. Error exact
keys: schema="magnetic-line-survey-error/1", code:Enum(invalid_contract,
custody_mismatch,metadata_ineligible,unsupported_operation,nonconverged,
cancelled,resource_refused,io_failed), stage:Enum(ingest,seal,correction,
crossover,fit,predict,transform,evaluate,export,replay), field:Nullable(ID),
message:Text, partial_manifest_sha256:Nullable(Hash). Messages are fixed
code/stage strings; no arbitrary native exceptions, traceback, path, raw value
or authenticated-origin claim. Durable partial evidence never becomes success.
Fresh output directory only, staged members hash/fsync before final manifest;
interrupted/cancelled attempts remain independently identified and non-success.

No file receipt, structural pass, convergence or preview grants online
admission or full M03 acceptance. Source metadata/datum/error/reference,
predictive thresholds, provider bytes/comparator and actual useful whole-run
resource measurements remain separately required.
