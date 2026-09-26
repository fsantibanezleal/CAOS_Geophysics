import { describe, expect, it } from "vitest";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { absoluteThreshold, curvePath, membershipField, physicalTarget, propertyScale, selectedModel, sharedScale, uncertaintyProblem } from "../recovery";
import { evaluationLabel, evaluationReason, provenanceDescription, targetDescription } from "../data/evidence";
import { metricInfo, metricValue, methodName } from "../data/metrics";
import { ApplicabilityWarning, DetectionEvidence, EvidenceMetrics, EvaluationStatus, PetrophysicalView, UncertaintyView } from "../components/ScientificEvidence";
import { PotentialCalibration } from "../components/PotentialCalibration";
import type { Method, Run, Uncertainty } from "../science";

function method(overrides: Partial<Method> = {}): Method {
  return { name: "Inverse", name_es: "Inversa", model: [0.1, 0.2], frames: [[0.01, -0.04], [0.03, 0.06]], predicted: [1, 2], residual: [0, 0], history: [3, 1], metrics: {}, ...overrides };
}
function run(overrides: Partial<Run> = {}): Run {
  return { schema: "inverse-earth/v2", id: "test", family: "gravity", name: "Test", name_es: "Prueba", geometry: "independent", variant: "reference", seed: 5, engine: "test", lane: "offline", truth: [0, 1], units: "g/cm³", data_units: "mGal", methods: { l2: method(), irls: method({ model: [0.4, -2], frames: [[0, 3]] }) }, parameters: {}, runtime_seconds: 0, provenance: { synthetic: true, version: "test", license: "CC0", seed: 5 }, ...overrides };
}
function ensemble(overrides: Partial<Uncertainty> = {}): Uncertainty {
  return { kind: "conditional-parametric-bootstrap", conditioning: "Fixed model and independent Gaussian observation noise", members: 20, seed: 13, quantiles: [.05, .95], lower: [80, 170], upper: [120, 230], mean: [100, 200], std: [10, 15], coverage: .5, ...overrides };
}

describe("physical comparison and state identity", () => {
  it("uses the same physical domain for every method, truth and replay", () => {
    const r = run();
    expect(propertyScale(r, "l2")).toEqual(propertyScale(r, "irls"));
    expect(propertyScale(r, "l2").range).toEqual([-3, 3]);
    expect(absoluteThreshold(propertyScale(r, "l2"), .2)).toBeCloseTo(.6);
    expect(absoluteThreshold(propertyScale(r, "irls"), .2)).toBeCloseTo(.6);
  });
  it("keeps negative CNN estimates visible without mixing column and cell units", () => {
    const r = run({ family: "learned", column_truth: [[4, 8]], methods: { cnn: method({ model: [[-10, 2]], frames: [] }), l2: method({ model: [1000, 2000] }) } });
    expect(propertyScale(r, "cnn").range).toEqual([-10, 10]);
    expect(sharedScale([[[1, 2]], [[-3, 1]]], true).range).toEqual([-3, 3]);
  });
  it("defaults to the final model even when the last legacy frame is different", () => {
    const m = method();
    expect(selectedModel(m)).toBe(m.model);
    expect(selectedModel(m, "final", 100)).toBe(m.model);
    expect(selectedModel(m, "replay", 0)).toBe(m.frames[0]);
    expect(selectedModel(m, "replay", 100)).toBe(m.frames[1]);
    expect(m.predicted).toEqual([1, 2]); // replay never overwrites final predictions
    expect(selectedModel(method({ frames: [] }), "replay", 10)).toEqual([.1, .2]);
  });
  it("does not invent a physical threshold for an all-zero field", () => {
    expect(sharedScale([[0, 0]]).maximum).toBe(0);
    expect(absoluteThreshold(sharedScale([[0, 0]]), .5)).toBe(0);
  });
  it("separates secondary property scales and validates mixture responsibility rows", () => {
    const m = method({ magnetic_model: [.01, .02], prior_membership: [[.2, .8], [.9, .1]] });
    const r = run({ family: "joint", secondary_truth: [0, .03], methods: { pgi: m } });
    expect(propertyScale(r, "pgi", true).range).toEqual([0, .03]);
    expect(membershipField(m, 1, 2)).toEqual([.8, .1]);
    expect(membershipField(m, 1, 3)).toBeNull();
    expect(membershipField(method({ prior_membership: [[.8, .8]] }), 0, 1)).toBeNull();
  });
});

