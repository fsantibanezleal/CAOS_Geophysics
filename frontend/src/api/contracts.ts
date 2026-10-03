/** Wire-contract mirror of the approved product SDD. The released data/v2 format is separate. */
export type Sha256 = string;
export type RightsDecision = "mirror" | "provider-link-only" | "derivative-only" | "forbidden";
export type Modality = "gravity" | "magnetics" | "mt" | "ert" | "waveform" | "traveltime" | "seismic";
export type JobState = "queued" | "running" | "succeeded" | "failed" | "cancelled" | "nonconverged" | "ineligible";
export type ExecutionLane = "online-cpu" | "client-live" | "offline-local" | "replay";

export interface SourceRecord {
  schema_version: "geophysics.source-record-view/v1";
  source_id: string;
  version: number;
  provider: string;
  location: { kind: "upload"; filename: string };
  doi: string | null;
  citation: string | null;
  retrieved_at: string;
  rights_statement: string;
  rights_decision: RightsDecision;
  private_storage_permission: "attested" | null;
  declared_format: string;
  expected_bytes: number | null;
  sha256: Sha256;
  attribution: string;
}

export interface RawAsset {
  schema_version: "geophysics.raw-asset-view/v1";
  asset_id: string;
  owner_id: string;
  project_id: string;
  source_id: string;
  source: SourceRecord;
  original_filename: string;
  mime_type: string;
  detected_format: string;
  byte_count: number;
  sha256: Sha256;
  physical_metadata: RawPhysicalMetadata;
  created_at: string;
  receipt: string;
  download_url: string;
  /** This checks only the upload envelope, not scientific dataset QC. */
  validation_status: "raw_metadata_checked";
}

export interface RawPhysicalMetadata {
  coordinate_reference: "epsg" | "local";
  epsg: number | null;
  local_crs: string | null;
  axis_order: "xy" | "yx" | "lon_lat" | "lat_lon";
  horizontal_datum: string;
  vertical_datum: string;
  vertical_positive: "up" | "down";
  horizontal_unit: "m" | "km" | "degree";
  vertical_unit: "m" | "ft";
  measurement_unit: string;
  epoch_utc: string;
  component_frame: string;
  geometry: Record<string, unknown>;
}

export interface AxisDimension {
  name: string;
  size: number;
  unit: string;
  direction: "increasing" | "decreasing";
}

export interface EvidenceArray {
  axis_order: string[];
  shape: number[];
  values: number[];
  unit: string;
}

export type CoordinateReference =
  | { kind: "epsg"; epsg: number; horizontal_datum: string; vertical_datum: string; vertical_positive: "up" | "down"; axis_order: string[] }
  | { kind: "local"; name: string; horizontal_datum: string; vertical_datum: string; vertical_positive: "up" | "down"; axis_order: string[] };

export interface ObservationDataset {
  dataset_id: string;
  version: number;
  modality: Modality;
  dimensions: AxisDimension[];
  axis_order: string[];
  coordinates: CoordinateReference;
  physical_units: Record<string, string>;
  geometry: { kind: string; component_orientation: string; coordinates: Record<string, EvidenceArray> };
  observed: EvidenceArray;
  mask: { included: boolean[]; missing_reasons: Record<string, string> };
  uncertainty: { kind: string; unit: string; values: EvidenceArray | null; covariance: EvidenceArray | null };
  correction_history: Array<{ name: string; parameters: Record<string, string | number>; reversible: boolean }>;
  parser: { name: string; version: string };
  parent_raw_hashes: Sha256[];
  qc_verdict: "passed" | "failed" | "unresolved" | "ineligible";
}

export interface ProcessingRun {
  run_id: string;
  input_dataset_versions: Array<{ dataset_id: string; version: number }>;
  transform_dag: Array<{ id: string; operation: string; input_ids: string[]; parameters: Record<string, string | number> }>;
  code_digest: Sha256;
  environment_digest: Sha256;
  output_dataset_versions: Array<{ dataset_id: string; version: number }>;
  /** Immutable output mask/uncertainty references; arrays live in the versioned datasets. */
  output_evidence: Array<{ dataset_id: string; version: number; mask_sha256: Sha256; uncertainty_sha256: Sha256 }>;
  warnings: string[];
  measured: { wall_seconds: number; peak_rss_bytes: number; scratch_bytes: number };
  content_hashes: Record<string, Sha256>;
}

