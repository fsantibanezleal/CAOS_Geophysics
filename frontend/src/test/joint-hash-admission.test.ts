import { describe, expect, it, vi } from "vitest";
import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { createHash } from "node:crypto";
import { importJointOutput, jointSha, type JointFile } from "../api/joint-result";

const encode = (v: unknown) => new TextEncoder().encode(JSON.stringify(v));
const digest = (bytes: Uint8Array) => createHash("sha256").update(bytes).digest("hex");
function originals(variable = "GEOPHYSICS_JOINT_OUTPUT_FIXTURE"): JointFile[] {
  const root = process.env[variable]; if (!root) throw new Error(`Explicit external ${variable} required; no skipped hash gate`);
  const files: JointFile[] = [];
  function visit(dir: string) { for (const name of readdirSync(dir)) { const path = join(dir, name), info = statSync(path);
    if (info.isDirectory()) visit(path); else files.push({ path: relative(root!, path).replaceAll("\\", "/"), size: info.size, read: async () => new Uint8Array(readFileSync(path)) }); } }
  visit(root); return files;
}
function observe(files: JointFile[], controller?: AbortController, rejectFirst = false) {
  const npys = files.filter(f => f.path.endsWith(".npy")).length;
  let reads = 0, active = 0, peak = 0, calls = 0, large = 0;
  const original = crypto.subtle.digest.bind(crypto.subtle);
  const spy = vi.spyOn(crypto.subtle, "digest").mockImplementation(async (algorithm, bytes) => {
    expect(reads).toBe(npys); const size = bytes.byteLength;
    if (size > 262144) { expect(active).toBe(0); large++; } else expect(active).toBeLessThan(4);
    active++; peak = Math.max(peak, active); const call = ++calls;
    // Native snapshot occurs immediately, before the artificial scheduling delay.
    const pending = original(algorithm, bytes);
    try { await Promise.resolve(); const result = await pending;
      if (call === 1) { controller?.abort(); if (rejectFirst) throw new Error("injected digest rejection"); }
      return result;
    } finally { active--; }
  });
  return { files: files.map(f => ({ ...f, read: async () => { const bytes = await f.read(); if (f.path.endsWith(".npy")) reads++; return bytes; } })),
    state: () => ({ active, peak, calls, large }), restore: () => spy.mockRestore() };
}
// Adverse transport only: inflated zero trace is NEVER accepted as real science.
// Valid native headers let the large-file path reach its original digest refusal.
async function largeAdverseFiles() {
  const files = originals("GEOPHYSICS_JOINT_MAX_OUTPUT_FIXTURE"), buffers = new Map<string, Uint8Array>();
  const manifestFile = files.find(f => f.path === "calibration/calibration.json")!;
  const doc = JSON.parse(new TextDecoder().decode(await manifestFile.read()));
  const candidate = doc.payload.candidates[0], count = 20, n = candidate.identity.parameter_count;
  candidate.result.iterations = count - 1;
  for (const [key, d] of Object.entries(doc.arrays) as [string, { dtype: string; shape: number[]; file_bytes: number; file_sha256: string; data_sha256: string }][]) {
    if (!key.startsWith("c00_") || key === "c00_q") continue;
    const shape = key.endsWith("models_q") || key.endsWith("physical_trace") ? [count, n] : key.endsWith("terms_trace") ? [count, 5]
      : [candidate.result.trace[key.slice(4)] && ["phi_d", "phi_m", "phi_engine", "kkt_normalized"].includes(key.slice(4)) ? count : count - 1];
    const bytes = new Uint8Array(128 + shape.reduce((a, b) => a * b, 1) * (d.dtype === "|b1" ? 1 : 8));
    bytes.set([147, 78, 85, 77, 80, 89, 1, 0, 118, 0]);
    const header = `{'descr': '${d.dtype}', 'fortran_order': False, 'shape': (${shape.join(", ")}${shape.length === 1 ? "," : ""}), }`;
    bytes.set(new TextEncoder().encode(header.padEnd(117, " ") + "\n"), 10);
    Object.assign(d, { shape, file_bytes: bytes.length, file_sha256: digest(bytes), data_sha256: digest(bytes.subarray(128)) });
    buffers.set(`calibration/${key}.npy`, bytes);
  }
  // Refuse the first inflated model at its original whole-file SHA check.
  doc.arrays.c00_models_q.file_sha256 = "0".repeat(64);
  buffers.set(manifestFile.path, encode(doc));
  const receiptFile = files.find(f => f.path === "workflow.json")!;
  const receipt = JSON.parse(new TextDecoder().decode(await receiptFile.read()));
  receipt.private_export_bytes_before_receipt = files.reduce((sum, f) => sum + (f.path === "workflow.json" ? 0 : buffers.get(f.path)?.length ?? f.size), 0);
  buffers.set(receiptFile.path, encode(receipt));
  return files.map(f => { const bytes = buffers.get(f.path); return bytes ? { path: f.path, size: bytes.length, read: async () => bytes } : f; });
}

