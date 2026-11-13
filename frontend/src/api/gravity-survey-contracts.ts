import { hash, integer, keys, number, processingObject, processingText } from "./processing-contracts";

export const GRAVITY_SURVEY_VIEW_SCHEMA = "geophysics.gravity-survey-view/v1" as const;
type JsonRecord = Record<string, unknown>;
export type GravitySurveyView = {
  schema: typeof GRAVITY_SURVEY_VIEW_SCHEMA;
  method: "l2" | "irls";
  calibration_sha256: string;
  plan_sha256: string;
  selection: { status: string; selected_index: number | null; candidates: JsonRecord[] };
  fit: JsonRecord;
  cells: { active_cell_indices: number[]; bounds_m: number[][]; density_kg_m3: number[] | null };
  stations: JsonRecord;
  history: JsonRecord[];
  warnings: string[];
  scope: { source_verification: "external_required_not_performed_by_solver"; geometry_error_propagated: false;
    field_eligible: false; full_M02_accepted: false; API_accepted: false; host_accepted: false; GPU_accepted: false };
};

const fail = (message: string): never => { throw new Error(`M02 inspection contract rejected: ${message}`); };
const obj = (value: unknown, name: string): JsonRecord => processingObject(value, name);
const exact = (value: JsonRecord, expected: string[], name: string) => keys(value, expected, name);
const vec = (value: unknown, n: number, name: string): number[] => {
  if (!Array.isArray(value) || value.length !== n) fail(`${name} dimensions`);
  const values = value as unknown[]; values.forEach(number);
  return values as number[];
};
const matrix = (value: unknown, rows: number, columns: number, name: string): number[][] => {
  if (!Array.isArray(value) || value.length !== rows) fail(`${name} row count`);
  return (value as unknown[]).map((row, index) => vec(row, columns, `${name}[${index}]`));
};
const nullableNumber = (value: unknown, name: string) => { if (value !== null) { try { number(value); } catch { fail(`${name} must be finite`); } } };
const nullOrVector = (value: unknown, length: number, name: string) => {
  if (value !== null) vec(value, length, name);
};

function parseHistory(value: unknown): JsonRecord[] {
  if (!Array.isArray(value) || value.length > 201) fail("history cap");
  return (value as unknown[]).map((item, index) => {
    const row = obj(item, `history[${index}]`);
    const phase = processingText(row.phase, "history phase");
    const base = ["accepted_index", "phase", "stage_index"];
    const measured = ["phi_d", "phi_m", "phi_engine", "kkt_normalized", "line_search_count", "cg_count"];
    exact(row, phase === "auxiliary_adoption" ? base : [...base, ...measured], "history row");
    integer(row.accepted_index, 0, 200);
    if (row.accepted_index !== index) fail("history order");
    if (!["initialization", "auxiliary_adoption", "native_inner", "l2"].includes(phase)) fail("history phase");
    if (row.stage_index !== null) integer(row.stage_index, 0, 20);
    for (const key of ["phi_d", "phi_m", "phi_engine", "kkt_normalized"]) nullableNumber(row[key], key);
    for (const key of ["line_search_count", "cg_count"]) if (row[key] !== null) integer(row[key], 0, 200);
    return row;
  });
}

function parseCandidates(value: unknown): JsonRecord[] {
  if (!Array.isArray(value) || value.length !== 8) fail("exact eight candidates required");
  return (value as unknown[]).map((candidate, index) => {
    const row = obj(candidate, `candidate[${index}]`);
    exact(row, ["index", "beta", "eligible", "score", "reason", "folds"], "candidate");
    integer(row.index, 0, 7); if (row.index !== index) fail("candidate order");
    number(row.beta); if (typeof row.eligible !== "boolean") fail("candidate eligibility");
    nullableNumber(row.score, "candidate score"); processingText(row.reason, "candidate reason");
    if (!Array.isArray(row.folds) || row.folds.length !== 3) fail("exact three folds required");
    (row.folds as unknown[]).forEach((item, foldIndex) => {
      const fold = obj(item, "candidate fold");
      exact(fold, ["fit_index", "status", "reason", "validation_phi_d", "validation_wrms", "validation_rmse_mgal"], "candidate fold");
      if (fold.fit_index !== null) integer(fold.fit_index, 0, 23);
      processingText(fold.status, "fold status"); processingText(fold.reason, "fold reason");
      for (const key of ["validation_phi_d", "validation_wrms", "validation_rmse_mgal"]) nullableNumber(fold[key], key);
      if (fold.fit_index !== null && fold.fit_index !== 3 * index + foldIndex) fail("fold reference");
    });
    return row;
  });
}

