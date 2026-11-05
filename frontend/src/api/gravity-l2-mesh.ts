import type { GravityL2Parameters } from "./gravity-l2-contracts";
import type { GravityDataset } from "./processing-contracts";

export type GravityMeshResolution = { x: number; y: number; z: number };

function meshCellCount({ x, y, z }: GravityMeshResolution): number {
  if (![x, y, z].every(value => Number.isSafeInteger(value) && value >= 1 && value <= 64) || x * y * z > 4096) {
    throw new Error("Gravity mesh resolution must be integer dimensions from 1 to 64 with at most 4096 cells");
  }
  return x * y * z;
}

const span = (values: number[]) => Math.max(25, Math.max(...values) - Math.min(...values));

export function gravityL2Starter(dataset: Pick<GravityDataset, "xyz_m">, resolution: GravityMeshResolution = { x: 4, y: 4, z: 3 }): GravityL2Parameters {
  const count = meshCellCount(resolution), xyz = dataset.xyz_m;
  if (xyz.length < 1 || xyz.some(point => point.length !== 3 || point.some(value => !Number.isFinite(value)))) {
    throw new Error("Gravity mesh requires finite three-coordinate station positions");
  }
  const xs = xyz.map(point => point[0]), ys = xyz.map(point => point[1]), zs = xyz.map(point => point[2]);
  const spanX = span(xs), spanY = span(ys), hx = spanX / resolution.x, hy = spanY / resolution.y;
  const hz = Math.max(25, Math.max(hx, hy) / 2), top = Math.min(...zs) - hz;
  const minStep = (values: number[]) => {
    const unique = Array.from(new Set(values)).sort((a, b) => a - b), differences = unique.slice(1).map((value, index) => value - unique[index]).filter(value => value > 0);
    return differences.length ? Math.max(0.01, Math.min(...differences) * 0.45) : Math.max(0.01, span(values) / 1000);
  };
  const blockX = minStep(xs), blockY = minStep(ys);
  return {
    schema: "gravity.survey-l2-parameters/v1", background_mgal: 0,
    mesh: { origin_m: [Math.min(...xs), Math.min(...ys), top - resolution.z * hz],
      hx_m: Array(resolution.x).fill(hx), hy_m: Array(resolution.y).fill(hy), hz_m: Array(resolution.z).fill(hz), active: Array(count).fill(true) },
    split: { block_origin_m: [Math.min(...xs), Math.min(...ys)], block_size_m: [blockX, blockY],
      buffer_m: Math.max(0.01, Math.min(blockX, blockY) * 0.25), seed: 104729 },
    prior: { lower_kg_m3: Array(count).fill(-500), upper_kg_m3: Array(count).fill(500),
      start_kg_m3: Array(count).fill(0), reference_kg_m3: Array(count).fill(0), density_scale_kg_m3: 100,
      lengths_m: [spanX, spanY, hz], basis: "user-authored uniform active-cell density parameters",
      reference_in_smooth: true, spatial_weights: "none" },
  };
}

export function resizeGravityL2Mesh(parameters: GravityL2Parameters, resolution: GravityMeshResolution): GravityL2Parameters {
  const count = meshCellCount(resolution), old = parameters.mesh, prior = parameters.prior;
  const extentX = old.hx_m.reduce((sum, width) => sum + width, 0), extentY = old.hy_m.reduce((sum, width) => sum + width, 0);
  const top = old.origin_m[2] + old.hz_m.reduce((sum, width) => sum + width, 0);
  const hz = Math.max(1e-6, Math.min(...old.hz_m));
  const lower = Math.max(...prior.lower_kg_m3), upper = Math.min(...prior.upper_kg_m3);
  if (!(extentX > 0 && extentY > 0 && lower < upper)) {
    throw new Error("Cannot regenerate mesh: require positive extents and ordered prior bounds");
  }
  const neutral = Math.max(lower, Math.min(upper, 0));
  return {
    ...parameters,
    mesh: { origin_m: [old.origin_m[0], old.origin_m[1], top - resolution.z * hz],
      hx_m: Array(resolution.x).fill(extentX / resolution.x), hy_m: Array(resolution.y).fill(extentY / resolution.y),
      hz_m: Array(resolution.z).fill(hz), active: Array(count).fill(true) },
    prior: { ...prior, lower_kg_m3: Array(count).fill(lower), upper_kg_m3: Array(count).fill(upper),
      start_kg_m3: Array(count).fill(neutral), reference_kg_m3: Array(count).fill(neutral) },
  };
}