export interface SolverJob {
  job_id: string;
  attempt: number;
  owner_id: string;
  project_id: string;
  dataset_id: string;
  dataset_version: number;
  method_id: string;
  method_version: string;
  execution_lane: ExecutionLane;
  survey_geometry_id: string;
  mesh: Record<string, string | number>;
  model_parameterization: string;
  starting_model_id: string;
  reference_model_id: string | null;
  physical_bounds: { lower: number; upper: number; unit: string };
  data_weights_id: string;
  regularizer: string;
  beta: number;
  seed: number;
  preflight: { estimated_wall_seconds: number; estimated_peak_rss_bytes: number; estimated_scratch_bytes: number };
  admission: { verdict: "admitted" | "rejected"; reason: string | null };
  state: JobState;
  progress: number;
  worker_id: string | null;
  timestamps: { created_at: string; started_at: string | null; ended_at: string | null };
  measured: { wall_seconds: number | null; peak_rss_bytes: number | null; scratch_bytes: number | null };
  error: { code: string; message: string } | null;
}

export interface ResultArtifact {
  schema_version: string;
  result_id: string;
  job_id: string;
  input_dataset_id: string;
  input_hashes: Sha256[];
  engine: { id: string; version: string; digest: Sha256 };
  data_origin: "synthetic" | "field";
  axes: AxisDimension[];
  observed: EvidenceArray;
  predicted: EvidenceArray;
  signed_residual: EvidenceArray;
  residual_convention: "observed-minus-predicted";
  normalized_residual: EvidenceArray;
  model: EvidenceArray;
  truth: EvidenceArray | null;
  objective: Record<string, number>;
  stopping_reason: string;
  sensitivity: EvidenceArray | null;
  coverage: EvidenceArray | null;
  unavailable_reason: string | null;
  uncertainty_definition: string;
  held_out_partition: string;
  figure_arrays: Record<string, EvidenceArray>;
  provenance: { nodes: string[]; edges: Array<{ from: string; to: string }> };
  rights_decision: RightsDecision;
  licence: string;
  file_hashes: Record<string, Sha256>;
  interpretation_hypotheses: string[];
}

function fail(path: string, detail: string): never {
  throw new Error(`${path}: ${detail}`);
}

function object(value: unknown, path: string): Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) fail(path, "expected object");
  return value as Record<string, unknown>;
}

function nonempty(value: unknown, path: string): string {
  if (typeof value !== "string" || !value.trim()) fail(path, "missing text");
  return value;
}

function timestamp(value: unknown, path: string): string {
  const text = nonempty(value, path);
  if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(text) || Number.isNaN(Date.parse(text)))
    fail(path, "expected timestamp with timezone");
  return text;
}

function finite(value: unknown, path: string): number {
  if (typeof value !== "number" || !Number.isFinite(value)) fail(path, "expected finite number");
  return value;
}

function nonnegative(value: unknown, path: string): number {
  const number = finite(value, path);
  if (number < 0) fail(path, "must be nonnegative");
  return number;
}

function integer(value: unknown, path: string, minimum = 0): number {
  const number = finite(value, path);
  if (!Number.isInteger(number) || number < minimum) fail(path, `expected integer >= ${minimum}`);
  return number;
}

function sha(value: unknown, path: string): Sha256 {
  if (typeof value !== "string" || !/^[a-f0-9]{64}$/i.test(value)) fail(path, "invalid SHA-256");
  return value;
}

function choice<T extends string>(value: unknown, choices: readonly T[], path: string): T {
  if (!choices.includes(value as T)) fail(path, `expected ${choices.join("/")}`);
  return value as T;
}

function array(value: unknown, path: string): unknown[] {
  if (!Array.isArray(value)) fail(path, "expected array");
  return value;
}

function textArray(value: unknown, path: string): string[] {
  return array(value, path).map((item, index) => nonempty(item, `${path}[${index}]`));
}