describe("evidence contracts", () => {
  it("does not turn missing metrics into zero", () => {
    for (const value of [null, undefined, NaN, Infinity, false]) expect(metricValue(value)).toBeUndefined();
    expect(metricValue(0)).toBe(0);
    expect(curvePath([0, 1, 2], [3, NaN, 5], x => x, y => y)).toBe("M0,3 M2,5");
  });
  it("renders actual metrics and a failing verdict rather than inferring success from data fit", () => {
    const r = run({ methods: { l2: method({ metrics: { active_wrms: .8, heldout_wrms: 29.5, baseline_ratio: 1.3, model_rmse: .4, initial_model_rmse: .3, support_rmse: .6 }, evaluation: { status: "failed", reason_codes: ["worse_than_baseline"] } }) } });
    const html = renderToStaticMarkup(createElement(EvidenceMetrics, { run: r, methodId: "l2" }));
    expect(html).toContain("29.5"); expect(html).toContain("Withheld-observation"); expect(html).toContain("Target-support");
    expect(renderToStaticMarkup(createElement(EvaluationStatus, { method: r.methods.l2 }))).toContain("Recovery criteria failed");
    expect(renderToStaticMarkup(createElement(EvaluationStatus, { method: method() }))).toContain("Recovery not evaluated");
  });
  it("provides bilingual definitions and does not mix model targets", () => {
    for (const key of ["initial_model_rmse", "baseline_ratio", "heldout_wrms", "correlation", "support_rmse", "centroid_error_m", "direction_error_deg", "active_component_wrms", "withheld_relative_mse", "deep_initial_rmse"]) {
      for (const es of [false, true]) { const info = metricInfo(key, "seismic", "fwi-l2", es); expect(info.description.length).toBeGreaterThan(20); expect(info.label).not.toBe(key); }
    }
    expect(metricInfo("initial_velocity_rmse", "seismic").unit).toBe("m/s");
    expect(targetDescription(run({ family: "learned", methods: { cnn: method() } }), "cnn", false)).toContain("not a depth-resolved");
    expect(provenanceDescription(run(), false)).toContain("not measured geology");
    expect(evaluationLabel("negative-control", true)).toBe("Control negativo declarado");
    expect(methodName("pgi", true)).toContain("petrofísica");
  });
  it("rejects mismatched, nonfinite, inverted and mislabelled uncertainty arrays", () => {
    expect(uncertaintyProblem(ensemble(), [100, 200])).toBeNull();
    expect(uncertaintyProblem(ensemble(), [[100, 200]])).toBe("shape");
    expect(uncertaintyProblem(ensemble({ lower: [NaN, 2] }), [100, 200])).toBe("shape");
    expect(uncertaintyProblem(ensemble({ lower: [121, 170] }), [100, 200])).toBe("interval");
    expect(uncertaintyProblem(ensemble({ std: [-1, 2] }), [100, 200])).toBe("interval");
    expect(uncertaintyProblem(ensemble({ coverage: 50 }), [100, 200])).toBe("coverage");
    expect(uncertaintyProblem(ensemble({ quantiles: [.95, .05] }), [100, 200])).toBe("quantiles");
    expect(uncertaintyProblem(ensemble({ members: 1 }), [100, 200])).toBe("members");
  });
  it("renders measured interval bands only when actual ensemble arrays are supplied", () => {
    const m = method({ model: [100, 200], uncertainty: ensemble() });
    const r = run({ family: "mt", truth: [100, 240], methods: { "mt-lm": m } });
    const html = renderToStaticMarkup(createElement(UncertaintyView, { run: r, method: m, section: 0 }));
    expect(html).toContain("not posterior"); expect(html).toContain("50%"); expect(html).toContain("empirical quantiles"); expect(html).toContain("fill-opacity");
    expect(renderToStaticMarkup(createElement(UncertaintyView, { run: r, method: method(), section: 0 }))).toBe("");
  });
  it("renders PGI secondary property and independent prior data", () => {
    const r = run({ family: "joint", grid: { shape: [1, 1, 2], spacing: [80, 80, 70] }, secondary_truth: [0, .03], methods: { pgi: method({ magnetic_model: [.01, .02], prior_membership: [[.2, .8], [.9, .1]], petrophysical_prior: { means: [[.1, .02], [.4, .05]], covariances: [[[.1, 0], [0, .001]], [[.1, 0], [0, .001]]], weights: [.5, .5], source: "Independent petrophysical samples" } }) } });
    const html = renderToStaticMarkup(createElement(PetrophysicalView, { run: r, methodId: "pgi", section: 0 }));
    expect(html).toContain("Final recovered susceptibility"); expect(html).toContain("Mixture responsibility"); expect(html).toContain("Independent petrophysical samples"); expect(html).toContain("0.02");
  });
  it("labels a frozen-network regularization condition and matched column ratios", () => {
    const m = method({ applicability: { varied_parameter: false, reason: "Frozen checkpoint; regularization changes classical comparator only" } });
    const html = renderToStaticMarkup(createElement(ApplicabilityWarning, { method: m }));
    expect(html).toContain("does not retrain");
    expect(renderToStaticMarkup(createElement(ApplicabilityWarning, { method: method() }))).toBe("");
    expect(metricInfo("classical_column_rmse", "learned", "cnn").unit).toBe("g/cm³ m");
    expect(metricInfo("classical_baseline_ratio", "learned", "cnn").description).toContain("Above one");
  });
  it("translates literal physical targets and current MT reasons", () => {
    const targets = [
      ["density contrast", "Contraste de densidad"],
      ["electrical resistivity", "Resistividad por capa"],
      ["acoustic velocity", "Velocidad acústica"],
      ["depth-integrated density contrast", "Contraste de densidad integrado"],
      ["effective magnetization / inducing-field amplitude", "Magnetización efectiva"],
      ["density contrast with jointly estimated susceptibility", "susceptibilidad estimada conjuntamente"],
      ["normalized observation reconstruction error", "Error normalizado"],
    ];
    for (const [quantity, label] of targets) {
      const r = run({ methods: { l2: method({ target: { quantity, units: "SI", dimensionality: 3, provenance: "test" } }) } });
      expect(targetDescription(r, "l2", true)).toContain(label);
    }
    expect(evaluationReason("model_not_better_than_initial", true)).toContain("no mejora");
    expect(evaluationReason("conditional_synthetic_recovery_over_initial", true)).toContain("no se establece unicidad");
  });
  it("separates vector amplitude truth from scalar induced susceptibility", () => {
    const r = run({ family: "magnetics", truth: [-2, 1], methods: { vector: method({ model: [4, 2], vector_truth: [[3, 4, 0], [1, 0, 0]], frames: [] }), l2: method({ model: [100, 200] }) } });
    expect(physicalTarget(r, "vector")).toEqual([5, 1]);
    expect(propertyScale(r, "vector").range).toEqual([0, 5]);
  });
  it("makes zero sensitivity and independently measured undercoverage explicit", () => {
    const html = renderToStaticMarkup(createElement(DetectionEvidence, { data: { calibration_count: 160, calibration_seed: 49001, ood_count: 80, ood_seed: 59001, true_positive: 0, false_negative: 80, false_positive: 1, true_negative: 159, sensitivity: 0, specificity: .99375, roc_auc: .43109, id_test_errors: [], ood_test_errors: [] } }));
    expect(html).toContain("0 / 80");
    expect(html).toContain("missed every tested OOD case");
    expect(html).toContain("High specificity does not compensate");
    const calibration = renderToStaticMarkup(createElement(PotentialCalibration));
    expect(calibration).toContain("9.88%");
    expect(calibration).toContain("16");
    expect(calibration).toContain("nominal 95%");
    expect(calibration).toContain("negative evidence");
  });
  it("renders missed detections without relabelling them as subsurface recovery", () => {
    const html = renderToStaticMarkup(createElement(DetectionEvidence, { data: { calibration_count: 160, calibration_seed: 49001, ood_count: 80, ood_seed: 59001, true_positive: 20, false_negative: 60, false_positive: 8, true_negative: 152, sensitivity: .25, specificity: .95, roc_auc: .61, id_test_errors: [1,2], ood_test_errors: [2,3] } }));
    expect(html).toContain("60"); expect(html).toContain("misses"); expect(html).toContain("0.25"); expect(html).toContain("not whether its subsurface has been recovered");
  });
});
