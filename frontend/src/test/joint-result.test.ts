import { describe, expect, it } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { unzipSync } from "fflate";
import { importJointOutput, jointFrameSidecar, jointInstrumentFrame, jointJson, jointPhysicalRange, jointResponse, jointSidecar, jointState, exportJointOriginals, type JointFile } from "../api/joint-result";

export function actualJointFiles(root: string): JointFile[] {
  const entries: JointFile[] = [];
  function visit(dir: string) { for (const name of readdirSync(dir)) { const path = join(dir, name), info = statSync(path); if (info.isDirectory()) visit(path);
    else entries.push({ path: relative(root, path).replaceAll("\\", "/"), size: info.size, read: async () => new Uint8Array(readFileSync(path)) }); } }
  visit(root); return entries;
}
const root = process.env.GEOPHYSICS_JOINT_OUTPUT_FIXTURE;
const evaluation = process.env.GEOPHYSICS_JOINT_EVALUATION_FIXTURE;
const aborted = process.env.GEOPHYSICS_JOINT_ABORT_FIXTURE;
const durableAbort = process.env.GEOPHYSICS_JOINT_DURABLE_ABORT_FIXTURE;
const matrix = process.env.GEOPHYSICS_JOINT_MATRIX_FIXTURE;
const maximum = process.env.GEOPHYSICS_JOINT_MAX_OUTPUT_FIXTURE;
const instrument = process.env.GEOPHYSICS_JOINT_INSTRUMENT_FIXTURE;
const encode = (v: unknown) => new TextEncoder().encode(typeof v === "string" ? v : JSON.stringify(v));
const mutateJson = async (files: JointFile[], path: string, mutate: (v: Record<string, unknown>) => void) => {
  const original = files.find(f => f.path === path)!, v = JSON.parse(new TextDecoder().decode(await original.read())); mutate(v);
  const bytes = encode(v); const changed = files.map(f => f === original ? { ...f, size: bytes.length, read: async () => bytes } : f);
  // Rehashed metadata is not authentic: reach semantic guards after byte admission.
  const wf = changed.find(f => f.path === "workflow.json");
  if (wf && path !== "workflow.json") { const receipt = JSON.parse(new TextDecoder().decode(await wf.read()));
    receipt.private_export_bytes_before_receipt = changed.reduce((sum, f) => sum + (f === wf ? 0 : f.size), 0);
    const rb = encode(receipt); return changed.map(f => f === wf ? { ...f, size: rb.length, read: async () => rb } : f); }
  return changed;
};