function parseStageBook(value: unknown): JsonRecord[] {
  if (!Array.isArray(value) || value.length > 21) fail("stage book cap");
  return (value as unknown[]).map((item, index) => {
    const row = obj(item, "stage book row");
    if (row.index !== index) fail("stage book order");
    if ("inner_status" in row) {
      exact(row, ["index", "epsilon", "weight_sha256", "operator_sha256", "start_row", "adopted_row", "stop_row", "attempt_count", "inner_status", "inner_reason", "inner_iterations", "inner_phi_d", "inner_phi_m", "inner_phi_engine", "inner_kkt_normalized"], "corrected stage book row");
      if (!Array.isArray(row.epsilon) || row.epsilon.length !== 4) fail("stage epsilon"); (row.epsilon as unknown[]).forEach(number);
      for (const key of ["weight_sha256", "operator_sha256"]) hash(row[key]);
      for (const key of ["start_row", "adopted_row", "stop_row"]) integer(row[key], 0, 200);
      integer(row.attempt_count, 0, 200); integer(row.inner_iterations, 0, 200);
      processingText(row.inner_status, "stage status"); processingText(row.inner_reason, "stage reason");
      for (const key of ["inner_phi_d", "inner_phi_m", "inner_phi_engine", "inner_kkt_normalized"]) nullableNumber(row[key], key);
    } else {
      exact(row, ["index", "accepted_span", "model_span", "beta_engine", "epsilon", "weight_sha256", "operator_sha256", "status", "reason", "metrics"], "legacy stage book row");
      vec(row.accepted_span, 2, "accepted span").forEach(x => integer(x, 0, 200));
      vec(row.model_span, 2, "model span").forEach(x => integer(x, 0, 200));
      number(row.beta_engine); if (!Array.isArray(row.epsilon) || row.epsilon.length !== 4) fail("stage epsilon"); (row.epsilon as unknown[]).forEach(number);
      for (const key of ["weight_sha256", "operator_sha256"]) if (!Array.isArray(row[key]) || row[key].length !== 4) fail("stage component hashes");
      (row.weight_sha256 as unknown[]).forEach(hash); (row.operator_sha256 as unknown[]).forEach(hash);
      processingText(row.status, "stage status"); processingText(row.reason, "stage reason");
      const metrics = obj(row.metrics, "stage metrics"); Object.values(metrics).forEach(value => nullableNumber(value, "stage metric"));
    }
    return row;
  });
}

