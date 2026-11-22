import { describe, expect, it } from "vitest";
import { densityCells } from "./GravityDensityView";
import { validateAcceptedFrames } from "../api/gravity-density-contract";
import type { GravityVolumeData } from "./GravityDensityView";

const data = (overrides: Partial<GravityVolumeData> = {}) => ({ active_cell_indices: [3, 8],
  bounds_m: [[100, 140, 210, 270, -90, -70], [140, 200, 210, 270, -70, -30]], density_kg_m3: [-125, 250], ...overrides });

describe("physical 3D gravity volume contract", () => {
  it("preserves physical bounds, active indices, signed density and actual cell centres", () => {
    expect(densityCells(data())).toEqual([
      { index: 3, bounds: [100, 140, 210, 270, -90, -70], density: -125, centre: [120, 240, -80] },
      { index: 8, bounds: [140, 200, 210, 270, -70, -30], density: 250, centre: [170, 240, -50] },
    ]);
  });
  it("returns no volume for an unstarted or unavailable fit", () => {
    expect(densityCells(data({ active_cell_indices: [3], bounds_m: [[0, 1, 0, 1, 0, 1]], density_kg_m3: null }))).toEqual([]);
  });
  it("rejects malformed dimensions, nonfinite values and physically invalid cells", () => {
    expect(() => densityCells(data({ active_cell_indices: [3], bounds_m: [[0, 1, 0, 1, 0]], density_kg_m3: [1] }))).toThrow(/invalid physical/);
    expect(() => densityCells(data({ active_cell_indices: [3], bounds_m: [[0, 0, 0, 1, 0, 1]], density_kg_m3: [1] }))).toThrow(/nonpositive extent/);
    expect(() => densityCells(data({ active_cell_indices: [3], bounds_m: [[0, 1, 0, 1, 0, 1]], density_kg_m3: [Infinity] }))).toThrow(/invalid physical/);
    expect(() => densityCells(data({ active_cell_indices: [3, 4], bounds_m: [[0, 1, 0, 1, 0, 1]], density_kg_m3: [1] }))).toThrow(/not aligned/);
    expect(() => densityCells(data({ active_cell_indices: [3], bounds_m: [[0, 1, 0, 1, 0, 1]], density_kg_m3: [1, 2] }))).toThrow(/not aligned/);
    expect(() => densityCells(data({ active_cell_indices: [3, 3] }))).toThrow(/unique nonnegative integers/);
  });
  it("replays finite accepted optimizer states and binds the last frame to the returned model", () => {
    const frames = [{ density_kg_m3: [0, 0], phi_engine: 12, kkt_normalized: 0.8 },
      { density_kg_m3: [-125, 250], phi_engine: 4, kkt_normalized: 1e-8 }];
    expect(validateAcceptedFrames(frames, [-125, 250], 2)).toEqual(frames);
    expect(() => validateAcceptedFrames(frames, [-124, 250], 2)).toThrow(/does not end/);
    expect(() => validateAcceptedFrames([{ ...frames[0], phi_engine: Number.NaN }], [0, 0], 2)).toThrow(/history is invalid/);
    expect(() => validateAcceptedFrames(Array(202).fill(frames[0]), [0, 0], 2)).toThrow(/history is invalid/);
  });
});