function hashes(value: unknown, path: string): void {
  const map = object(value, path);
  if (!Object.keys(map).length) fail(path, "at least one file hash required");
  for (const [key, digest] of Object.entries(map)) sha(digest, `${path}.${key}`);
}

function exactKeys(value: Record<string, unknown>, expected: readonly string[], path: string): void {
  const extras = Object.keys(value).filter(key => !expected.includes(key));
  if (extras.length) fail(path, `unexpected field ${extras.join(", ")}`);
  for (const key of expected) if (!(key in value)) fail(`${path}.${key}`, "missing field");
}

export function rawPhysical(value: unknown): RawPhysicalMetadata {
  const physical = object(value, "raw_asset.physical_metadata");
  exactKeys(physical, ["coordinate_reference", "epsg", "local_crs", "axis_order", "horizontal_datum", "vertical_datum", "vertical_positive", "horizontal_unit", "vertical_unit", "measurement_unit", "epoch_utc", "component_frame", "geometry"], "raw_asset.physical_metadata");
  choice(physical.coordinate_reference, ["epsg", "local"] as const, "raw_asset.physical_metadata.coordinate_reference");
  if (physical.epsg !== null) integer(physical.epsg, "raw_asset.physical_metadata.epsg", 1000);
  if (physical.local_crs !== null) nonempty(physical.local_crs, "raw_asset.physical_metadata.local_crs");
  choice(physical.axis_order, ["xy", "yx", "lon_lat", "lat_lon"] as const, "raw_asset.physical_metadata.axis_order");
  nonempty(physical.horizontal_datum, "raw_asset.physical_metadata.horizontal_datum");
  nonempty(physical.vertical_datum, "raw_asset.physical_metadata.vertical_datum");
  choice(physical.vertical_positive, ["up", "down"] as const, "raw_asset.physical_metadata.vertical_positive");
  choice(physical.horizontal_unit, ["m", "km", "degree"] as const, "raw_asset.physical_metadata.horizontal_unit");
  choice(physical.vertical_unit, ["m", "ft"] as const, "raw_asset.physical_metadata.vertical_unit");
  nonempty(physical.measurement_unit, "raw_asset.physical_metadata.measurement_unit");
  timestamp(physical.epoch_utc, "raw_asset.physical_metadata.epoch_utc");
  nonempty(physical.component_frame, "raw_asset.physical_metadata.component_frame");
  const geometry = object(physical.geometry, "raw_asset.physical_metadata.geometry");
  if ("storage_key" in geometry) fail("raw_asset.physical_metadata.geometry", "unexpected private storage key");
  return value as RawPhysicalMetadata;
}

function scalarParameters(value: unknown, path: string): void {
  for (const [name, parameter] of Object.entries(object(value, path))) {
    if (typeof parameter === "string") nonempty(parameter, `${path}.${name}`);
    else finite(parameter, `${path}.${name}`);
  }
}

function dimensions(value: unknown, path: string): AxisDimension[] {
  const axes = array(value, path).map((raw, index) => {
    const axis = object(raw, `${path}[${index}]`);
    return {
      name: nonempty(axis.name, `${path}[${index}].name`),
      size: integer(axis.size, `${path}[${index}].size`, 1),
      unit: nonempty(axis.unit, `${path}[${index}].unit`),
      direction: choice(axis.direction, ["increasing", "decreasing"] as const, `${path}[${index}].direction`),
    };
  });
  if (!axes.length || new Set(axes.map(axis => axis.name)).size !== axes.length) fail(path, "missing or duplicate axis");
  return axes;
}