describe("bounded original hash scheduling", () => {
  it("snapshots exact subarray bytes before immediate caller mutation", async () => {
    const bytes = new Uint8Array([9, 1, 2, 3, 8]), view = bytes.subarray(1, 4), expected = digest(view);
    const pending = jointSha(view); bytes.fill(0); expect(await pending).toBe(expected);
  });
  it("owns a nonshared snapshot for shared byte inputs", async () => {
    const bytes = new Uint8Array(new SharedArrayBuffer(5)); bytes.set([9, 1, 2, 3, 8]);
    const view = bytes.subarray(1, 4), expected = digest(view), pending = jointSha(view);
    bytes.fill(0); expect(await pending).toBe(expected);
  });
  it("admits every real header before hashing with at most four active small digests", async () => {
    const watcher = observe(originals());
    try { const result = await importJointOutput(watcher.files);
      expect(result.outcome).toBe("completed"); expect(watcher.state()).toMatchObject({ active: 0, peak: 4 });
      expect(watcher.state().calls).toBeGreaterThan(1000); expect(result.limitations.scientific_acceptance_verified).toBe(false);
    } finally { watcher.restore(); }
  });
  it("rejects an adverse late header before any digest", async () => {
    const files = originals(), npys = files.filter(f => f.path.endsWith(".npy")), last = npys.at(-1)!;
    const spy = vi.spyOn(crypto.subtle, "digest");
    try { await expect(importJointOutput(files.map(f => f === last ? { ...f, read: async () => { const bytes = await f.read(); bytes[7] = 1; return bytes; } } : f))).rejects.toThrow("NPY1"); expect(spy).not.toHaveBeenCalled(); }
    finally { spy.mockRestore(); }
  });
  it("drains native small hashes before rejecting cancellation", async () => {
    const controller = new AbortController(), watcher = observe(originals(), controller);
    try { await expect(importJointOutput(watcher.files, controller.signal)).rejects.toThrow("cancelled"); expect(watcher.state()).toMatchObject({ active: 0, calls: 4, peak: 4 }); }
    finally { watcher.restore(); }
  });
  it("drains sibling digests before propagating a digest rejection", async () => {
    const watcher = observe(originals(), undefined, true);
    try { await expect(importJointOutput(watcher.files)).rejects.toThrow("injected digest rejection"); expect(watcher.state().active).toBe(0); expect(watcher.state().peak).toBe(4); expect(watcher.state().calls).toBe(7); }
    finally { watcher.restore(); }
  });
  it("isolates large native hash input and drains before its exact SHA refusal", async () => {
    const watcher = observe(await largeAdverseFiles());
    try { await expect(importJointOutput(watcher.files)).rejects.toThrow("digest mismatch"); expect(watcher.state()).toMatchObject({ active: 0, large: 1 }); }
    finally { watcher.restore(); }
  });
  it("bounds asynchronous real header reads and isolates large reader input", async () => {
    let active = 0, peak = 0, large = 0;
    const files = (await largeAdverseFiles()).map(f => ({ ...f, read: async () => {
      if (f.path.endsWith(".json")) return f.read();
      if (f.size > 262144) { expect(active).toBe(0); large++; } else expect(active).toBeLessThan(4);
      active++; peak = Math.max(peak, active);
      try { await Promise.resolve(); return await f.read(); } finally { active--; }
    } }));
    await expect(importJointOutput(files)).rejects.toThrow("digest mismatch");
    expect(active).toBe(0); expect(peak).toBe(4); expect(large).toBe(2);
  });
  it("drains original readers before rejecting a late header error", async () => {
    const original = originals(), last = original.filter(f => f.path.endsWith(".npy")).at(-1)!;
    let active = 0;
    const spy = vi.spyOn(crypto.subtle, "digest");
    try { const files = original.map(f => ({ ...f, read: async () => {
      active++; try { await Promise.resolve(); const bytes = await f.read(); if (f === last) bytes[7] = 1; return bytes; } finally { active--; }
    } }));
      await expect(importJointOutput(files)).rejects.toThrow("NPY1"); expect(active).toBe(0); expect(spy).not.toHaveBeenCalled();
    } finally { spy.mockRestore(); }
  });
  it("drains original reader siblings before propagating reader rejection", async () => {
    const original = originals(), first = original.filter(f => f.path.endsWith(".npy"))[0]; let active = 0;
    const spy = vi.spyOn(crypto.subtle, "digest");
    try { const files = original.map(f => ({ ...f, read: async () => {
      active++; try { await Promise.resolve(); if (f === first) throw new Error("injected reader rejection"); return await f.read(); } finally { active--; }
    } }));
      await expect(importJointOutput(files)).rejects.toThrow("injected reader rejection"); expect(active).toBe(0); expect(spy).not.toHaveBeenCalled();
    } finally { spy.mockRestore(); }
  });
});
