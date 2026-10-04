import { describe, expect, it, vi } from "vitest";
import actual from "./fixtures/mt-actual.json";
import { fixture } from "./fixtures/processing";
import { parseMtResult } from "../api/mt-contracts";
import { gravityInspection, mtInspection, mtReadout, recordedMtState, readSavedResult } from "../components/result-view-data";

describe("server result inspection, not computation", () => {
  it("checks ZIP size and success before any byte read", async () => {
    const f = fixture(), read = vi.fn(() => Promise.resolve(new ArrayBuffer(0)));
    for (const size of [0, 21, 17 * 1048576 + 1, NaN, Infinity, 22.5]) {
      await expect(readSavedResult({ size, arrayBuffer: read } as unknown as Blob,
        { kind: "gravity", job: f.job, dataset: f.dataset })).rejects.toThrow();
    }
    await expect(readSavedResult({ size: 22, arrayBuffer: read } as unknown as Blob,
      { kind: "gravity", job: { ...f.job, state: "cancelled" }, dataset: f.dataset })).rejects.toThrow();
    expect(read).not.toHaveBeenCalled();
  });
  it("opens only original verified members bound to selected dataset/job", async () => {
    const f = fixture();
    expect(await readSavedResult(f.bundle(), { kind: "gravity", job: f.job, dataset: f.dataset })).toEqual(f.result);
    await expect(readSavedResult(f.bundle(), { kind: "gravity", job: { ...f.job, job_id: "00000000-0000-4000-8000-000000000009" }, dataset: f.dataset })).rejects.toThrow();
    await expect(readSavedResult(f.bundle({ "result.json": new TextEncoder().encode(JSON.stringify({ ...f.result, engine_sha256: "d".repeat(64) })) }),
      { kind: "gravity", job: f.job, dataset: f.dataset })).rejects.toThrow();
  });
  it("exports exact gravity observations, uncertainty, masks and null unavailable science", () => {
    const f = fixture(), before = JSON.stringify(f);
    const snapshot = JSON.parse(JSON.stringify(gravityInspection(f.dataset, f.result, 4)));
    expect(snapshot.selected.index).toBe(4);
    expect(snapshot.dataset).toEqual(f.dataset);
    expect(snapshot.result).toEqual(f.result);
    expect(snapshot.prediction).toBeNull(); expect(snapshot.residual).toBeNull(); expect(snapshot.model).toBeNull();
    expect(snapshot.units).toEqual({ position: "m", observation: "mGal", uncertainty: "mGal", robust_score: "1" });
    expect(gravityInspection(f.dataset, null, 0).result).toBeNull();
    expect(JSON.stringify(f)).toBe(before);
  });
  it("links exact XY and sign-corrected -YX values without masks or rounding", () => {
    const r = parseMtResult(structuredClone(actual.m06)), before = JSON.stringify(r);
    const values = mtReadout(r, 4), m = r.inverse!.methods["mt-lm"];
    expect(values.partition).toBe("heldout"); expect(values.frequency_hz).toBe(r.frequency_hz[4]);
    for (const c of ["xy", "yx"] as const) {
      const row = values.components[c], obs = r.screen.observed[c];
      expect(row.observed).toEqual({ real: obs.real[4], imag: obs.imag[4], apparent: obs.apparent[4], phase: obs.phase[4] });
      expect(row.predicted).toEqual({ real: m.predicted.real[4], imag: m.predicted.imag[4], apparent: m.predicted.apparent[4], phase: m.predicted.phase[4] });
      expect(row.residual!.real).toBe(obs.real[4] - m.predicted.real[4]);
      expect(row.standardized_residual!.imag).toBe((obs.imag[4] - m.predicted.imag[4]) / obs.sigma_real_imag_ohm[4]);
    }
    expect(JSON.parse(JSON.stringify(mtInspection(r, 4))).result).toEqual(r);
    expect(JSON.stringify(r)).toBe(before);
  });
  it("keeps M05 inverse fields null even after exporting selected values", () => {
    const r = parseMtResult(structuredClone(actual.m05)), read = mtReadout(r, 0);
    expect(read.partition).toBe("qc-only");
    for (const c of ["xy", "yx"] as const) {
      expect(read.components[c].predicted).toBeNull(); expect(read.components[c].residual).toBeNull();
      expect(read.components[c].standardized_residual).toBeNull();
    }
    expect(mtInspection(r, 0).result.inverse).toBeNull();
    expect(() => recordedMtState(r, 0)).toThrow();
  });
  it("exports literal recorded evaluations, no historical predicted curves", () => {
    const r = parseMtResult(structuredClone(actual.m06)), m = r.inverse!.methods["mt-lm"];
    const index = m.frames.length - 1, state = JSON.parse(JSON.stringify(recordedMtState(r, index)));
    expect(state.model_ohm_m).toEqual(m.frames[index]); expect(state.state).toEqual(m.states[index]);
    expect(state.objective).toBe(m.history[index]); expect(state.historical_prediction).toBeNull();
    expect(state.thickness_m).toEqual(r.inverse!.thickness);
    expect(state.evaluation_kind).toBe("residual-evaluation-record");
  });
  it.each([-1, .5, NaN, Infinity, 999999])("rejects invalid selection %s rather than clamping or fabricating", index => {
    const f = fixture(), r = parseMtResult(structuredClone(actual.m06));
    expect(() => gravityInspection(f.dataset, f.result, index)).toThrow();
    expect(() => mtReadout(r, index)).toThrow(); expect(() => recordedMtState(r, index)).toThrow();
  });
});