function evidenceArray(value: unknown, path: string, axes: AxisDimension[]): EvidenceArray {
  const record = object(value, path);
  const axisOrder = textArray(record.axis_order, `${path}.axis_order`);
  const shape = array(record.shape, `${path}.shape`).map((size, index) => integer(size, `${path}.shape[${index}]`, 1));
  const values = array(record.values, `${path}.values`).map((number, index) => finite(number, `${path}.values[${index}]`));
  const unit = nonempty(record.unit, `${path}.unit`);
  if (!axisOrder.length || axisOrder.length !== shape.length || new Set(axisOrder).size !== axisOrder.length)
    fail(path, "axis order and shape disagree");
  for (let index = 0; index < axisOrder.length; index++) {
    const axis = axes.find(candidate => candidate.name === axisOrder[index]);
    if (!axis || axis.size !== shape[index]) fail(path, `axis ${axisOrder[index]} has wrong or undeclared size`);
  }
  if (shape.reduce((product, size) => product * size, 1) !== values.length) fail(path, "array length does not match shape");
  return { axis_order: axisOrder, shape, values, unit };
}

function sameShape(left: EvidenceArray, right: EvidenceArray, path: string): void {
  if (left.axis_order.join("|") !== right.axis_order.join("|") || left.shape.join("|") !== right.shape.join("|"))
    fail(path, "array shape or orientation differs from observed");
}

export function parseSourceRecord(value: unknown): SourceRecord {
  const source = object(value, "source");
  exactKeys(source, ["schema_version", "source_id", "version", "provider", "location", "doi", "citation", "retrieved_at", "rights_statement", "rights_decision", "private_storage_permission", "declared_format", "expected_bytes", "sha256", "attribution"], "source");
  choice(source.schema_version, ["geophysics.source-record-view/v1"] as const, "source.schema_version");
  nonempty(source.source_id, "source.source_id");
  integer(source.version, "source.version", 1);
  nonempty(source.provider, "source.provider");
  const location = object(source.location, "source.location");
  exactKeys(location, ["kind", "filename"], "source.location");
  choice(location.kind, ["upload"] as const, "source.location.kind");
  nonempty(location.filename, "source.location.filename");
  if (source.doi !== null) nonempty(source.doi, "source.doi");
  if (source.citation !== null) nonempty(source.citation, "source.citation");
  timestamp(source.retrieved_at, "source.retrieved_at");
  nonempty(source.rights_statement, "source.rights_statement");
  choice(source.rights_decision, ["mirror", "provider-link-only", "derivative-only", "forbidden"] as const, "source.rights_decision");
  if (source.private_storage_permission !== null) choice(source.private_storage_permission, ["attested"] as const, "source.private_storage_permission");
  nonempty(source.declared_format, "source.declared_format");
  if (source.expected_bytes !== null) integer(source.expected_bytes, "source.expected_bytes", 0);
  sha(source.sha256, "source.sha256");
  nonempty(source.attribution, "source.attribution");
  return value as SourceRecord;
}

export function parseRawAsset(value: unknown): RawAsset {
  const asset = object(value, "raw_asset");
  exactKeys(asset, ["schema_version", "asset_id", "owner_id", "project_id", "source_id", "source", "original_filename", "mime_type", "detected_format", "byte_count", "sha256", "physical_metadata", "validation_status", "created_at", "receipt", "download_url"], "raw_asset");
  choice(asset.schema_version, ["geophysics.raw-asset-view/v1"] as const, "raw_asset.schema_version");
  for (const field of ["asset_id", "owner_id", "project_id", "source_id", "original_filename", "mime_type", "detected_format", "receipt", "download_url"])
    nonempty(asset[field], `raw_asset.${field}`);
  integer(asset.byte_count, "raw_asset.byte_count", 1);
  sha(asset.sha256, "raw_asset.sha256");
  const source = parseSourceRecord(asset.source);
  if (source.source_id !== asset.source_id || source.sha256 !== asset.sha256 || source.location.filename !== asset.original_filename || source.declared_format !== asset.detected_format)
    fail("raw_asset.source", "source identity or original metadata disagrees with asset");
  rawPhysical(asset.physical_metadata);
  timestamp(asset.created_at, "raw_asset.created_at");
  choice(asset.validation_status, ["raw_metadata_checked"] as const, "raw_asset.validation_status");
  const receipt = `/api/projects/${asset.project_id}/assets/${asset.asset_id}`;
  if (asset.receipt !== receipt || asset.download_url !== `${receipt}/download`)
    fail("raw_asset.download_url", "owner receipt path disagrees with asset identity");
  return value as RawAsset;
}

