import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { parseAmargosaResult, type AmargosaResult } from "./amargosa";
import { parseAmargosaBytes } from "./amargosa";
import fieldIndex from "../data/field-study-index.json";

const raw = readFileSync(new URL("../../../data/derived/field/amargosa/amargosa-m03-20261111.json", import.meta.url));
const source = JSON.parse(raw.toString("utf8")) as unknown;
const bytes = Uint8Array.from(raw).buffer as ArrayBuffer;
const pin = fieldIndex.artifacts.find((artifact) => artifact.path === "amargosa/amargosa-m03-20261111.json")!;

describe("source-bound Amargosa M03 result", () => {
  it("accepts the measured artifact and keeps unsupported cells masked", () => {
    const result = parseAmargosaResult(source);
    expect(result.source_selection.track_count).toEqual({ flight: 12, tie: 4 });
    expect(result.heldout_interpolation.rmse).toBeCloseTo(25.7216516005, 8);
    expect(result.claims.inverse_model).toBe(false);
    expect(result.grid.support_mask.flat().filter(Boolean)).toHaveLength(2101);
  });

  it("verifies the committed field-index digest before parsing bytes", async () => {
    const parsed = await parseAmargosaBytes(bytes, pin.sha256);
    expect(parsed.source.sha256).toBe("2698b48a79822f28122f7f8bcd49d0d28c3c103340ddc0012fee0228866ec22c");
    const altered = Uint8Array.from(raw);
    altered[altered.length - 2] ^= 1;
    await expect(parseAmargosaBytes(altered.buffer, pin.sha256)).rejects.toThrow("differ from the reviewed field-study index");
  });

  it.each([
    (result: AmargosaResult) => { result.claims.inverse_model = true; },
    (result: AmargosaResult) => { result.source_acquisition_receipt.sha256 = "0".repeat(64); },
    (result: AmargosaResult) => { result.grid.values[0][0] = Number.NaN; },
    (result: AmargosaResult) => { result.source_selection.track_count.flight++; },
  ])("rejects a broken evidence contract", (damage) => {
    const candidate = structuredClone(source) as AmargosaResult;
    damage(candidate);
    expect(() => parseAmargosaResult(candidate)).toThrow();
  });
});
