import { describe, expect, it } from "vitest";
import { parseObservationDataset, parseProcessingRun, parseRawAsset, parseResultArtifact, parseSolverJob, parseSourceRecord } from "../api/contracts";

const hash = "a".repeat(64);
const array = (values: number[], unit = "mGal", axis_order = ["station"], shape = [2]) => ({ axis_order, shape, values, unit });
const axis = { name: "station", size: 2, unit: "1", direction: "increasing" };
const source = {
  source_id: "src-1", provider: "USGS", location: { kind: "url", url: "https://example.org/data.csv" },
  doi: "10.5066/example", citation: "Provider source", retrieved_at: "2026-09-27T00:00:00Z",
  rights_statement: "Provider link only", rights_decision: "provider-link-only", declared_format: "csv",
  expected_bytes: 120, sha256: hash, attribution: "USGS",
};
const dataset = {
  dataset_id: "ds-1", version: 1, modality: "gravity", dimensions: [axis], axis_order: ["station"],
  coordinates: { kind: "local", name: "Survey grid", horizontal_datum: "local metric", vertical_datum: "survey level", vertical_positive: "up", axis_order: ["easting", "northing", "up"] },
  physical_units: { observed: "mGal", east: "m" },
  geometry: { kind: "stations", component_orientation: "vertical-positive-up", coordinates: { east: array([0, 10], "m") } },
  observed: array([1, 2]), mask: { included: [true, false], missing_reasons: { "1": "instrument dropout" } },
  uncertainty: { kind: "standard-deviation", unit: "mGal", values: array([0.1, 0.2]), covariance: null },
  correction_history: [{ name: "drift", parameters: { reference: 1 }, reversible: true }],
  parser: { name: "gravity-csv", version: "1" }, parent_raw_hashes: [hash], qc_verdict: "passed",
};
const job = {
  job_id: "job-1", attempt: 1, owner_id: "owner-1", project_id: "project-1", dataset_id: "ds-1", dataset_version: 1,
  method_id: "M02", method_version: "1", execution_lane: "online-cpu", survey_geometry_id: "stations-1",
  mesh: { cells: 8 }, model_parameterization: "density", starting_model_id: "start-1", reference_model_id: null,
  physical_bounds: { lower: -1000, upper: 1000, unit: "kg/m3" }, data_weights_id: "sigma-1", regularizer: "L2",
  beta: 1, seed: 42, preflight: { estimated_wall_seconds: 60, estimated_peak_rss_bytes: 1000, estimated_scratch_bytes: 100 },
  admission: { verdict: "admitted", reason: null }, state: "queued", progress: 0, worker_id: null,
  timestamps: { created_at: "2026-09-27T00:00:00Z", started_at: null, ended_at: null },
  measured: { wall_seconds: null, peak_rss_bytes: null, scratch_bytes: null }, error: null,
};
const rawAsset = {
  asset_id: "asset-1", owner_id: "owner-1", project_id: "project-1", source_id: "src-1",
  original_filename: "survey.csv", mime_type: "text/csv", detected_format: "gravity-csv",
  byte_count: 120, sha256: hash, storage_key: "project-1/raw/asset-1", receipt: "2026-09-27T00:00:00Z", validation_status: "valid",
};
const processingRun = {
  run_id: "processing-1", input_dataset_versions: [{ dataset_id: "ds-1", version: 1 }],
  transform_dag: [{ id: "drift", operation: "gravity-drift", input_ids: ["ds-1"], parameters: { reference: 1 } }],
  code_digest: hash, environment_digest: hash, output_dataset_versions: [{ dataset_id: "ds-1", version: 2 }],
  output_evidence: [{ dataset_id: "ds-1", version: 2, mask_sha256: hash, uncertainty_sha256: hash }],
  warnings: [], measured: { wall_seconds: 1, peak_rss_bytes: 1024, scratch_bytes: 0 }, content_hashes: { "derived.csv": hash },
};
const result = {
  schema_version: "1", result_id: "r-1", job_id: "job-1", input_dataset_id: "ds-1", input_hashes: [hash],
  engine: { id: "SimPEG", version: "1", digest: hash }, data_origin: "field", axes: [axis],
  observed: array([1, 2]), predicted: array([0.9, 1.9]), signed_residual: array([0.1, 0.1]), residual_convention: "observed-minus-predicted",
  normalized_residual: array([1, 1], "1"), model: array([10, 20], "kg/m3"), truth: null,
  objective: { data: 2, regularization: 1 }, stopping_reason: "converged", sensitivity: array([0.5, 0.4], "1"),
  coverage: null, unavailable_reason: null, uncertainty_definition: "survey standard deviations", held_out_partition: "line-2",
  figure_arrays: { residual: array([0.1, 0.1]) }, provenance: { nodes: ["raw", "dataset", "job"], edges: [{ from: "raw", to: "dataset" }, { from: "dataset", to: "job" }] },
  rights_decision: "derivative-only", licence: "CC-BY-4.0", file_hashes: { "result.json": hash }, interpretation_hypotheses: ["A possible density contrast"],
};
const clone = <T>(value: T): T => structuredClone(value);

