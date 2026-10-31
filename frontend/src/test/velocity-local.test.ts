import { describe, expect, it, vi } from "vitest";
import { readVelocityFiles, velocitySelection, parseVelocityResult, strictVelocityJson } from "../api/velocity-local-contracts";

// STRUCTURAL parser controls, not a computed inverse or physical replay fixture.
function control(learned = false) {
  const n = 8, predicted = Array(n).fill(.4), times = predicted.map((v, i) => v + (i % 2 ? .002 : -.001));
  const residual = times.map(v => v - .4), normalized = residual.map(v => v / .001);
  const chi = normalized.reduce((s, v) => s + v * v, 0);
  const record = { velocity_m_s: Array.from({ length: 16 }, () => Array(16).fill(2000)), predicted_s: predicted, residual_s: residual,
    normalized_residual: normalized, bilinear_predicted_s: predicted, cell_vs_bilinear_rmse_s: 0, data_chi_square: chi, data_wrms: Math.sqrt(chi / n) };
  return { schema: "geophysics.velocity-result/v1", status: "computed", request: {
    schema: "geophysics.velocity-user-data/v1", id: "parser-control", source: { citation: "Structural parser-only control, not computed evidence", rights: "owner-permitted", scope: "synthetic-control" },
    frame: "local-x-z-down", units: { distance: "m", time: "s", velocity: "m/s" }, ray_ids: Array.from({ length: n }, (_, i) => `ray-${i}`),
    rays_m: Array.from({ length: n }, (_, i) => [0, 25 + 50 * i, 800, 25 + 50 * i]), times_s: times, sigma_s: Array(n).fill(.001), lambda: 100 },
    source: { sha256: "a".repeat(64), bytes: 1024 }, axes: { x_m: Array.from({ length: 16 }, (_, i) => 25 + 50 * i), depth_m: Array.from({ length: 16 }, (_, i) => 25 + 50 * i), order: ["depth", "distance"] },
    coverage_m: Array.from({ length: 16 }, () => Array(16).fill(50)), results: { classical: { ...record, clipped_cells: 0, regularizer: 0,
      solver: "Cholesky unconstrained normal equation followed by explicit slowness clipping", bound_constrained_optimum_certified: false }, ...(learned ? { learned: structuredClone(record) } : {}) },
    learned_domain: learned ? { training_geometry: false, training_noise: true, field_validated: false, heldout_advantage: false } : null,
    warnings: ["Straight-ray approximation; no bent-ray or field accuracy established"], engine: { numpy: "2.2.6", scipy: "1.15.2", user_tool_sha256: "b".repeat(64), velocity_operator_sha256: "c".repeat(64),
      checkpoint_sha256: learned ? "d".repeat(64) : null, checkpoint_protocol: learned ? "original" : null, refinement_code_sha256: null },
    claims: { field_truth_known: false, field_validated: false, heldout_advantage: false, online_admitted: false } };
}
async function files(value: unknown) {
  const result = new Blob([JSON.stringify(value)]), bytes = await result.arrayBuffer();
  const digest = [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))].map(x => x.toString(16).padStart(2, "0")).join("");
  const doc = value as ReturnType<typeof control>;
  return { result, manifest: new Blob([JSON.stringify({ schema: "geophysics.velocity-bundle/v1", result_sha256: digest, result_bytes: bytes.byteLength, source: doc.source, engine: doc.engine })]) };
}
describe("local velocity scalar admission, not producer physical replay", () => {
  it("rejects both file sizes before either byte read", async () => {
    const read = vi.fn();
    for (const size of [0, NaN, 1.5, 4194305]) await expect(readVelocityFiles({ size, arrayBuffer: read } as unknown as Blob, new Blob(["{}"]))).rejects.toThrow();
    await expect(readVelocityFiles({ size: 1, arrayBuffer: read } as unknown as Blob, { size: 4097, arrayBuffer: read } as unknown as Blob)).rejects.toThrow();
    expect(read).not.toHaveBeenCalled();
  });
  it("binds original result bytes and declared source without claiming authenticity", async () => {
    const c = control(), f = await files(c), loaded = await readVelocityFiles(f.result, f.manifest);
    expect(loaded.result).toEqual(c); expect(loaded.resultBytes).toBe(f.result.size);
    expect(loaded.physicsReplayed).toBe(false);
    await expect(readVelocityFiles(new Blob([JSON.stringify(c) + " "]), f.manifest)).rejects.toThrow();
  });
  it("checks scalar identities even if changed result is rehashed", async () => {
    const c = control(); c.results.classical.residual_s[0] += .01;
    const f = await files(c); await expect(readVelocityFiles(f.result, f.manifest)).rejects.toThrow();
  });
  it("exports exact linked original rays/errors/map cells and selected actual model", () => {
    const c = control(true), before = JSON.stringify(c), r = parseVelocityResult(c);
    const p = velocitySelection(r, "learned", 3, 4, 5);
    expect(p.ray.id).toBe("ray-3"); expect(p.ray.endpoints_m).toEqual(c.request.rays_m[3]);
    expect(p.ray.residual_s).toBe(c.results.learned!.residual_s[3]); expect(p.cell).toEqual({ x_index: 4, depth_index: 5, x_m: 225, depth_m: 275, velocity_m_s: 2000, coverage_m: 50 });
    expect(JSON.stringify(c)).toBe(before);
    expect(() => velocitySelection(parseVelocityResult(control()), "learned", 0, 0, 0)).toThrow();
  });
  it.each(["original", "physics-v2"])("admits %s only with matching checkpoint/domain contract", protocol => {
    const c = control(true); c.engine.checkpoint_protocol = protocol;
    if (protocol === "physics-v2") c.engine.refinement_code_sha256 = "e".repeat(64) as never;
    expect(parseVelocityResult(c).engine.checkpoint_protocol).toBe(protocol);
  });
  it.each([
    (c: ReturnType<typeof control>) => { c.request.sigma_s[0] = 0; },
    c => { c.request.rays_m[0][2] = 801; },
    c => { c.axes.x_m[0] = 0; },
    c => { c.coverage_m[0][0] = -1; },
    c => { c.results.classical.velocity_m_s[0][0] = NaN; },
    c => { c.results.classical.normalized_residual[0] = 0; },
    c => { c.results.classical.data_wrms += 1; },
    c => { c.request.ray_ids[1] = c.request.ray_ids[0]; },
    c => { (c.claims as Record<string, boolean>).field_validated = true; },
  ] satisfies ((c: ReturnType<typeof control>) => void)[])("rejects malformed/nonfinite/false-claim control %#", mutate => {
    const c = control(); mutate(c); expect(() => parseVelocityResult(c)).toThrow();
  });
  it("rejects duplicate decoded keys, depth, nodes, invalid UTF8 and unknown fields", () => {
    const bytes = (text: string) => new TextEncoder().encode(text);
    for (const text of ['{"id":1,"\\u0069d":2}', "[".repeat(13) + "0" + "]".repeat(13), "[" + Array(160001).fill("0").join(",") + "]", '{"x":NaN}']) expect(() => strictVelocityJson(bytes(text))).toThrow();
    expect(() => strictVelocityJson(new Uint8Array([255]))).toThrow();
    expect(() => parseVelocityResult({ ...control(), truth: 1 })).toThrow();
  });
});
