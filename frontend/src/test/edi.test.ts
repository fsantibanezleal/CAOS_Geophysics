import { describe, expect, it } from "vitest";
import { readFileSync, existsSync } from "node:fs";
import { createHash } from "node:crypto";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { calibrationSeries, ediInterval, ediPath, validateEdiRun, type EdiBundle, type EdiCalibration, type EdiRun } from "../edi";
import { EdiCalibrationResult, EdiResult } from "../components/EdiFixtures";
import { mtForward } from "../mt";
import { intervalPath } from "../recovery";

// Canonical post-promotion bundle in CI; independently generated bundle during integration.
const canonical = new URL("../../../data/derived/v2/edi/manifest.json", import.meta.url);
const manifestPath = existsSync(canonical) ? canonical : new URL("../../../data/experiments/edi/manifest.json", import.meta.url);
const read = <T,>(filename: string): T => JSON.parse(readFileSync(new URL(filename, manifestPath), "utf8"));
const bundle = read<EdiBundle>("manifest.json");

describe("actual EDI fixture and calibration contracts", () => {
  it("only fetches adjacent exporter-owned files", () => {
    expect(ediPath("halfspace-100-native.edi")).toBe("edi/halfspace-100-native.edi");
    for (const path of ["../private.json", "https://example.com/a.json", "/a.json", "sub/a.json", "a.html"]) expect(() => ediPath(path)).toThrow();
  });
  it("keeps all three generic inversion targets unknown and verifies final-prediction parity", () => {
    expect(bundle.fixtures).toHaveLength(3);
    for (const fixture of bundle.fixtures) {
      const run = read<EdiRun>(fixture.artifact);
      for (const [filename, digest] of [[fixture.source, fixture.source_sha256], [fixture.artifact, fixture.artifact_sha256]]) expect(createHash("sha256").update(readFileSync(new URL(filename, manifestPath))).digest("hex")).toBe(digest);
      expect(() => validateEdiRun(run, fixture)).not.toThrow();
      expect(run.truth).toBeNull();
      expect(run.provenance.target_known).toBe(false);
      for (const method of Object.values(run.methods)) {
        const actual = mtForward(method.model, run.thickness, run.frequencies);
        actual.apparent.forEach((v, i) => expect(Math.abs(v / method.predicted.apparent[i] - 1)).toBeLessThan(2e-6));
        actual.phase.forEach((v, i) => expect(Math.abs(v - method.predicted.phase[i])).toBeLessThan(2e-5));
        expect(ediInterval(method.uncertainty)?.lower).toHaveLength(method.model.length);
        expect(method.evaluation?.status).toBe("unresolved");
      }
    }
  });
  it("rejects mismatched identity, missing methods, nonpositive errors and malformed initialization", () => {
    const fixture = bundle.fixtures[0], run = read<EdiRun>(fixture.artifact);
    expect(() => validateEdiRun({ ...run, methods: {} }, fixture)).toThrow();
    expect(() => validateEdiRun({ ...run, sigma: run.sigma.map(() => 0) }, fixture)).toThrow();
    expect(() => validateEdiRun(run, { ...fixture, source_sha256: "wrong" })).toThrow();
    const corrupt = structuredClone(run); corrupt.methods["mt-lm"].solver.initial_model[0] = NaN;
    expect(() => validateEdiRun(corrupt, fixture)).toThrow();
  });
  it("renders real observations, baselines, separate fixture oracle, source downloads and conditional bands", () => {
    const fixture = bundle.fixtures[2], run = read<EdiRun>(fixture.artifact);
    const html = renderToStaticMarkup(createElement(EdiResult, { run, fixture }));
    for (const text of ["Parsed EDI observations", "Final-model prediction", "Independent starting-model response", "Independent synthetic fixture oracle", "truth = null", "not a geological posterior", "Parsed tensor and 1D compatibility", fixture.source, fixture.artifact, fixture.source_sha256]) expect(html).toContain(text);
    expect(html).not.toMatch(/type="file"|upload.*input|NaN/);
  });
  it("plots actual independent calibration intervals and preserves failed intervals as gaps", () => {
    expect(bundle.calibration).toHaveLength(2);
    for (const entry of bundle.calibration) {
      const data = read<EdiCalibration>(entry.artifact);
      expect(data.coverage_per_layer).toEqual(entry.coverage_per_layer);
      expect(calibrationSeries(data, 0).x).toHaveLength(data.realizations);
      const html = renderToStaticMarkup(createElement(EdiCalibrationResult, { data }));
      expect(html).toContain("Wilson 95% limits");
      expect(html).toContain("not geological resistivity uncertainty");
      expect(html).not.toContain("NaN");
      const failed = { ...data, rows: [{ realization: 0, error: "nonconvergence" }] };
      expect(calibrationSeries(failed, 0).lower[0]).toBeNaN();
    }
    const path = intervalPath([1, 2, 3], [1, NaN, 2], [2, NaN, 3], x => x, y => y);
    expect(path).toBe("M1,1 L1,2 Z M3,2 L3,3 Z");
  });
});
