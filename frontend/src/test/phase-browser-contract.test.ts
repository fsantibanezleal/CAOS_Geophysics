import { describe, expect, it } from "vitest";
import {
  normalizeCounts, parseLocalTrace, parseNormalizedF32, parsePhaseBenchmark, parsePhaseManifest,
  validateProbabilities, PHASE_SAMPLES,
} from "../phase-picker";

const hash = "a".repeat(64);
const channel = (base: number, swing: number) => Array.from({ length: PHASE_SAMPLES }, (_, i) => base + (i % 2 ? swing : -swing));
const local = () => ({
  schema: "caos.phase-browser-trace.v1", trace_id: "local-example", source: "user-supplied counts",
  sample_rate_hz: 100, component_order: ["E", "N", "Z"], representation: "counts", unit: "counts",
  qc: { components_measured: true, gaps: false, clipped: false, response_corrected: false },
  channels: { E: channel(100, 2), N: channel(200, 3), Z: channel(-40, 5) },
});
const manifest = () => ({
  schema: "caos.phase-browser-assets.v1", status: "assets-exported-browser-parity-not-yet-verified",
  browser_parity_verified: false,
  input: { sample_rate_hz: 100, samples: 6000, component_order: ["E", "N", "Z"], shape: [1,3,6000],
    file_dtype: "float32-little-endian", file_layout: "component-major; 6000 consecutive samples per component",
    unit: "dimensionless normalized instrument counts" },
  output: { shape: [1,3,6000], classes: ["N","P","S"] },
  model: { file: "model.onnx", bytes: 5739696, sha256: hash, checkpoint_sha256: hash,
    thresholds: { P: 0.8, S: 0.8 } },
  benchmark: { file: "benchmark.json", sha256: hash, selected: 6000, qc_valid: 5926,
    tolerance_s: 0.5, reference: "STEAD manual P/S picks, not geological truth" },
  selection: { selected: 24, qc_valid: 23, qc_rejected: 1, full_benchmark_selected: 6000,
    selected_before_heldout_scoring: true },
  source: { dataset: "STEAD", citation: "Stanford Earthquake Dataset", authors: "Mousavi et al.",
    doi: "10.1109/ACCESS.2019.2947848", license: "CC BY 4.0", license_url: "https://example.org/license",
    original_url: "https://example.org/source", mirror_url: "https://example.org/mirror", modification: "ENZ normalized" },
  records: Array.from({ length: 24 }, (_, i) => i === 19 ? {
    trace_id: `trace-${i}`, status: "qc-rejected", category: "noise", network: "AV", station_id: "AV.ANNE",
    channel: "EH", analyst_p_s: null, analyst_s_s: null, reference_is_ground_truth: false,
    qc_reason: "flat component",
  } : {
    trace_id: `trace-${i}`, status: "qc-valid", category: i >= 16 ? "noise" : "earthquake_local",
    network: "PB", station_id: "PB.B917", channel: "EH", analyst_p_s: i >= 16 ? null : 7,
    analyst_s_s: i >= 16 ? null : 12.7, reference_is_ground_truth: false,
    waveform_file: `trace-${String(i).padStart(2,"0")}.f32`, waveform_sha256: hash, waveform_bytes: 72000,
  }),
});