describe("approved evidence mirrors", () => {
  it("accepts_valid_contract_records", () => {
    expect(parseSourceRecord(source).rights_decision).toBe("provider-link-only");
    expect(parseRawAsset(rawAsset).sha256).toBe(hash);
    expect(parseObservationDataset(dataset).axis_order).toEqual(["station"]);
    expect(parseProcessingRun(processingRun).transform_dag[0].operation).toBe("gravity-drift");
    expect(parseSolverJob(job).state).toBe("queued");
    expect(parseResultArtifact(result).data_origin).toBe("field");
  });

  it("rejects_invalid_evidence", () => {
    expect(() => parseSourceRecord({ ...source, sha256: "short" })).toThrow("SHA-256");
    expect(() => parseSourceRecord({ ...source, rights_decision: "publish-anyway" })).toThrow("rights_decision");
    expect(() => parseSourceRecord({ ...source, retrieved_at: "2026-09-27" })).toThrow("timestamp");
    expect(() => parseObservationDataset({ ...dataset, coordinates: { ...dataset.coordinates, vertical_datum: "" } })).toThrow("vertical_datum");
    expect(() => parseObservationDataset({ ...dataset, axis_order: ["depth"] })).toThrow("axis_order");
    expect(() => parseObservationDataset({ ...dataset, coordinates: { ...dataset.coordinates, axis_order: ["east", "east"] } })).toThrow("ambiguous");
    expect(() => parseObservationDataset({ ...dataset, mask: { included: [true, false], missing_reasons: {} } })).toThrow("missing reason");
    expect(() => parseProcessingRun({ ...processingRun, code_digest: "unknown" })).toThrow("SHA-256");
    expect(() => parseProcessingRun({ ...processingRun, output_evidence: [] })).toThrow("missing mask or uncertainty provenance");
    expect(() => parseProcessingRun({ ...processingRun, output_evidence: [{ ...processingRun.output_evidence[0], uncertainty_sha256: "short" }] })).toThrow("SHA-256");
    expect(() => parseProcessingRun({ ...processingRun, transform_dag: [{ id: "drift", operation: "drift", input_ids: ["drift"], parameters: {} }] })).toThrow("later step");
    expect(() => parseSolverJob({ ...job, state: "succeeded", admission: { verdict: "rejected", reason: "too large" } })).toThrow("cannot succeed");
    expect(() => parseResultArtifact({ ...result, truth: array([1, 2]) })).toThrow("field data cannot have synthetic truth");
    expect(() => parseResultArtifact({ ...result, observed: array([1]) })).toThrow("array length");
    expect(() => parseResultArtifact({ ...result, predicted: array([0.9, 1.9], "nT") })).toThrow("units disagree");
    expect(() => parseResultArtifact({ ...result, signed_residual: array([-0.1, -0.1]) })).toThrow("sign or value");
    expect(() => parseResultArtifact({ ...result, provenance: { nodes: ["a", "b"], edges: [{ from: "a", to: "b" }, { from: "b", to: "a" }] } })).toThrow("cycle");
    const nonfinite = clone(result);
    nonfinite.observed.values[0] = Number.NaN;
    expect(() => parseResultArtifact(nonfinite)).toThrow("finite number");
  });
});