describe("native local joint output, not a browser inverse", () => {
  it.skipIf(!instrument)("accepted state instrument", async () => {
    const inspection = await importJointOutput(actualJointFiles(instrument!)); expect(inspection.instrument).not.toBeNull();
    for (const e of inspection.instrument!.payload.entries as import("../api/joint-result").Json[]) { const entry = e as Record<string, import("../api/joint-result").Json>, key = entry.key as string;
      for (let i = 0; i < (entry.state_count as number); i++) { const frame = jointInstrumentFrame(inspection, key, i);
        if (entry.modality !== null) { expect(frame.coupling).toBeNull(); expect(Object.keys(frame.responses)).toEqual([entry.modality]); expect(Object.keys(frame.model.arrays).filter(k => ["density_kg_m3", "susceptibility_si"].includes(k))).toHaveLength(1); }
        else expect(frame.coupling!.face_contribution).toHaveLength(inspection.model!.arrays.density_kg_m3.shape[0]);
        for (const parts of Object.values(frame.responses)) for (const response of Object.values(parts!)) expect(response.residual.every((v, j) => v === response.predicted[j] - response.observed[j])).toBe(true);
      }
    }
    const state = jointInstrumentFrame(inspection, "c00", 1); expect(state.candidate!.status).toBe("nonconverged");
    expect(state.responses.gravity!.sealed.predicted).not.toEqual(jointResponse(inspection, "gravity", "sealed").predicted);
    const sidecar = jointFrameSidecar(inspection, "c25", 0); expect(sidecar.coupling).not.toBeNull(); expect(sidecar.responses).toHaveProperty("magnetic.sealed.metrics"); expect(sidecar.scientific_acceptance_verified).toBe(false);
    const baseline = jointInstrumentFrame(inspection, "baseline", 0); expect(baseline.entry.kind).toBe("independently_optimized_pair"); expect(baseline.entry.weights).toHaveProperty("coupling", 0);
    const selected = jointInstrumentFrame(inspection, "selected", 0); expect(selected.responses.magnetic!.sealed.predicted).toEqual(jointResponse(inspection, "magnetic", "sealed").predicted);
    await expect(importJointOutput(actualJointFiles(instrument!).map(f => f.path === "instrument/c25_face_contribution.npy" ? { ...f, read: async () => { const b = await f.read(); b[b.length - 1] ^= 1; return b; } } : f))).rejects.toThrow("digest mismatch");
  });
  it("does not invent negative susceptibility or constant legend values", () => {
    expect(jointPhysicalRange(new Float64Array([0, 0]), false)).toEqual([0, 0]);
    expect(jointPhysicalRange(new Float64Array([.003, .003]), false)).toEqual([.003, .003]);
    expect(jointPhysicalRange(new Float64Array([-120, 300]), true)).toEqual([-300, 300]);
    expect(jointPhysicalRange(new Float64Array([.002, .004]), false)).toEqual([.002, .004]);
  });
  it("rejects malformed transport before value loading", async () => {
    let reads = 0; const f = (path: string, size: number): JointFile => ({ path, size, read: async () => { reads++; return encode("{}"); } });
    for (const files of [[f("../workflow.json", 2)], [f("workflow.json", 268435457)], [f("workflow.json", 2), f("workflow.json", 2)], [f("output/workflow.json", 2), f("another/result/result.json", 2)], Array.from({ length: 1101 }, () => f("workflow.json", 2))]) await expect(importJointOutput(files)).rejects.toThrow();
    expect(reads).toBe(0);
    for (const json of ['{"status":1,"status":2}', '{"__proto__":{}}', '{"n":1e999}', '{"n":9007199254740993}', '{"a":' + '['.repeat(9) + '0' + ']'.repeat(9) + '}']) expect(() => jointJson(encode(json))).toThrow();
  });
  it.skipIf(!root)("imports actual workflow without scientific promotion", async () => {
    const result = await importJointOutput(actualJointFiles(root!));
    expect(result.outcome).toBe("completed"); expect(result.candidates).toHaveLength(26);
    expect(result.receipt.inverse_completed).toBe(true);
    expect(Object.values(result.limitations).every(v => v === false)).toBe(true);
    expect(result.result!.payload.claims).toMatchObject({ inverse_completed: false, recovery_verified: false });
    expect(result.files.size).toBeGreaterThan(550);
  });
  it.skipIf(!root)("preserves exact linked physical values", async () => {
    const result = await importJointOutput(actualJointFiles(root!)), response = jointResponse(result, "gravity", "sealed"), sidecar = jointSidecar(result, "gravity", "sealed", 0, 0, 0, 0);
    expect(response.residual[0]).toBe(response.predicted[0] - response.observed[0]);
    expect(sidecar.selected_response!.row).toBe(response.rows[0]);
    expect(sidecar.selected_cell!.density_kg_m3).toBe(result.frozen!.arrays.q.values[0] * (result.model!.payload.density_scale as number));
    expect(sidecar.selected_cell!.bounds_m).toHaveLength(6);
    await expect(importJointOutput(await mutateJson(actualJointFiles(root!), "models/model.json", v => { (v.payload as Record<string, unknown>).density_unit = "g_cm3"; }))).rejects.toThrow("native physical units");
  });
  it.skipIf(!root)("retains nonconverged states and exact exported coupling", async () => {
    const result = await importJointOutput(actualJointFiles(root!)), failed = result.candidates.find(c => c.status === "nonconverged")!;
    expect(failed).toBeDefined(); const state = jointState(failed, 0);
    expect(state.terminal_status).toBe("nonconverged"); expect(state.terminal_metrics_apply).toBe(false);
    expect(state.historical_prediction).toBeNull(); expect(state.terms!.coupling).toBe(failed.terms!.values[4]);
    const joint = result.candidates[25], terminal = jointState(joint, joint.iterations);
    expect(terminal.weights).toEqual(joint.weights); expect(terminal.terms!.coupling).toBe(joint.terms!.values[joint.iterations * 5 + 4]);
  });
  it.skipIf(!root)("round trips original bytes without promotion", async () => {
    const result = await importJointOutput(actualJointFiles(root!)), archive = unzipSync(await exportJointOriginals(result));
    expect(Object.keys(archive).sort()).toEqual([...result.files.keys()].sort());
    for (const [path, bytes] of result.files) expect(archive[path]).toEqual(bytes);
    const again = await importJointOutput(Object.entries(archive).map(([path, bytes]) => ({ path, size: bytes.length, read: async () => bytes })));
    expect(again.hashes).toEqual(result.hashes); expect(again.limitations.scientific_acceptance_verified).toBe(false);
    const original = result.files.get("frozen/q.npy")!; original[original.length - 1] ^= 1;
    await expect(exportJointOriginals(result)).rejects.toThrow("original changed");
  });
  it.skipIf(!root)("rejects bad headers hashes extra files and altered frozen identity", async () => {
    const files = actualJointFiles(root!);
    await expect(importJointOutput([...files, { path: "result/extra.npy", size: 2, read: async () => encode("{}") }])).rejects.toThrow();
    const bad = files.map(f => f.path === "frozen/q.npy" ? { ...f, read: async () => { const b = await f.read(); b[7] = 1; return b; } } : f);
    await expect(importJointOutput(bad)).rejects.toThrow("NPY1");
    const changed = files.map(f => f.path === "result/q.npy" ? { ...f, read: async () => { const b = await f.read(); b[b.length - 1] ^= 1; return b; } } : f);
    await expect(importJointOutput(changed)).rejects.toThrow("digest mismatch");
    await expect(importJointOutput(await mutateJson(files, "frozen/frozen.json", v => { (v.payload as Record<string, unknown>).frozen_sha256 = "0".repeat(64); }))).rejects.toThrow("identity");
    const controller = new AbortController(); controller.abort(); await expect(importJointOutput(files, controller.signal)).rejects.toThrow("cancelled");
  });
  it.skipIf(!evaluation)("does not promote actual supplied evaluation to inversion", async () => {
    const r = await importJointOutput(actualJointFiles(evaluation!)); expect(r.mode).toBe("evaluate"); expect(r.receipt.inverse_completed).toBe(false); expect(r.candidates).toEqual([]);
  });
  it.skipIf(!aborted)("retains aborted workflow without sealed promotion", async () => {
    const r = await importJointOutput(actualJointFiles(aborted!)); expect(r.outcome).toBe("failed"); expect(r.result).toBeNull(); expect(r.frozen).toBeNull(); expect(r.model).toBeNull();
    expect(r.receipt.inverse_completed).toBe(false); expect(r.candidates.at(-1)!.writerReplayed).toBe(false);
    expect(jointState(r.candidates.at(-1)!, 0).physical).toBeNull();
    expect(() => jointResponse(r, "gravity", "sealed")).toThrow();
  });
  it.skipIf(!aborted)("rejects altered abort phase and source-bound attempt declarations", async () => {
    const files = actualJointFiles(aborted!);
    await expect(importJointOutput(await mutateJson(files, "aborted/aborted.json", v => { (v.payload as Record<string, unknown>).frozen_selection_created = true; }))).rejects.toThrow("abort phase");
    await expect(importJointOutput(await mutateJson(files, "aborted/aborted.json", v => {
      const p = v.payload as Record<string, unknown>, last = p.last_attempt as Record<string, unknown>;
      (last.identity as Record<string, unknown>).source_inventory_sha256 = "0".repeat(64);
    }))).rejects.toThrow("attempt/source inventory binding");
    await expect(importJointOutput(await mutateJson(files, "aborted/aborted.json", v => {
      ((v.payload as Record<string, unknown>).source_inventory as Record<string, unknown>).CrossGradient = "0".repeat(64);
    }))).rejects.toThrow("inventory declaration digest binding");
  });
  it.skipIf(!durableAbort)("does not promote actual durable freeze after late workflow failure", async () => {
    const files = actualJointFiles(durableAbort!), result = await importJointOutput(files);
    expect(result.outcome).toBe("failed"); expect(result.files.has("frozen/q.npy")).toBe(true);
    expect(result.candidates).toHaveLength(26); expect(result.aborted!.payload.frozen_selection_created).toBe(true);
    expect(result.result).toBeNull(); expect(result.model).toBeNull(); expect(result.frozen).toBeNull();
    await expect(importJointOutput(await mutateJson(files, "aborted/aborted.json", v => { (v.payload as Record<string, unknown>).plan_sha256 = "0".repeat(64); }))).rejects.toThrow("retained failure identity binding");
  });
  it.skipIf(!matrix)("imports every actual24-case output without excluding failures", async () => {
    let actualAttempts = 0, nonconverged = 0;
    for (let i = 0; i < 24; i++) { const r = await importJointOutput(actualJointFiles(join(matrix!, `joint-control-${String(i).padStart(2, "0")}`, "output")));
      actualAttempts += r.candidates.length; nonconverged += r.candidates.filter(c => c.status === "nonconverged").length; }
    expect(actualAttempts).toBe(624); expect(nonconverged).toBeGreaterThan(0);
  }, 30_000);
  it.skipIf(!maximum)("admits actual maximum-count resource output without recovery claim", async () => {
    const r = await importJointOutput(actualJointFiles(maximum!)); expect(r.model!.arrays.density_kg_m3.shape).toEqual([1932]);
    expect(r.model!.arrays.density_kg_m3.values.every(v => v === 0)).toBe(true);
    expect(r.limitations.scientific_acceptance_verified).toBe(false);
  }, 30_000);
});