describe("M13 browser input and frozen asset boundary", () => {
  it("matches raw-count float32 centering and does not normalize curated input twice", () => {
    const parsed = parseLocalTrace(local());
    expect(parsed.input.length).toBe(18000);
    expect([...parsed.input.slice(0, 4)]).toEqual([-1,1,-1,1]);
    expect([...parsed.input.slice(6000, 6004)]).toEqual([-1,1,-1,1]);
    expect([...parsed.channels[0].slice(0, 4)]).toEqual([-1,1,-1,1]);
    expect(parsed.channels[0][0]).toBe(parsed.input[0]);
    expect(normalizeCounts([channel(100, 2), channel(200, 3), channel(-40, 5)])[2][0]).toBe(-1);
    const normalized = local();
    normalized.representation = "normalized"; normalized.unit = "dimensionless";
    normalized.channels = {
      E: channel(0, 1),
      N: Array.from({ length: 6000 }, (_, i) => i % 3 ? 1 : -1),
      Z: Array.from({ length: 6000 }, (_, i) => i % 4 ? 1 : -1),
    };
    expect(() => parseLocalTrace(normalized)).not.toThrow();
    expect(parseLocalTrace(normalized).input[0]).toBe(-1);
  });

  it("rejects unsupported rate, component ambiguity, gaps and filled/flat channels", () => {
    const wrongRate = local(); wrongRate.sample_rate_hz = 50;
    expect(() => parseLocalTrace(wrongRate)).toThrow(/100 Hz/);
    const gaps = local(); gaps.qc.gaps = true;
    expect(() => parseLocalTrace(gaps)).toThrow(/Unsupported channel QC/);
    const duplicated = local(); duplicated.channels.N = duplicated.channels.E.slice();
    expect(() => parseLocalTrace(duplicated)).toThrow(/duplicates/);
    const duplicateAtFloat32 = local(); duplicateAtFloat32.channels.N = duplicateAtFloat32.channels.E.map(value => value + 1e-8);
    expect(() => parseLocalTrace(duplicateAtFloat32)).toThrow(/duplicates/);
    const flat = local(); flat.channels.Z.fill(0);
    expect(() => parseLocalTrace(flat)).toThrow(/flat/);
    const flatAtFloat32 = local(); flatAtFloat32.channels.Z = flatAtFloat32.channels.Z.map((_, i) => 1 + (i % 2 ? 1e-9 : 0));
    expect(() => parseLocalTrace(flatAtFloat32)).toThrow(/flat/);
  });

  it("accepts schema-accurate 23/1 manifest and forbids QC waveform substitution", () => {
    const parsed = parsePhaseManifest(manifest());
    expect(parsed.records).toHaveLength(24);
    expect(parsed.records[19].status).toBe("qc-rejected");
    const changed = manifest();
    changed.records[19].waveform_file = "replacement.f32";
    expect(() => parsePhaseManifest(changed)).toThrow(/QC-failed/);
  });

  it("checks the sealed benchmark population and checkpoint before showing offline metrics", () => {
    const published = parsePhaseManifest(manifest());
    const metric = () => ({ f1_at_0p5s: 0.8, correct_within_0p5s: 4000,
      reference_count: 5000, timing_absolute_median_s: 0.08, valid_noise_false_pick_rate: 0.01 });
    const benchmark = {
      schema: "caos.stead-phase-heldout-benchmark.v1", checkpoint_sha256: hash,
      selected: 6000, valid: 5926, qc_rejected: 74, tolerance_s: 0.5,
      reference: "STEAD manual P/S picks, not geological truth", metrics_include_qc_failures_as_unpicked: true,
      metrics: { nominal: { M08: { P: metric(), S: metric() }, M13: { P: metric(), S: metric() } } },
    };
    expect(parsePhaseBenchmark(benchmark, published).nominal.M13.P.f1_at_0p5s).toBe(0.8);
    benchmark.valid = 5927;
    expect(() => parsePhaseBenchmark(benchmark, published)).toThrow(/denominator/);
  });

  it("reads little-endian channel-major float32 without a second transform", () => {
    const bytes = new ArrayBuffer(72000);
    const view = new DataView(bytes);
    for (let c = 0; c < 3; c++) for (let i = 0; i < 6000; i++)
      view.setFloat32((c * 6000 + i) * 4, i % (c + 2) ? 1 : -1, true);
    const trace = parseNormalizedF32(bytes, parsePhaseManifest(manifest()).records[0]);
    expect(trace.input[0]).toBe(-1);
    expect(trace.input[6001]).toBe(1);
    expect(trace.representation).toBe("normalized");
    expect(() => parseNormalizedF32(bytes, parsePhaseManifest(manifest()).records[19])).toThrow(/QC-failed/);
  });

  it("validates all raw output samples before global peaks and S abstention", () => {
    const values = new Float32Array(18000);
    for (let i = 0; i < 6000; i++) values[i] = 1;
    values[100] = 0.1; values[6100] = 0.9;
    values[139] = 0.1; values[12139] = 0.9;
    const near = validateProbabilities(values, [1,3,6000]);
    expect(near.picks).toEqual({ P: 100, S: null });
    expect(near.reasons.S).toBe("ps-separation");
    values[139] = 1; values[12139] = 0;
    values[140] = 0.1; values[12140] = 0.9;
    expect(validateProbabilities(values, [1,3,6000]).picks).toEqual({ P: 100, S: 140 });
    values[400] = Number.NaN;
    expect(() => validateProbabilities(values, [1,3,6000])).toThrow(/Invalid N\/P\/S/);
  });
});
