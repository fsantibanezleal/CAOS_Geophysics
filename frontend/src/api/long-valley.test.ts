import { readFileSync } from "node:fs";
import { describe, expect, it } from "vitest";
import { differenceEpochs, parseLongValleyCase } from "./long-valley";

const artifact = JSON.parse(readFileSync(new URL("../../../data/derived/field/long-valley/1982-06_to_1999-07.json", import.meta.url), "utf8"));

describe("Long Valley source-bound time-lapse", () => {
  it("parses the committed field artifact and computes all 37 paired stations", () => {
    const data = parseLongValleyCase(artifact);
    const rows = differenceEpochs(data, "1982-06", "1999-07");
    expect(rows).toHaveLength(37);
    expect(rows.find((r) => r.station_id === "12DOR75")).toMatchObject({
      earlier_gravity_mgal: 979242.333,
      later_gravity_mgal: 979242.215,
      delta_gravity_mgal: expect.closeTo(-0.118, 8),
      earlier_sigma_mgal: 0.005,
      later_sigma_mgal: 0.012,
      delta_sigma_independent_mgal: expect.closeTo(Math.hypot(0.005, 0.012), 10),
    });
  });

  it("refuses inconsistent count, duplicate stations, and non-finite measurements", () => {
    expect(() => parseLongValleyCase({ ...artifact, station_count: 36 })).toThrow("count is inconsistent");
    const duplicate = structuredClone(artifact);
    duplicate.stations[1].station_id = duplicate.stations[0].station_id;
    expect(() => parseLongValleyCase(duplicate)).toThrow("identity or geometry is invalid");
    const nonfinite = structuredClone(artifact);
    nonfinite.stations[0].measurements[0].gravity_mgal = Number.NaN;
    expect(() => parseLongValleyCase(nonfinite)).toThrow("measurement is invalid");
  });

  it("refuses a stale precomputed epoch-difference table", () => {
    const stale = structuredClone(artifact);
    stale.difference.stations[0].delta_gravity_mgal += 0.01;
    expect(() => parseLongValleyCase(stale)).toThrow("do not replay from the occupation arrays");
  });

  it("refuses equal or unknown epochs and leaves unsupported cross-epoch covariance explicit", () => {
    const data = parseLongValleyCase(artifact);
    expect(() => differenceEpochs(data, "1982-06", "1982-06")).toThrow("two distinct occupations");
    expect(() => differenceEpochs(data, "1900-01", "1999-07")).toThrow("two distinct occupations");
    expect(data.difference.uncertainty_model).toContain("covariance unavailable");
  });

  it("preserves but excludes the exact unresolved source-QC observation unless requested", () => {
    const data = parseLongValleyCase(artifact);
    const raw = data.stations.find((s) => s.station_id === "1JD1952")!.measurements.find((m) => m.epoch === "1982-09")!;
    expect(raw).toMatchObject({ gravity_mgal: 979255.21, qc: { status: "suspect" } });
    expect(differenceEpochs(data, "1982-09", "1999-07")).toHaveLength(23);
    expect(differenceEpochs(data, "1982-09", "1999-07", true)).toHaveLength(24);
    expect(differenceEpochs(data, "1982-09", "1999-07", true).find((r) => r.station_id === "1JD1952")?.delta_gravity_mgal).toBeCloseTo(24.605, 3);
    const invalid = structuredClone(artifact);
    invalid.stations.find((s: { station_id: string }) => s.station_id === "1JD1952").measurements.find((m: { epoch: string }) => m.epoch === "1982-09").qc.status = "corrected";
    expect(() => parseLongValleyCase(invalid)).toThrow("quality flag is invalid");
  });
});