export function parseGravitySurveyView(value: unknown): GravitySurveyView {
  const packet = obj(value, "gravity survey view");
  exact(packet, ["schema", "method", "calibration_sha256", "plan_sha256", "selection", "fit", "cells", "stations", "history", "warnings", "scope"], "gravity survey view");
  if (packet.schema !== GRAVITY_SURVEY_VIEW_SCHEMA || !["l2", "irls"].includes(String(packet.method))) fail("schema/method");
  hash(packet.calibration_sha256); hash(packet.plan_sha256);
  const selection = obj(packet.selection, "selection");
  exact(selection, ["status", "selected_index", "candidates"], "selection");
  processingText(selection.status, "selection status");
  if (selection.selected_index !== null) integer(selection.selected_index, 0, 7);
  parseCandidates(selection.candidates);

  const fit = obj(packet.fit, "fit");
  exact(fit, ["index", "status", "reason", "accepted_state_count", "frame_index", "runtime_epoch", "policy_sha256", "fit_sha256", "frame_model_sha256", "recipe_sha256", "beta_candidate", "beta_engine", "terminal", "terminal_metrics", "stage_book"], "fit");
  integer(fit.index, 0, 24); processingText(fit.status, "fit status"); processingText(fit.reason, "fit reason");
  integer(fit.accepted_state_count, 0, 201);
  if (fit.frame_index !== null) integer(fit.frame_index, 0, 200);
  processingText(fit.runtime_epoch, "runtime epoch");
  for (const key of ["policy_sha256", "fit_sha256", "recipe_sha256"]) hash(fit[key]);
  if (fit.frame_model_sha256 === null) { if (fit.accepted_state_count !== 0) fail("missing actual frame hash"); }
  else hash(fit.frame_model_sha256);
  nullableNumber(fit.beta_candidate, "candidate beta"); nullableNumber(fit.beta_engine, "engine beta");
  if (fit.terminal !== null) obj(fit.terminal, "terminal frame");
  const terminalMetrics = obj(fit.terminal_metrics, "terminal metrics");
  exact(terminalMetrics, ["phi_d", "phi_m", "phi_engine", "wrms", "kkt_normalized", "canonical_absolute_kkt", "canonical_weight_mismatch"], "terminal metrics");
  Object.values(terminalMetrics).forEach(value => nullableNumber(value, "terminal metric"));
  const stages = parseStageBook(fit.stage_book);

  const cells = obj(packet.cells, "cells");
  exact(cells, ["active_cell_indices", "bounds_m", "density_kg_m3"], "cells");
  if (!Array.isArray(cells.active_cell_indices) || cells.active_cell_indices.length > 4096) fail("cell count");
  const activeIndices = cells.active_cell_indices as unknown[];
  activeIndices.forEach(x => integer(x, 0, Number.MAX_SAFE_INTEGER));
  matrix(cells.bounds_m, activeIndices.length, 6, "cell bounds");
  nullOrVector(cells.density_kg_m3, activeIndices.length, "density");

  const stations = obj(packet.stations, "stations");
  exact(stations, ["row_indices", "ids", "partition_group_ids", "receivers_m", "observed_mgal", "predicted_mgal", "residual_observed_minus_predicted_mgal", "residual_convention", "acceleration_unit", "vertical_positive"], "stations");
  if (!Array.isArray(stations.row_indices) || stations.row_indices.length > 2048) fail("station count");
  const rowIndices = stations.row_indices as unknown[];
  const n = rowIndices.length;
  rowIndices.forEach(x => integer(x, 0, Number.MAX_SAFE_INTEGER));
  for (const key of ["ids", "partition_group_ids"]) if (!Array.isArray(stations[key]) || stations[key].length !== n) fail(`${key} count`);
  (stations.ids as unknown[]).forEach(x => processingText(x, "station id"));
  (stations.partition_group_ids as unknown[]).forEach(x => processingText(x, "station group"));
  matrix(stations.receivers_m, n, 3, "receivers"); vec(stations.observed_mgal, n, "observed");
  nullOrVector(stations.predicted_mgal, n, "predicted");
  nullOrVector(stations.residual_observed_minus_predicted_mgal, n, "residual");
  if (stations.residual_convention !== "observed_minus_predicted" || stations.acceleration_unit !== "mGal" || stations.vertical_positive !== "up") fail("residual units or convention");
  if ((stations.predicted_mgal === null) !== (stations.residual_observed_minus_predicted_mgal === null)) fail("prediction/residual availability mismatch");

  const history = parseHistory(packet.history);
  if (history.length !== fit.accepted_state_count || (history.length && fit.frame_index === null) || (history.length && (fit.frame_index as number) >= history.length)) fail("fit/history/frame binding");
  if (history.length && stages.length && stages.length !== 21) fail("stage/history recipe length");
  if (!Array.isArray(packet.warnings)) fail("warnings"); (packet.warnings as unknown[]).forEach(x => processingText(x, "warning"));
  const scope = obj(packet.scope, "scope");
  exact(scope, ["source_verification", "geometry_error_propagated", "field_eligible", "full_M02_accepted", "API_accepted", "host_accepted", "GPU_accepted"], "scope");
  if (scope.source_verification !== "external_required_not_performed_by_solver" ||
      ["geometry_error_propagated", "field_eligible", "full_M02_accepted", "API_accepted", "host_accepted", "GPU_accepted"].some(k => scope[k] !== false)) fail("scientific scope claim");
  return packet as unknown as GravitySurveyView;
}