export function parseObservationDataset(value: unknown): ObservationDataset {
  const dataset = object(value, "dataset");
  nonempty(dataset.dataset_id, "dataset.dataset_id");
  integer(dataset.version, "dataset.version", 1);
  choice(dataset.modality, ["gravity", "magnetics", "mt", "ert", "waveform", "traveltime", "seismic"] as const, "dataset.modality");
  const axes = dimensions(dataset.dimensions, "dataset.dimensions");
  const order = textArray(dataset.axis_order, "dataset.axis_order");
  if (!order.length || new Set(order).size !== order.length || order.some(name => !axes.some(axis => axis.name === name)))
    fail("dataset.axis_order", "contains a missing or duplicate dimension");
  const coordinates = object(dataset.coordinates, "dataset.coordinates");
  const kind = choice(coordinates.kind, ["epsg", "local"] as const, "dataset.coordinates.kind");
  if (kind === "epsg") integer(coordinates.epsg, "dataset.coordinates.epsg", 1);
  else nonempty(coordinates.name, "dataset.coordinates.name");
  nonempty(coordinates.horizontal_datum, "dataset.coordinates.horizontal_datum");
  nonempty(coordinates.vertical_datum, "dataset.coordinates.vertical_datum");
  choice(coordinates.vertical_positive, ["up", "down"] as const, "dataset.coordinates.vertical_positive");
  const coordinateOrder = textArray(coordinates.axis_order, "dataset.coordinates.axis_order");
  if (!coordinateOrder.length || new Set(coordinateOrder).size !== coordinateOrder.length)
    fail("dataset.coordinates.axis_order", "coordinate axis order is missing or ambiguous");
  const units = object(dataset.physical_units, "dataset.physical_units");
  if (!Object.keys(units).length) fail("dataset.physical_units", "missing physical units");
  for (const [field, unit] of Object.entries(units)) nonempty(unit, `dataset.physical_units.${field}`);
  const geometry = object(dataset.geometry, "dataset.geometry");
  nonempty(geometry.kind, "dataset.geometry.kind");
  nonempty(geometry.component_orientation, "dataset.geometry.component_orientation");
  const geometryCoordinates = object(geometry.coordinates, "dataset.geometry.coordinates");
  if (!Object.keys(geometryCoordinates).length) fail("dataset.geometry.coordinates", "missing survey geometry");
  for (const [name, coordinate] of Object.entries(geometryCoordinates)) evidenceArray(coordinate, `dataset.geometry.coordinates.${name}`, axes);
  const observed = evidenceArray(dataset.observed, "dataset.observed", axes);
  if (observed.axis_order.join("|") !== order.join("|")) fail("dataset.observed", "orientation differs from dataset axis order");
  if (units.observed !== observed.unit) fail("dataset.physical_units.observed", "unit differs from observed array");
  const mask = object(dataset.mask, "dataset.mask");
  const included = array(mask.included, "dataset.mask.included");
  if (included.length !== observed.values.length || included.some(item => typeof item !== "boolean")) fail("dataset.mask.included", "mask must match observations");
  const reasons = object(mask.missing_reasons, "dataset.mask.missing_reasons");
  for (const [index, reason] of Object.entries(reasons)) {
    if (!/^\d+$/.test(index) || Number(index) >= included.length || included[Number(index)] !== false) fail("dataset.mask.missing_reasons", "reason index is not masked");
    nonempty(reason, `dataset.mask.missing_reasons.${index}`);
  }
  included.forEach((flag, index) => { if (!flag && !reasons[String(index)]) fail("dataset.mask.missing_reasons", `missing reason for ${index}`); });
  const uncertainty = object(dataset.uncertainty, "dataset.uncertainty");
  nonempty(uncertainty.kind, "dataset.uncertainty.kind");
  nonempty(uncertainty.unit, "dataset.uncertainty.unit");
  if (uncertainty.values === null && uncertainty.covariance === null) fail("dataset.uncertainty", "values or covariance required");
  if (uncertainty.values !== null) {
    const values = evidenceArray(uncertainty.values, "dataset.uncertainty.values", axes);
    sameShape(observed, values, "dataset.uncertainty.values");
    if (values.unit !== uncertainty.unit || values.unit !== observed.unit) fail("dataset.uncertainty.values", "uncertainty units differ from observations");
    if (values.values.some(value => value <= 0)) fail("dataset.uncertainty.values", "uncertainty must be positive");
  }
  if (uncertainty.covariance !== null) evidenceArray(uncertainty.covariance, "dataset.uncertainty.covariance", axes);
  array(dataset.correction_history, "dataset.correction_history").forEach((raw, index) => {
    const step = object(raw, `dataset.correction_history[${index}]`);
    nonempty(step.name, `dataset.correction_history[${index}].name`);
    scalarParameters(step.parameters, `dataset.correction_history[${index}].parameters`);
    if (typeof step.reversible !== "boolean") fail(`dataset.correction_history[${index}].reversible`, "expected boolean");
  });
  const parser = object(dataset.parser, "dataset.parser");
  nonempty(parser.name, "dataset.parser.name");
  nonempty(parser.version, "dataset.parser.version");
  if (!array(dataset.parent_raw_hashes, "dataset.parent_raw_hashes").length) fail("dataset.parent_raw_hashes", "missing raw lineage");
  array(dataset.parent_raw_hashes, "dataset.parent_raw_hashes").forEach((digest, index) => sha(digest, `dataset.parent_raw_hashes[${index}]`));
  choice(dataset.qc_verdict, ["passed", "failed", "unresolved", "ineligible"] as const, "dataset.qc_verdict");
  return value as ObservationDataset;
}

