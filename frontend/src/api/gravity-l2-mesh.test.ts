import { describe, expect, it } from "vitest";
import type { GravityDataset } from "./processing-contracts";
import { gravityL2Starter, resizeGravityL2Mesh } from "./gravity-l2-mesh";
import { validateGravityL2Parameters } from "./gravity-l2-contracts";

const survey = { xyz_m: [[500000, 6200000, 5], [500100, 6200000, 8], [500000, 6200100, 6]] } as Pick<GravityDataset, "xyz_m">;

describe("user survey gravity mesh builder", () => {
  it("creates a physically placed 4 × 4 × 3 x-fast 3D starter with 48 unknowns", () => {
    const parameters = gravityL2Starter(survey);
    expect([parameters.mesh.hx_m.length, parameters.mesh.hy_m.length, parameters.mesh.hz_m.length]).toEqual([4, 4, 3]);
    expect(parameters.mesh.active).toHaveLength(48);
    expect(parameters.prior.lower_kg_m3).toHaveLength(48);
    expect(parameters.mesh.origin_m).toEqual([500000, 6200000, -95]);
    expect(parameters.mesh.hx_m.reduce((sum, value) => sum + value, 0)).toBe(100);
    expect(parameters.mesh.hy_m.reduce((sum, value) => sum + value, 0)).toBe(100);
    expect(parameters.mesh.origin_m[2] + parameters.mesh.hz_m.reduce((sum, value) => sum + value, 0)).toBe(-20);
    expect(validateGravityL2Parameters(parameters)).toEqual(parameters);
  });

  it("resizes while preserving survey extents and vertical top, and makes per-cell resets explicit", () => {
    const original = gravityL2Starter(survey);
    original.mesh.active[0] = false;
    original.prior.start_kg_m3[0] = -50;
    original.prior.reference_kg_m3[0] = 25;
    original.prior.lower_kg_m3[0] = -300;
    original.prior.upper_kg_m3[0] = 300;
    const resized = resizeGravityL2Mesh(original, { x: 3, y: 2, z: 4 });
    expect([resized.mesh.hx_m.length, resized.mesh.hy_m.length, resized.mesh.hz_m.length]).toEqual([3, 2, 4]);
    expect(resized.mesh.active).toEqual(Array(24).fill(true));
    expect(resized.prior.start_kg_m3).toEqual(Array(24).fill(0));
    expect(resized.prior.reference_kg_m3).toEqual(Array(24).fill(0));
    expect(resized.prior.lower_kg_m3).toEqual(Array(24).fill(-300));
    expect(resized.prior.upper_kg_m3).toEqual(Array(24).fill(300));
    expect(resized.mesh.hx_m.reduce((sum, value) => sum + value, 0)).toBe(100);
    expect(resized.mesh.hy_m.reduce((sum, value) => sum + value, 0)).toBe(100);
    expect(resized.mesh.origin_m[2] + resized.mesh.hz_m.reduce((sum, value) => sum + value, 0)).toBe(-20);
    expect(validateGravityL2Parameters(resized)).toEqual(resized);
  });

  it("rejects dimensions outside the explicit per-axis and total-cell caps", () => {
    expect(() => gravityL2Starter(survey, { x: 65, y: 1, z: 1 })).toThrow(/resolution/);
    expect(() => resizeGravityL2Mesh(gravityL2Starter(survey), { x: 16, y: 16, z: 16 })).not.toThrow();
    expect(() => resizeGravityL2Mesh(gravityL2Starter(survey), { x: 64, y: 64, z: 2 })).toThrow(/resolution/);
  });
});
