// Independent five-station test control, never bundled as application data.
import { createHash } from "node:crypto";
import { zipSync, strToU8 } from "fflate";
import { FLAG_METHOD, type GravityDataset, type DatasetReceipt, type ProcessingJob, type FlagResult } from "../../api/processing-contracts";
export const id = (n: number) => `00000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
export const digest = (bytes: Uint8Array) => createHash("sha256").update(bytes).digest("hex");
export const bytes = (object: unknown) => strToU8(JSON.stringify(object));
export function fixture() {
  const dataset: GravityDataset = {
    schema: "geophysics.observation-dataset/v1", dataset_id: id(3), version: 1, owner_id: id(1), project_id: id(2), raw_asset_id: id(4), parent_raw_sha256: "a".repeat(64),
    parser_version: "gravity-station-csv/v1", modality: "gravity_station", dimensions: {station: 5}, axis_order: ["station"], station_ids: ["S1", "S2", "S3", "S4", "S5"],
    xyz_m: [[500000, 6200000, 100], [500010, 6200010, 101], [500020, 6200000, 100], [500030, 6200010, 100], [500040, 6200000, 100]],
    observed_mgal: [1, 2, 3, 4, 100], sigma_mgal: [.1, .1, .1, .1, .1], uncertainty_kind: "per_station_standard_deviation", mask: [false,false,false,false,false], missing_reasons: [null,null,null,null,null],
    physical_metadata: {coordinate_reference: "epsg", epsg: 32719, local_crs: null, axis_order: "xy", horizontal_datum: "WGS84", vertical_datum: "survey benchmark", vertical_positive: "up", horizontal_unit: "m", vertical_unit: "m", measurement_unit: "mGal", epoch_utc: "2026-10-03T12:00:00Z", component_frame: "local vertical down", geometry: {station_id_column: "station", x_column: "x", y_column: "y", z_column: "z", value_column: "g", sigma_column: "sigma"}},
    correction_history: [], qc_verdict: "parsed_for_flag_qc_only", rights_decision: "provider-link-only", rights_statement: "Private test control", attribution: "Independent test control",
  };
  const datasetHash = digest(bytes(dataset));
  const receipt: DatasetReceipt = {schema: dataset.schema, dataset_id: dataset.dataset_id, project_id: dataset.project_id, raw_asset_id: dataset.raw_asset_id, version: 1, modality: "gravity_station", row_count: 5, parser_version: dataset.parser_version, raw_sha256: dataset.parent_raw_sha256, sha256: datasetHash, created_at: "2026-10-03T12:00:00Z", qc_verdict: dataset.qc_verdict};
  const job: ProcessingJob = {job_id: id(5), project_id: id(2), dataset_id: id(3), dataset_sha256: datasetHash, method_id: FLAG_METHOD,
    request: {schema: "geophysics.processing-request/v1", job_id: id(5), project_id: id(2), dataset_id: id(3), dataset_sha256: datasetHash, method_id: FLAG_METHOD, parameters: {threshold: 6}}, request_sha256: "b".repeat(64),
    preflight: {estimated_memory_bytes: 33554432, memory_limit_bytes: 268435456, scratch_limit_bytes: 8388608, wall_limit_seconds: 30}, state: "succeeded", cancel_requested: false,
    created_at: "2026-10-03T12:00:00Z", started_at: "2026-10-03T12:00:01Z", finished_at: "2026-10-03T12:00:02Z", wall_ms: 1000, peak_rss_bytes: 30000000, scratch_bytes: 2000, result_sha256: null, error: null, result_url: `/api/projects/${id(2)}/jobs/${id(5)}/result`};
  const result: FlagResult = {schema: "geophysics.processing-result/v1", job_id: job.job_id, dataset_id: dataset.dataset_id, dataset_sha256: datasetHash, method_id: FLAG_METHOD, request_sha256: job.request_sha256, engine_sha256: "c".repeat(64), parameters: {threshold: 6}, axis_order: ["station"], dimensions: dataset.dimensions,
    station_ids: dataset.station_ids, xyz_m: dataset.xyz_m, observed_mgal: dataset.observed_mgal, sigma_mgal: dataset.sigma_mgal, outlier_flag: [false,false,false,false,true], robust_score: [2/1.4826,1/1.4826,0,1/1.4826,97/1.4826],
    statistics: {median_mgal: 3, mad_mgal: 1, scaled_mad_mgal: 1.4826, flagged_count: 1}, uncertainty_kind: dataset.uncertainty_kind, physical_metadata: dataset.physical_metadata, rights_decision: dataset.rights_decision, rights_statement: dataset.rights_statement,
    correction_history: [{method_id: FLAG_METHOD, parameters: {threshold: 6}, effect: "flag_only; observations and uncertainty unchanged"}], interpretation_limit: "Statistical flags only; no datum correction, anomaly transform, exclusion, model or inversion"};
  job.result_sha256 = digest(bytes(result));
  const manifest = {schema: "geophysics.processing-bundle/v1", dataset_id: dataset.dataset_id, job_id: job.job_id, method_id: FLAG_METHOD, parameters: result.parameters, rights_decision: dataset.rights_decision, rights_statement: dataset.rights_statement, axes: dataset.axis_order, dimensions: dataset.dimensions, units: {position: "m", observation: "mGal", uncertainty: "mGal"}, provenance: {raw_sha256: dataset.parent_raw_sha256, dataset_sha256: datasetHash, request_sha256: job.request_sha256, engine_sha256: result.engine_sha256}, members: {"dataset.json": {sha256: datasetHash, bytes: bytes(dataset).length}, "result.json": {sha256: job.result_sha256, bytes: bytes(result).length}}, raw_bytes_included: false};
  const bundle = (overrides: Record<string, Uint8Array> = {}) => new Blob([Uint8Array.from(zipSync({"manifest.json": bytes(manifest), "dataset.json": bytes(dataset), "result.json": bytes(result), ...overrides}, {level: 0})).buffer]);
  return {dataset, receipt, job, result, manifest, bundle};
}