export function parseProcessingRun(value: unknown): ProcessingRun {
  const run = object(value, "processing_run");
  nonempty(run.run_id, "processing_run.run_id");
  const outputKeys = new Set<string>();
  for (const field of ["input_dataset_versions", "output_dataset_versions"]) {
    const versions = array(run[field], `processing_run.${field}`);
    if (!versions.length) fail(`processing_run.${field}`, "missing dataset version");
    versions.forEach((raw, index) => {
      const version = object(raw, `processing_run.${field}[${index}]`);
      nonempty(version.dataset_id, `processing_run.${field}[${index}].dataset_id`);
      integer(version.version, `processing_run.${field}[${index}].version`, 1);
      if (field === "output_dataset_versions") {
        const key = `${version.dataset_id}@${version.version}`;
        if (outputKeys.has(key)) fail(`processing_run.${field}`, "duplicate output dataset version");
        outputKeys.add(key);
      }
    });
  }
  const evidenceKeys = new Set<string>();
  array(run.output_evidence, "processing_run.output_evidence").forEach((raw, index) => {
    const evidence = object(raw, `processing_run.output_evidence[${index}]`);
    const id = nonempty(evidence.dataset_id, `processing_run.output_evidence[${index}].dataset_id`);
    const version = integer(evidence.version, `processing_run.output_evidence[${index}].version`, 1);
    const key = `${id}@${version}`;
    if (!outputKeys.has(key) || evidenceKeys.has(key)) fail("processing_run.output_evidence", "unmatched or duplicate output evidence");
    evidenceKeys.add(key);
    sha(evidence.mask_sha256, `processing_run.output_evidence[${index}].mask_sha256`);
    sha(evidence.uncertainty_sha256, `processing_run.output_evidence[${index}].uncertainty_sha256`);
  });
  if (evidenceKeys.size !== outputKeys.size) fail("processing_run.output_evidence", "missing mask or uncertainty provenance");
  const steps = array(run.transform_dag, "processing_run.transform_dag");
  if (!steps.length) fail("processing_run.transform_dag", "missing transform");
  const stepIds = steps.map((raw, index) => nonempty(object(raw, `processing_run.transform_dag[${index}]`).id, `processing_run.transform_dag[${index}].id`));
  if (new Set(stepIds).size !== stepIds.length) fail("processing_run.transform_dag", "duplicate transform ID");
  steps.forEach((raw, index) => {
    const step = object(raw, `processing_run.transform_dag[${index}]`);
    nonempty(step.operation, "transform.operation");
    const inputs = textArray(step.input_ids, "transform.input_ids");
    if (inputs.some(id => stepIds.indexOf(id) >= index)) fail("processing_run.transform_dag", "transform depends on itself or a later step");
    scalarParameters(step.parameters, "transform.parameters");
  });
  sha(run.code_digest, "processing_run.code_digest");
  sha(run.environment_digest, "processing_run.environment_digest");
  textArray(run.warnings, "processing_run.warnings");
  const measured = object(run.measured, "processing_run.measured");
  for (const field of ["wall_seconds", "peak_rss_bytes", "scratch_bytes"]) nonnegative(measured[field], `processing_run.measured.${field}`);
  hashes(run.content_hashes, "processing_run.content_hashes");
  return value as ProcessingRun;
}

