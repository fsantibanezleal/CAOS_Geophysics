import { describe, expect, it } from "vitest";
import { GRAVITY_SURVEY_VIEW_SCHEMA, parseGravitySurveyView } from "./gravity-survey-contracts";

const digest = "a".repeat(64);
function packet() {
  return {
    schema: GRAVITY_SURVEY_VIEW_SCHEMA, method: "irls", calibration_sha256: digest, plan_sha256: digest,
    selection: { status: "insufficient_candidates", selected_index: null,
      candidates: Array.from({ length: 8 }, (_, index) => ({ index, beta: 0.01 * 10 ** index,
        eligible: false, score: null, reason: "fold_failure",
        folds: Array.from({ length: 3 }, (_, fold) => ({ fit_index: 3 * index + fold,
          status: "nonconverged", reason: "line_search_failed", validation_phi_d: null,
          validation_wrms: null, validation_rmse_mgal: null })) })) },
    fit: { index: 0, status: "nonconverged", reason: "line_search_failed", accepted_state_count: 0,
      frame_index: null, runtime_epoch: "m02-survey-irls-cpu-1", policy_sha256: digest,
      fit_sha256: digest, frame_model_sha256: null, recipe_sha256: digest, beta_candidate: 0.01,
      beta_engine: 1.2, terminal: null,
      terminal_metrics: { phi_d: null, phi_m: null, phi_engine: null, wrms: null, kkt_normalized: null,
        canonical_absolute_kkt: null, canonical_weight_mismatch: null }, stage_book: [] },
    cells: { active_cell_indices: [0], bounds_m: [[0, 1, 0, 1, -2, -1]], density_kg_m3: null },
    stations: { row_indices: [0], ids: ["s-0"], partition_group_ids: ["line-0"], receivers_m: [[0, 0, 1]],
      observed_mgal: [0.2], predicted_mgal: null, residual_observed_minus_predicted_mgal: null,
      residual_convention: "observed_minus_predicted", acceleration_unit: "mGal", vertical_positive: "up" },
    history: [], warnings: ["rank_deficient"], scope: {
      source_verification: "external_required_not_performed_by_solver", geometry_error_propagated: false,
      field_eligible: false, full_M02_accepted: false, API_accepted: false, host_accepted: false, GPU_accepted: false,
    },
  };
}

describe("native gravity survey view contract", () => {
  it("retains all candidate/fold failure verdicts without inventing a frame", () => {
    const parsed = parseGravitySurveyView(packet());
    expect(parsed.selection.candidates).toHaveLength(8);
    expect(parsed.selection.candidates.reduce((n, candidate) => n + (candidate.folds as unknown[]).length, 0)).toBe(24);
    expect(parsed.fit.accepted_state_count).toBe(0);
    expect(parsed.cells.density_kg_m3).toBeNull();
    expect(parsed.stations.predicted_mgal).toBeNull();
  });
  it.each([
    ["unknown field", (p: Record<string, any>) => { p.outer_observations = [1]; }],
    ["missing fold", (p: Record<string, any>) => { p.selection.candidates[0].folds.pop(); }],
    ["forged acceptance", (p: Record<string, any>) => { p.scope.full_M02_accepted = true; }],
    ["bad residual convention", (p: Record<string, any>) => { p.stations.residual_convention = "predicted_minus_observed"; }],
    ["nonfinite value", (p: Record<string, any>) => { p.stations.observed_mgal[0] = Number.NaN; }],
  ])("rejects %s", (_name, mutate) => {
    const value = packet(); mutate(value as Record<string, any>);
    expect(() => parseGravitySurveyView(value)).toThrow();
  });
});
