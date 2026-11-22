import { describe, expect, it } from "vitest";
import { ertSurveyPoints } from "../components/ert-view-data";
import { parseProfileResult, profileSelection } from "../api/profile-local-contracts";

function result() {
  return {
    schema: "geophysics.supplied-profile-result/v1", method: "ert.topographic-profile/v1",
    metadata: { schema: "geophysics.supplied-profile/v1", method: "ert.topographic-profile/v1", source: {
      source_id: "test-profile", kind: "user_upload", citation: "test control",
      rights: { holder: "test operator", processing_allowed: true, redistribution_allowed: false }, sha256: "a".repeat(64), bytes: 16,
    }, frame: { horizontal_reference: "local", vertical_datum: "local", coordinate_unit: "m", vertical_positive: "up", profile_axes: ["distance", "elevation"] }, weights: { policy: "provider-example-conditional/v1" } },
    original: { sha256: "a".repeat(64), bytes: 16 },
    geometry: { sensor_xz_m: [[0, 0], [2, 0.5], [4, 1], [6, 0.5]], abmn_zero_based: [[0, 3, 1, 2], [0, 3, 1, 2], [0, 3, 1, 2], [0, 3, 1, 2]], row_ids_zero_based: [0, 1, 2, 3] },
    engine_report: { schema: "inverse-earth.local-ert-m07/v1", source_id: "test-profile", source_sha256: "a".repeat(64), source_bytes: 16,
      rights_decision: "supplied-declaration-not-verified", raw_publication: false, truth: null, field_geology_claim: null, inverse_status: "not-converged",
      qc: { sensor_count: 4, measurement_count: 4, topographic_relief_m: 1, reciprocal_pairs: [], flagged_rows: [] },
      split: { training_rows: [0, 1], heldout_rows: [2, 3] }, inverse: {
        mesh_cells: 2, model_resistivity_ohm_m: [100, 200], model_cell_center_xz_m: [[2 / 3, -2 / 3], [4 / 3, -4 / 3]], coverage_log10_sensitivity_per_cell: [-2, -1],
        observed_r_ohm: [1, 2, 3, 4], predicted_r_ohm: [1.1, 1.9, 3.2, 3.8], signed_residual_r_ohm: [0.1, -0.1, 0.2, -0.2],
        parameter_mesh: { schema: "geophysics.profile-parameter-mesh/v1", coordinate_unit: "m", vertical_positive: "up", node_xz_m: [[0, 0], [2, 0], [0, -2], [2, -2]], cell_node_ids: [[0, 1, 2], [1, 3, 2]] },
      } },
    code_hashes: { "ert.py": "b".repeat(64), "supplied_profiles.py": "c".repeat(64), "profile_mesh.py": "d".repeat(64) },
    numerical_settings: { lam: 10, maxIter: 12 },
    scope: { uploaded: false, raw_copied: false, execution: "explicit-local", rights: "operator-declaration-not-independent-permission-review", uncertainty: "assumed-not-calibrated", truth_available: false, residual_convention: "predicted-minus-observed" },
    content_sha256: "e".repeat(64),
  };
}

describe("M07 ERT result-view data", () => {
  it("preserves the supplied topographic elevation and exact ABMN electrode identities", () => {
    const parsed = parseProfileResult(result());
    expect(ertSurveyPoints(parsed.sensors, parsed.rows[0])).toEqual([
      { electrode: 0, x_m: 0, elevation_m: 0, label: "A" },
      { electrode: 1, x_m: 2, elevation_m: 0.5, label: "M" },
      { electrode: 2, x_m: 4, elevation_m: 1, label: "N" },
      { electrode: 3, x_m: 6, elevation_m: 0.5, label: "B" },
    ]);
  });

  it("exposes only producer-returned resistance, model and assumed-sigma values", () => {
    const parsed = parseProfileResult(result());
    const selected = profileSelection(parsed, 0, 2, 1);
    expect(selected.row).toMatchObject({ observed: 3, predicted: 3.2, residual: 0.2, sigma: 0.09, partition: "held" });
    expect(selected.cell).toMatchObject({ value: 200, unit: "Ω m", centre_m: [4 / 3, -4 / 3] });
    expect(parsed.models[0].report).not.toHaveProperty("apparent_resistivity");
  });
});