export function parseSolverJob(value: unknown): SolverJob {
  const job = object(value, "job");
  for (const field of ["job_id", "owner_id", "project_id", "dataset_id", "method_id", "method_version", "survey_geometry_id", "model_parameterization", "starting_model_id", "data_weights_id", "regularizer"])
    nonempty(job[field], `job.${field}`);
  integer(job.attempt, "job.attempt", 1);
  integer(job.dataset_version, "job.dataset_version", 1);
  choice(job.execution_lane, ["online-cpu", "client-live", "offline-local", "replay"] as const, "job.execution_lane");
  scalarParameters(job.mesh, "job.mesh");
  if (job.reference_model_id !== null) nonempty(job.reference_model_id, "job.reference_model_id");
  const bounds = object(job.physical_bounds, "job.physical_bounds");
  if (finite(bounds.lower, "job.physical_bounds.lower") >= finite(bounds.upper, "job.physical_bounds.upper")) fail("job.physical_bounds", "invalid physical bounds");
  nonempty(bounds.unit, "job.physical_bounds.unit");
  nonnegative(job.beta, "job.beta");
  integer(job.seed, "job.seed");
  const preflight = object(job.preflight, "job.preflight");
  for (const field of ["estimated_wall_seconds", "estimated_peak_rss_bytes", "estimated_scratch_bytes"]) nonnegative(preflight[field], `job.preflight.${field}`);
  const admission = object(job.admission, "job.admission");
  choice(admission.verdict, ["admitted", "rejected"] as const, "job.admission.verdict");
  if (admission.verdict === "rejected") nonempty(admission.reason, "job.admission.reason");
  choice(job.state, ["queued", "running", "succeeded", "failed", "cancelled", "nonconverged", "ineligible"] as const, "job.state");
  const progress = finite(job.progress, "job.progress");
  if (progress < 0 || progress > 1) fail("job.progress", "outside [0,1]");
  if (job.worker_id !== null) nonempty(job.worker_id, "job.worker_id");
  const timestamps = object(job.timestamps, "job.timestamps");
  timestamp(timestamps.created_at, "job.timestamps.created_at");
  for (const field of ["started_at", "ended_at"]) if (timestamps[field] !== null) timestamp(timestamps[field], `job.timestamps.${field}`);
  const measured = object(job.measured, "job.measured");
  for (const field of ["wall_seconds", "peak_rss_bytes", "scratch_bytes"]) if (measured[field] !== null) nonnegative(measured[field], `job.measured.${field}`);
  if (job.error !== null) { const error = object(job.error, "job.error"); nonempty(error.code, "job.error.code"); nonempty(error.message, "job.error.message"); }
  if (job.state === "succeeded" && admission.verdict !== "admitted") fail("job.state", "rejected job cannot succeed");
  return value as SolverJob;
}

