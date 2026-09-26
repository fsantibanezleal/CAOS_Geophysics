import { type Curves, type Method, type Uncertainty } from "./science";

export type EdiFixture = {
  id: string; label: string; synthetic: true;
  target: { quantity: string; units: string; dimensionality: string; provenance: string };
  truth_ohm_m: number[]; thickness_m: number[];
  source: string; source_sha256: string; artifact: string; artifact_sha256: string;
  noise_added: boolean; noise_seed: number; input_units: string; rotation_deg: number;
  sign_convention: string; selected_component: string;
};
export type EdiBundle = {
  schema: "inverse-earth/edi-bundle/v1";
  fixtures: EdiFixture[]; license: string; parser_dependency: string;
  calibration: { id: string; artifact: string; artifact_sha256: string; synthetic: boolean; realizations: number; coverage_per_layer: number[]; failures: number; seed: number }[];
};
export type EdiBootstrap = {
  kind: string; confidence: number; interval_method: string;
  conditioning_model: number[]; fixed_thickness_m: number[]; bounds_ohm_m: number[];
  initial_model: number[]; beta: number; sampling_law: string;
  seed: number; requested: number; completed: number;
  samples: number[][]; interval_ohm_m: [number[], number[]] | null;
  status: string; failures: { seed: number; error: string }[];
};
export type EdiMethod = Omit<Method, "model" | "predicted" | "residual" | "uncertainty"> & {
  model: number[]; predicted: Curves; residual: Curves;
  solver: { initial_model: number[]; bounds_ohm_m: number[]; beta: number; algorithm: string };
  uncertainty?: EdiBootstrap | Uncertainty;
};
export type EdiRun = {
  schema: "inverse-earth/edi-1d/v1"; id: string; family: "mt";
  component: string; units: string; data_units: string;
  frequencies: number[]; thickness: number[]; observed: Curves; sigma: number[];
  methods: Record<string, EdiMethod>; truth: null; clean: null;
  tensor?: { real: number[][][]; imag: number[][][]; sigma: number[][][]; rotation_deg: number[] };
  compatibility: { passes_screen: boolean; threshold: number; xx_component_wrms: number; yy_component_wrms: number; antisymmetry_conservative_wrms: number };
  provenance: {
    source_file: string; source_sha256: string; synthetic: boolean; target_known: false;
    original_units: string; output_units: string; units_multiplier_to_ohm: number;
    original_sign_convention: string; output_sign_convention: string;
    variance_convention: string; rotation_action: string;
    original_rotation_deg: number[]; parser: string; parser_version: string;
  };
};

/** Only exporter-owned adjacent filenames can be fetched from the public bundle. */
export function ediPath(filename: string): string {
  if (!/^[\w-]+\.(json|edi)$/i.test(filename)) throw new Error("Invalid EDI bundle filename");
  return "edi/" + filename;
}

export function validateEdiRun(run: EdiRun, fixture: EdiFixture): void {
  if (run.schema !== "inverse-earth/edi-1d/v1" || run.truth !== null || run.provenance.target_known !== false || run.provenance.source_sha256 !== fixture.source_sha256) throw new Error("EDI source identity or unknown-target contract mismatch");
  const n = run.frequencies.length;
  if (!Object.keys(run.methods).length || run.thickness.some(v => !Number.isFinite(v) || v <= 0)) throw new Error("Invalid EDI methods or thickness");
  if (!fixture.synthetic || fixture.truth_ohm_m.length !== fixture.thickness_m.length + 1 || fixture.truth_ohm_m.some(v => !Number.isFinite(v) || v <= 0)) throw new Error("Invalid independent fixture oracle");
  if (!n || run.frequencies.some(v => !Number.isFinite(v) || v <= 0) || run.sigma.length !== n || run.sigma.some(v => !Number.isFinite(v) || v <= 0)) throw new Error("Invalid EDI frequencies or uncertainties");
  for (const curves of [run.observed, ...Object.values(run.methods).map(m => m.predicted)])
    for (const field of [curves.real, curves.imag, curves.apparent, curves.phase])
      if (field.length !== n || field.some(v => !Number.isFinite(v))) throw new Error("Invalid EDI curve dimensions");
  for (const method of Object.values(run.methods)) {
    if (method.model.length !== run.thickness.length + 1 || method.model.some(v => !Number.isFinite(v) || v <= 0) || method.solver.initial_model.length !== method.model.length || method.solver.initial_model.some(v => !Number.isFinite(v) || v <= 0)) throw new Error("Invalid EDI layer model");
  }
  if (!run.compatibility.passes_screen) throw new Error("EDI tensor did not pass the necessary 1D screen");
}

export function ediInterval(uncertainty?: EdiBootstrap | Uncertainty): { lower: number[]; upper: number[]; members: number; requested: number; quantiles: number[]; seed: number; failures: number } | null {
  if (!uncertainty) return null;
  if ("interval_ohm_m" in uncertainty) {
    if (!uncertainty.interval_ohm_m || uncertainty.completed < 2 || uncertainty.completed > uncertainty.requested || !(uncertainty.confidence > 0 && uncertainty.confidence < 1)) return null;
    const [lower, upper] = uncertainty.interval_ohm_m;
    if (!lower.length || lower.length !== upper.length || lower.some((v, i) => !Number.isFinite(v) || !Number.isFinite(upper[i]) || v <= 0 || v > upper[i])) return null;
    return { lower, upper, members: uncertainty.completed, requested: uncertainty.requested, quantiles: [(1 - uncertainty.confidence) / 2, (1 + uncertainty.confidence) / 2], seed: uncertainty.seed, failures: uncertainty.failures.length };
  }
  const lower = uncertainty.lower.flat(), upper = uncertainty.upper.flat();
  if (uncertainty.members < 2 || uncertainty.quantiles.length !== 2 || !(uncertainty.quantiles[0] >= 0 && uncertainty.quantiles[0] < uncertainty.quantiles[1] && uncertainty.quantiles[1] <= 1) || !lower.length || lower.length !== upper.length || lower.some((v, i) => !Number.isFinite(v) || !Number.isFinite(upper[i]) || v <= 0 || v > upper[i])) return null;
  return { lower, upper, members: uncertainty.members, requested: uncertainty.members, quantiles: uncertainty.quantiles, seed: uncertainty.seed, failures: 0 };
}

export type EdiCalibration = {
  kind: "independent_seeded_conditional_bootstrap_coverage";
  seed: number; calibration_model: number[]; confidence: number; realizations: number;
  bootstrap_samples_per_realization: number; failures: number;
  coverage_per_layer: number[]; coverage_monte_carlo_standard_error: number[];
  coverage_wilson95_lower: number[]; coverage_wilson95_upper: number[];
  mean_width_ohm_m: number[]; bias_ohm_m: number[];
  rows: { realization: number; model?: number[]; interval_ohm_m?: [number[], number[]]; covered?: boolean[]; error?: string }[];
};

/** Failed/missing intervals remain gaps, not zero-width successes. */
export function calibrationSeries(data: EdiCalibration, layer: number) {
  return {
    x: data.rows.map(r => r.realization + 1),
    models: data.rows.map(r => r.model?.[layer] ?? NaN),
    lower: data.rows.map(r => r.interval_ohm_m?.[0]?.[layer] ?? NaN),
    upper: data.rows.map(r => r.interval_ohm_m?.[1]?.[layer] ?? NaN),
    oracle: data.rows.map(() => data.calibration_model[layer]),
  };
}
