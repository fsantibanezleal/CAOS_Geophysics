import { describe, expect, it } from "vitest";
import { readFileSync, existsSync } from "node:fs";
import { createHash } from "node:crypto";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { calibrationSeries, ediInterval, ediPath, validateEdiFieldScreen, validateEdiRun, type EdiBundle, type EdiCalibration, type EdiFieldScreen, type EdiFieldScreenEntry, type EdiRun } from "../edi";
import { EdiCalibrationResult, EdiFieldScreenResult, EdiResult } from "../components/EdiFixtures";
import { mtForward } from "../mt";
import { intervalPath } from "../recovery";

// Canonical post-promotion bundle in CI; independently generated bundle during integration.
const canonical = new URL("../../../data/derived/v2/edi/manifest.json", import.meta.url);
const manifestPath = existsSync(canonical) ? canonical : new URL("../../../data/experiments/edi/manifest.json", import.meta.url);
const read = <T,>(filename: string): T => JSON.parse(readFileSync(new URL(filename, manifestPath), "utf8"));
const bundle = read<EdiBundle>("manifest.json");

describe("actual EDI fixture and calibration contracts", () => {
  it("keeps measured screening separate from any inverse solution", () => {
    const fixtureRun = read<EdiRun>(bundle.fixtures[0].artifact);
    const entry: EdiFieldScreenEntry = { id: "cl061", artifact: "test-screen.json", artifact_sha256: "artifact-digest", source_sha256: "source-digest", source_release: { citation: "Source citation from exporter", station_url: "https://www.usgs.gov/example", release_doi: "10.1234/release", transfer_function_doi: "10.1234/transfer", rights: "Public test fixture", note: "No geological inference" } };
    const curve = { real: [1, 2], imag: [2, 3], apparent: [100, 200], phase: [30, 40], sigma_real_imag_ohm: [0.1, 0.2] };
    const screen: EdiFieldScreen = {
      schema: "inverse-earth/edi-screen/v1", id: entry.id, family: "mt", source_kind: "measured EDI transfer functions",
      truth: null, methods: {}, inversion_performed: false, one_d_fit_performed: false, one_d_inversion_eligible: false,
      interpretation: "Necessary tensor screen", frequencies_hz: [1, 10], observed: { xy: curve, yx: { ...curve, phase: [130, 140] } },
      compatibility: { passes_screen: false, threshold: 3, xx_component_wrms: 320.23, yy_component_wrms: 109.51, antisymmetry_conservative_wrms: 267.60 },
      provenance: { ...fixtureRun.provenance, source_sha256: entry.source_sha256, synthetic: false, target_known: false },
    };
    expect(() => validateEdiFieldScreen(screen, entry)).not.toThrow();
    const html = renderToStaticMarkup(createElement(EdiFieldScreenResult, { screen, entry }));
    for (const text of ["1D screen rejected", "No 1D inversion was performed", "Zxx", "Zyy", "267.6", "Source citation from exporter", "USGS station record", "EarthScope release DOI", "Transfer-function DOI", "sign-corrected", "full tensor without this YX sign flip", "source-digest", "artifact-digest"]) expect(html).toContain(text);
    expect(html).toContain('href="https://doi.org/10.1234/release"');
    expect(html).toContain('href="https://doi.org/10.1234/transfer"');
    for (const text of ["Final-model prediction", "Selected final model", "Independent synthetic fixture oracle", "Layer resistivity and empirical interval"]) expect(html).not.toContain(text);
    expect(() => validateEdiFieldScreen({ ...screen, methods: { fabricated: {} } } as unknown as EdiFieldScreen, entry)).toThrow();
    expect(() => validateEdiFieldScreen({ ...screen, truth: [1] } as unknown as EdiFieldScreen, entry)).toThrow();
    expect(() => validateEdiFieldScreen({ ...screen, one_d_inversion_eligible: true }, entry)).toThrow();
    expect(() => validateEdiFieldScreen({ ...screen, observed: { ...screen.observed, xy: { ...curve, sigma_real_imag_ohm: [0, 0] } } }, entry)).toThrow();
  });
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