export function parseResultArtifact(value: unknown): ResultArtifact {
  const result = object(value, "result");
  for (const field of ["schema_version", "result_id", "job_id", "input_dataset_id", "stopping_reason", "uncertainty_definition", "held_out_partition", "licence"])
    nonempty(result[field], `result.${field}`);
  const inputHashes = array(result.input_hashes, "result.input_hashes");
  if (!inputHashes.length) fail("result.input_hashes", "missing input hashes");
  inputHashes.forEach((digest, index) => sha(digest, `result.input_hashes[${index}]`));
  const engine = object(result.engine, "result.engine");
  nonempty(engine.id, "result.engine.id");
  nonempty(engine.version, "result.engine.version");
  sha(engine.digest, "result.engine.digest");
  const origin = choice(result.data_origin, ["synthetic", "field"] as const, "result.data_origin");
  const axes = dimensions(result.axes, "result.axes");
  const observed = evidenceArray(result.observed, "result.observed", axes);
  const predicted = evidenceArray(result.predicted, "result.predicted", axes);
  const residual = evidenceArray(result.signed_residual, "result.signed_residual", axes);
  choice(result.residual_convention, ["observed-minus-predicted"] as const, "result.residual_convention");
  const normalized = evidenceArray(result.normalized_residual, "result.normalized_residual", axes);
  sameShape(observed, predicted, "result.predicted");
  sameShape(observed, residual, "result.signed_residual");
  sameShape(observed, normalized, "result.normalized_residual");
  if (observed.unit !== predicted.unit || observed.unit !== residual.unit || normalized.unit !== "1") fail("result", "observation/residual units disagree");
  for (let index = 0; index < residual.values.length; index++) {
    const expected = observed.values[index] - predicted.values[index];
    if (Math.abs(residual.values[index] - expected) > 1e-8 * Math.max(1, Math.abs(expected)))
      fail("result.signed_residual", `sign or value differs at ${index}`);
  }
  const model = evidenceArray(result.model, "result.model", axes);
  if (origin === "field" && result.truth !== null) fail("result.truth", "field data cannot have synthetic truth");
  if (origin === "synthetic" && result.truth === null) fail("result.truth", "synthetic result requires declared truth");
  if (result.truth !== null) {
    const truth = evidenceArray(result.truth, "result.truth", axes);
    sameShape(model, truth, "result.truth");
    if (model.unit !== truth.unit) fail("result.truth", "truth and model units differ");
  }
  const objective = object(result.objective, "result.objective");
  if (!Object.keys(objective).length) fail("result.objective", "missing objective components");
  for (const [name, number] of Object.entries(objective)) finite(number, `result.objective.${name}`);
  if (result.sensitivity !== null) evidenceArray(result.sensitivity, "result.sensitivity", axes);
  if (result.coverage !== null) evidenceArray(result.coverage, "result.coverage", axes);
  if (result.sensitivity === null && result.coverage === null) nonempty(result.unavailable_reason, "result.unavailable_reason");
  const figures = object(result.figure_arrays, "result.figure_arrays");
  for (const [name, figure] of Object.entries(figures)) evidenceArray(figure, `result.figure_arrays.${name}`, axes);
  const provenance = object(result.provenance, "result.provenance");
  const nodes = textArray(provenance.nodes, "result.provenance.nodes");
  if (!nodes.length || new Set(nodes).size !== nodes.length) fail("result.provenance.nodes", "missing or duplicate provenance nodes");
  const adjacency = new Map(nodes.map(node => [node, [] as string[]]));
  array(provenance.edges, "result.provenance.edges").forEach((raw, index) => {
    const edge = object(raw, `result.provenance.edges[${index}]`);
    const from = nonempty(edge.from, "edge.from"), to = nonempty(edge.to, "edge.to");
    if (!nodes.includes(from) || !nodes.includes(to)) fail("result.provenance.edges", "edge references unknown node");
    adjacency.get(from)!.push(to);
  });
  const visiting = new Set<string>(), visited = new Set<string>();
  function visit(node: string): void {
    if (visiting.has(node)) fail("result.provenance", "provenance contains a cycle");
    if (visited.has(node)) return;
    visiting.add(node);
    for (const next of adjacency.get(node) ?? []) visit(next);
    visiting.delete(node);
    visited.add(node);
  }
  nodes.forEach(visit);
  choice(result.rights_decision, ["mirror", "provider-link-only", "derivative-only", "forbidden"] as const, "result.rights_decision");
  hashes(result.file_hashes, "result.file_hashes");
  textArray(result.interpretation_hypotheses, "result.interpretation_hypotheses");
  return value as ResultArtifact;
}
