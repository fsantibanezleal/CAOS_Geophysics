/** Fixed teaching records and scalar explanations, never physical jobs. */
import type { Citation } from "@fasl-work/caos-app-shell";
import catalogueText from "./m01-course-record-index.json?raw";
import q1 from "../../../docs/methods/gravity-processing/scientific-course/01_quantity-and-reference.md?raw";
import q2 from "../../../docs/methods/gravity-processing/scientific-course/02_plate-and-terrain.md?raw";
import q3 from "../../../docs/methods/gravity-processing/scientific-course/03_uncertainty-and-covariance.md?raw";
import q4 from "../../../docs/methods/gravity-processing/scientific-course/04_equivalent-layer.md?raw";
import q5 from "../../../docs/methods/gravity-processing/scientific-course/05_spatial-validation.md?raw";
import q6 from "../../../docs/methods/gravity-processing/scientific-course/06_continuation-and-limits.md?raw";
import { artifactBase, deploymentMode } from "../lib/deployment";

export type Bilingual = readonly [string, string];
export type ExplanationId = "E01" | "E02" | "E03" | "E04";
export const scenarioIds = ["prism-case-0", "prism-case-1", "prism-case-2"] as const;
export type ScenarioId = typeof scenarioIds[number];
export const M01_COURSE_CITATIONS: Citation[] = [
  { id: "m01boule", label: "Boule 0.5", citation: "Boule 0.5.0: rotating normal potential, geodetic latitude and closed-form normal gravity at height.", url: "https://www.fatiando.org/boule/v0.5.0/user_guide/normal_gravity.html" },
  { id: "m01ellipsoid", label: "Boule height API", citation: "Boule 0.5.0 Ellipsoid: normal gravity evaluated at geodetic latitude and ellipsoidal height, not a surface-only formula.", url: "https://www.fatiando.org/boule/v0.5.0/api/generated/boule.Ellipsoid.html" },
  { id: "m01li", label: "Li and Götze 2001", citation: "Li, X. and Götze, H.-J. Ellipsoid, geoid, gravity, geodesy, and geophysics. Geophysics 66(6), 1660-1668 (2001). Reference-surface distinction; not a new reproduction of its numerical appendix.", doi: "10.1190/1.1487109" },
  { id: "m01geoid", label: "NOAA GEOID18", citation: "NOAA GEOID18 technical details: the stated NAD83(2011)/NAVD88 relationship, not a universal conversion or Bartlett datum resolution.", url: "https://www.ngs.noaa.gov/GEOID/GEOID18/geoid18_tech_details.shtml" },
  { id: "m01plate", label: "Harmonica plate", citation: "Harmonica 0.7.0 Bouguer plate correction. General ocean options are not an implemented lane of this station core.", url: "https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.bouguer_correction.html" },
  { id: "m01topography", label: "Harmonica topography", citation: "Harmonica 0.7.0 topographic modelling guide. External terrain modelling differs from supplying a signed plate residual.", url: "https://www.fatiando.org/harmonica/v0.7.0/user_guide/topographic_correction.html" },
  { id: "m01gum", label: "JCGM 100:2008", citation: "JCGM 100:2008, Evaluation of measurement data: Guide to the expression of uncertainty in measurement, section 5. First-order covariance propagation.", url: "https://www.bipm.org/documents/20126/2071204/JCGM_100_2008_E.pdf" },
  { id: "m01gum2026", label: "JCGM amendment 2026", citation: "JCGM 100:2008 Amendment 1:2026. Significant nonlinearity limits the first-order approximation. Official BIPM link; no mirrored PDF.", url: "https://www.bipm.org/documents/20126/2071204/JCGM_100_Amd1_2026.pdf" },
  { id: "m01equivalent", label: "Harmonica equivalent sources", citation: "Harmonica 0.7.0 EquivalentSources: scalar 1/r basis, custom source positions and damped least squares.", url: "https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.EquivalentSources.html" },
  { id: "m01verde", label: "Verde 1.9 least squares", citation: "Verde 1.9.0 least_squares source: uncentred column scaling, Ridge alpha and sample weights.", url: "https://www.fatiando.org/verde/v1.9.0/_modules/verde/base/least_squares.html" },
  { id: "m01blocks", label: "Verde block splits", citation: "Verde 1.9.0 BlockShuffleSplit; block fraction and geometry-count balancing, not a guaranteed row fraction or statistical independence.", url: "https://www.fatiando.org/verde/v1.9.0/api/generated/verde.BlockShuffleSplit.html" },
  { id: "m01folds", label: "Verde inner folds", citation: "Verde 1.9.0 BlockKFold: spatial folds, with shuffle and balancing explicitly chosen by the immutable local transform.", url: "https://www.fatiando.org/verde/v1.9.0/api/generated/verde.BlockKFold.html" },
  { id: "m01continuation", label: "Harmonica continuation", citation: "Harmonica 0.7.0 upward continuation kernel: ideal flat-plane Fourier attenuation and angular wavenumber convention.", url: "https://www.fatiando.org/harmonica/v0.7.0/api/generated/harmonica.filters.upward_continuation_kernel.html" },
  { id: "m01dampney", label: "Dampney 1969", citation: "Dampney, C. N. G. The equivalent source technique. Geophysics 34(1), 39-53 (1969). Further reading; no independent full-paper numerical reproduction is claimed.", doi: "10.1190/1.1439996" },
  { id: "m01roberts", label: "Roberts et al. 2017", citation: "Roberts et al. Cross-validation strategies for data with temporal, spatial, hierarchical, or phylogenetic structure. Ecography 40, 913-929 (2017). Indexed primary discussion, not a reproduced independence theorem.", doi: "10.1111/ecog.02881" },
];

export interface Lesson {
  id: number; title: Bilingual; source: string; refs: string[];
  question: Bilingual; answer: Bilingual; calculator?: ExplanationId;
}
export const lessons: Lesson[] = [
  { id: 1, title: ["Quantity and reference", "Magnitud y referencia"], source: q1, refs: ["m01boule", "m01ellipsoid", "m01li", "m01geoid"], calculator: "E01",
    question: ["At fixed latitude, why is adding approximate free-air after the two reference additions a double correction?", "A latitud fija, ¿por qué sumar aire libre aproximado después de las dos adiciones de referencia duplica la corrección?"],
    answer: ["The two additions sum to −γ(φ,h), already the co-located height-dependent reference subtraction. They do not move the observation to sea level. Processed CBA cannot become absolute gravity by relabelling.", "Las dos adiciones suman −γ(φ,h), la referencia dependiente de altura ya restada en el mismo receptor. No trasladan la observación al nivel del mar. Renombrar CBA no recupera gravedad absoluta."] },
  { id: 2, title: ["Plate and terrain", "Placa y terreno"], source: q2, refs: ["m01plate", "m01topography"], calculator: "E02",
    question: ["If actual topographic attraction exceeds the plate, which sign has T, and is it added or subtracted?", "Si la atracción topográfica real supera la placa, ¿qué signo tiene T y se suma o resta?"],
    answer: ["T=B−A_topo is negative and is added after D_B=D−B. Thus D_T=D−A_topo. The receiver height does not replace the surface thickness of the infinite plate.", "T=B−A_topo es negativo y se suma después de D_B=D−B. Así D_T=D−A_topo. La altura del receptor no sustituye el espesor de superficie de la placa infinita."] },
  { id: 3, title: ["Errors and dependence", "Errores y dependencia"], source: q3, refs: ["m01gum", "m01gum2026"], calculator: "E03",
    question: ["Why must one shared geoid error enter through a combined derivative, rather than two independent height errors?", "¿Por qué un mismo error geoidal entra mediante una derivada combinada y no dos errores independientes de altura?"],
    answer: ["Both h_r and h_s contain the same N. Their signed derivatives combine before RSS or absolute-value bounds. Independent copies discard known covariance and cancellation. A marginal upper bound is not an independent station SD.", "h_r y h_s contienen el mismo N. Las derivadas con signo se combinan antes de RSS o cotas absolutas. Copias independientes pierden covarianza y cancelación conocidas. Una cota marginal no es DE independiente por estación."] },
  { id: 4, title: ["Equivalent layer", "Capa equivalente"], source: q4, refs: ["m01equivalent", "m01verde", "m01dampney"],
    question: ["Do stable fits at different source depths identify a density body?", "¿Ajustes estables a distintas profundidades identifican un cuerpo de densidad?"],
    answer: ["No. The fitted kernel is scalar 1/r; coefficients have mGal m units, not kg/m³. Mathematical sources and a damped condition number do not remove geological nonuniqueness. Noise-transfer SD also excludes model bias and selection.", "No. El núcleo ajustado es 1/r escalar; los coeficientes tienen mGal m, no kg/m³. Fuentes matemáticas y condición amortiguada no eliminan no unicidad geológica. La DE transferida también excluye sesgo y selección."] },
  { id: 5, title: ["Spatial validation", "Validación espacial"], source: q5, refs: ["m01blocks", "m01folds", "m01verde", "m01roberts"],
    question: ["Can outer holdout RMSE choose depth, damping, radius or a new mask?", "¿Puede RMSE de reserva externa elegir profundidad, penalización, radio o una nueva máscara?"],
    answer: ["No. Geometry freezes the outer split; inner folds select only within outer training. Changing held-out observations changes evaluation, not the selected model. Unsupported counts remain alongside RMSE; a block split does not prove independence.", "No. La geometría fija la partición externa; los pliegues internos seleccionan solo dentro del entrenamiento externo. Cambiar observaciones reservadas cambia evaluación, no modelo. Los conteos sin soporte acompañan RMSE; los bloques no prueban independencia."] },
  { id: 6, title: ["Continuation and limits", "Continuación y límites"], source: q6, refs: ["m01continuation", "m01equivalent", "m01gum"], calculator: "E04",
    question: ["Why does a higher target often look smoother without establishing better geological resolution?", "¿Por qué un destino más alto suele verse suave sin demostrar mejor resolución geológica?"],
    answer: ["Ideal source-free modes attenuate as exp(−2πΔh/λ), with short wavelengths attenuated more. Real grids use the irregular equivalent layer and conditional noise transfer. Null support is not filled, downward heights reject, and the lowest height satisfying a preset noise ceiling is not a recovered geological resolution.", "Los modos ideales sin fuentes se atenúan como exp(−2πΔh/λ), más para longitudes cortas. Las mallas reales usan capa irregular y transferencia condicional de ruido. No se rellenan null, alturas descendentes rechazan y el menor destino que cumple la cota prefijada no es resolución geológica recuperada."] },
];

/** Display the frozen physics, not historical engineering-stage statements.
 * Original Markdown bytes remain unchanged. Only explicit historical status
 * sentences are omitted from the current teaching view. No physical waiver.
 */
const historicalStatements = [
  "This recipe was not executed in the wiki stage.",
  "The recipe was syntax-checked only, not executed in this wiki milestone.",
  "It was not executed in this wiki milestone.",
  "It was syntax-checked but not executed for this wiki milestone.",
  "; it was not executed in this wiki milestone",
  "Solo fue comprobado sintácticamente.",
  "; no se ejecutó en este hito wiki",
  " y no se ejecutó en este hito wiki",
  "Aquí no se ejecutan controles, métricas, tolerancias ni modelos reales.",
  "Aquí no se ejecuta oráculo/validación ni se adopta JUnit privado como resultado del curso.",
  " Solo fue comprobado sintácticamente.",
  "No new control, metric, tolerance or field model is executed here.",
  "No oracle or blocked run is executed for this wiki stage, and no historical private JUnit is adopted as a course result.",
];
export function lessonBody(lesson: Lesson, language: 0 | 1): string {
  const english = lesson.source.indexOf("## English");
  const spanish = lesson.source.indexOf("## Español");
  let body = language === 0 ? lesson.source.slice(english, spanish) : lesson.source.slice(spanish);
  for (const historical of historicalStatements) body = body.replaceAll(historical, "");
  // Display the same dimensioned equations in both languages. The reviewed
  // Spanish derivations refer to these equations, without duplicating fences.
  if (language === 1) {
    const equations = lesson.source.slice(english, spanish).match(/\\\[[\s\S]*?\\\]/g) ?? [];
    const firstBreak = body.indexOf("\n\n");
    body = body.slice(0, firstBreak) + "\n\n" + equations.join("\n\n") + body.slice(firstBreak);
  }
  return body.trim();
}

export interface ExplanationField { key: string; label: Bilingual; min: number; max: number; initial: number; }
export const explanationFields: Record<ExplanationId, ExplanationField[]> = {
  E01: [{ key: "latitude_deg", label: ["Geodetic latitude (°)", "Latitud geodésica (°)"], min: -90, max: 90, initial: 45 }],
  E02: [
    { key: "density_kg_m3", label: ["Supplied density (kg/m³)", "Densidad suministrada (kg/m³)"], min: 1, max: 10000, initial: 2670 },
    { key: "plate_thickness_m", label: ["Land plate thickness (m)", "Espesor de placa terrestre (m)"], min: 0, max: 10000, initial: 1000 },
  ],
  E03: [
    { key: "a1", label: ["First sensitivity (dimensionless)", "Primera sensibilidad (adimensional)"], min: -1, max: 1, initial: 1 },
    { key: "a2", label: ["Second sensitivity (dimensionless)", "Segunda sensibilidad (adimensional)"], min: -1, max: 1, initial: 1 },
    { key: "sigma1_mgal", label: ["First declared toy SD (mGal)", "Primera DE docente declarada (mGal)"], min: 0, max: 1, initial: .02 },
    { key: "sigma2_mgal", label: ["Second declared toy SD (mGal)", "Segunda DE docente declarada (mGal)"], min: 0, max: 1, initial: .02 },
    { key: "correlation", label: ["Declared correlation", "Correlación declarada"], min: -1, max: 1, initial: 0 },
  ],
  E04: [
    { key: "wavelength_m", label: ["Wavelength (m)", "Longitud de onda (m)"], min: 10, max: 20000, initial: 500 },
    { key: "delta_height_m", label: ["Upward increment (m)", "Incremento ascendente (m)"], min: 0, max: 10000, initial: 300 },
    { key: "amplitude_mgal", label: ["Original amplitude (mGal)", "Amplitud original (mGal)"], min: 0, max: 100, initial: 1 },
  ],
};
export const explanationAssumptions: Record<ExplanationId, Bilingual> = {
  E01: ["Surface Somigliana only, with rounded WGS84 constants. Not the closed-form reference at height or a processed station.", "Solo Somigliana superficial con constantes WGS84 redondeadas. No es referencia completa a altura ni estación procesada."],
  E02: ["Infinite horizontal land plate, receiver above plate; G=6.67430e−11 SI. No DEM, ocean or recovered density.", "Placa terrestre horizontal infinita, receptor sobre la placa; G=6.67430e−11 SI. Sin DEM, océano ni densidad recuperada."],
  E03: ["Two linear gravity errors, dimensionless sensitivities and declared correlation. The marginal bound is not measured SD or confidence. Defined zero toy SD does not fill a missing field error.", "Dos errores gravimétricos lineales, sensibilidades adimensionales y correlación declarada. La cota marginal no es DE medida ni confianza. DE docente cero no completa error de campo ausente."],
  E04: ["Ideal source-free flat-plane Fourier mode, k=2π/wavelength in rad/m. Incremental height, not the solver's absolute coordinate. No downward continuation or equivalent-source solve.", "Modo de Fourier ideal sin fuentes en plano, k=2π/longitud en rad/m. Altura incremental, no coordenada absoluta del solver. Sin continuación descendente ni ajuste equivalente."],
};
export function calculateExplanation(id: ExplanationId, input: Record<string, number>): Record<string, number> {
  const fields = explanationFields[id];
  if (!fields || !input || Object.getPrototypeOf(input) !== Object.prototype ||
      Object.keys(input).length !== fields.length ||
      fields.some(f => typeof input[f.key] !== "number" || !Number.isFinite(input[f.key]) ||
        input[f.key] < f.min || input[f.key] > f.max)) throw new Error("Invalid explanatory input.");
  if (id === "E01") {
    const f = 1 / 298.257223563, ge = 9.7803253359, gp = 9.8321849378;
    const k = (1 - f) * gp / ge - 1, e2 = 2 * f - f * f;
    const s = Math.sin(input.latitude_deg * Math.PI / 180) ** 2;
    return { surface_reference_mgal: ge * (1 + k * s) / Math.sqrt(1 - e2 * s) * 1e5 };
  }
  if (id === "E02") {
    const plate = 2 * Math.PI * 6.67430e-11 * input.density_kg_m3 * input.plate_thickness_m * 1e5;
    return { plate_mgal: plate, subtractive_mgal: -plate };
  }
  if (id === "E03") {
    const x = input.a1 * input.sigma1_mgal, y = input.a2 * input.sigma2_mgal;
    return { linear_sd_mgal: Math.sqrt(Math.max(x*x + y*y + 2*x*y*input.correlation, 0)),
      marginal_sd_upper_bound_mgal: Math.abs(x) + Math.abs(y) };
  }
  const attenuation = Math.exp(-2 * Math.PI * input.delta_height_m / input.wavelength_m);
  return { attenuation, continued_amplitude_mgal: attenuation * input.amplitude_mgal };
}

export interface Artifact { role: string; path: string; bytes: number; sha256: string; }
export interface CourseIndex {
  schema_version: "m01-course-record-1"; scenario_id: ScenarioId; label_kind: "synthetic_control_replay";
  request_sha256: string; result_sha256: string; source_pins: Record<string, string>;
  runtime: { python: string; python_implementation: "CPython"; engines: Record<string, string> };
  artifacts: Artifact[];
}
export interface Grid {
  height_m: number; shape: [number, number]; predicted_mgal: (number|null)[];
  conditional_sigma_mgal: (number|null)[]; covered: boolean[]; outside_hull: boolean[];
  outside_radius: boolean[]; nearest_training_m: number[]; max_conditional_sigma_mgal: number;
  adjacent_easting_difference_rms_mgal: number|null; height_precision_passed: boolean;
}
export interface Metric { covered_count: number; unsupported_count: number; rmse_mgal: number|null;
  normalized_rmse: number|null; signed_mean_mgal: number|null; }
export interface Alternative { depth_m: number; damping: number; status: string; reason?: string;
  training_rmse_mgal?: number; coefficient_l2_mgal_m?: number; damped_condition?: number; }
export interface CourseResult {
  schema_version: string; original_correction_result: Record<string, unknown>;
  geometry: { easting_m: number[]; northing_m: number[]; upward_m: number[]; mask: boolean[];
    mask_reasons: (string|null)[]; station_ids: string[] };
  config: Record<string, unknown>;
  model: { depth_m: number; damping: number; coefficients_mgal_m: number[]; training_indices: number[]; interpretation: string };
  selection: { depth_m: number; damping: number; height_m: number|null; status: string; candidates: Record<string, unknown>[] };
  split: { train_indices: number[]; holdout_indices: number[]; partition: string[]; sha256: string };
  stations: { observed_mgal: number[]; predicted_mgal: (number|null)[]; fit_sigma_mgal: number[];
    signed_predicted_minus_observed_mgal: (number|null)[]; prediction_covered: boolean[] };
  evaluation: { train: Metric; holdout: Metric };
  axes: { easting_m: number[]; northing_m: number[]; grid_axis_order: string; unit: string };
  grids: Grid[]; condition: { damped_condition: number; weighted_design_condition: number };
  nonuniqueness: { training_only_alternatives: Alternative[] };
  uncertainty: { kind: string; excludes: string[] }; resolution: Record<string, unknown>;
  provenance: { request_sha256: string; module_sha256: string; python: string; engines: Record<string,string>;
    corrections_reapplied: false; full_method_accepted: false; field_gate: "open" };
}
export interface VerifiedCourseRecord { index: CourseIndex; result: CourseResult;
  request: Record<string, unknown>; receipt: Record<string, unknown>;
  load: { fetched_bytes: number; elapsed_ms: number; parsed_objects: 3 }; }
export const artifactNames: Record<string, string> = {
  request: "request.json", result: "result.json", export_receipt: "receipt.json",
  map_light: "maps-light.svg", map_dark: "maps-dark.svg", diagnostics_light: "diagnostics-light.svg",
  diagnostics_dark: "diagnostics-dark.svg", map_light_png: "maps-light.png", map_dark_png: "maps-dark.png",
  diagnostics_light_png: "diagnostics-light.png", diagnostics_dark_png: "diagnostics-dark.png",
};
// This is an ORIGINAL INDEX FILE-BYTE hash, never a JS scientific-object hash.
export const catalogueByteIdentity = { bytes: 10476, sha256: "e2d6752f235050cab1571f2ed33588586744074d6ec4aaa650ff9e6bb13c97ba" };
function expect(ok: unknown): asserts ok { if (!ok) throw new Error("Recorded control integrity failed."); }
function exact(value: unknown, keys: string[]): asserts value is Record<string, unknown> {
  expect(value !== null && typeof value === "object" && !Array.isArray(value));
  expect(Object.keys(value).sort().join("|") === [...keys].sort().join("|"));
}
function hash(value: unknown): value is string { return typeof value === "string" && /^[0-9a-f]{64}$/.test(value); }
export async function fileByteHash(bytes: Uint8Array): Promise<string> {
  const buffer = bytes.slice().buffer; // bounded verified byte view, not scientific serialization
  return Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", buffer)),
    b => b.toString(16).padStart(2, "0")).join("");
}
export async function verifiedCatalogue(): Promise<CourseIndex[]> {
  const raw = new TextEncoder().encode(catalogueText);
  expect(raw.length === catalogueByteIdentity.bytes && await fileByteHash(raw) === catalogueByteIdentity.sha256);
  const entries: unknown = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(raw));
  expect(Array.isArray(entries) && entries.length === 3);
  entries.forEach((item, i) => {
    exact(item, ["schema_version", "scenario_id", "label_kind", "request_sha256", "result_sha256", "source_pins", "runtime", "artifacts"]);
    expect(item.schema_version === "m01-course-record-1" && item.label_kind === "synthetic_control_replay" && item.scenario_id === scenarioIds[i]);
    expect(hash(item.request_sha256) && hash(item.result_sha256));
    exact(item.source_pins, ["gravity_processing.py", "gravity_station_adapter.py", "gravity_transforms.py", "gravity_transform_controls.py", "gravity_transform_figures.py"]);
    expect(Object.values(item.source_pins).every(hash));
    exact(item.runtime, ["python", "python_implementation", "engines"]);
    expect(item.runtime.python_implementation === "CPython" && typeof item.runtime.python === "string" && /^3\.12\.\d+$/.test(item.runtime.python));
    exact(item.runtime.engines, ["boule", "harmonica", "numpy", "scipy", "verde", "scikit-learn", "matplotlib"]);
    expect(Array.isArray(item.artifacts) && item.artifacts.length === 11);
    const roles = new Set<string>();
    item.artifacts.forEach(a => {
      exact(a, ["role", "path", "bytes", "sha256"]);
      expect(typeof a.role === "string" && Object.hasOwn(artifactNames, a.role) && !roles.has(a.role));
      roles.add(a.role);
      expect(a.path === item.scenario_id + "/" + artifactNames[a.role] && hash(a.sha256));
      expect(typeof a.bytes === "number" && Number.isSafeInteger(a.bytes) && a.bytes > 0 && a.bytes <= 32 * 1024 * 1024);
    });
  });
  return entries as CourseIndex[];
}
export type FetchBytes = (url: string, init: RequestInit) => Promise<Response>;
export async function readBoundArtifact(entry: Artifact, signal: AbortSignal, fetcher: FetchBytes = fetch): Promise<Uint8Array> {
  exact(entry, ["role", "path", "bytes", "sha256"]);
  expect(Object.hasOwn(artifactNames, entry.role));
  expect(scenarioIds.some(id => entry.path === id + "/" + artifactNames[entry.role]));
  expect(Number.isSafeInteger(entry.bytes) && entry.bytes > 0 && entry.bytes <= 32 * 1024 * 1024 && hash(entry.sha256));
  if (signal.aborted) throw new DOMException("Aborted", "AbortError");
  const prefix = typeof window === "undefined" ? "/" : artifactBase(deploymentMode, window.location.pathname);
  const response = await fetcher(prefix + "data/m01-scientific-course/" + entry.path, { signal, cache: "no-store" });
  expect(response.ok && response.body !== null);
  const reader = response.body.getReader(), buffer = new Uint8Array(entry.bytes + 1);
  let count = 0;
  try {
    while (true) {
      if (signal.aborted) throw new DOMException("Aborted", "AbortError");
      const chunk = await reader.read();
      if (chunk.done) break;
      // Inspect/count the received chunk BEFORE copying or parsing; a source
      // byte beyond the measured bound rejects. Headers are not the bound.
      expect(chunk.value instanceof Uint8Array && count + chunk.value.length <= entry.bytes);
      buffer.set(chunk.value, count); count += chunk.value.length;
    }
  } finally { await reader.cancel().catch(() => undefined); reader.releaseLock(); }
  expect(count === entry.bytes);
  const bytes = buffer.subarray(0, count);
  expect(await fileByteHash(bytes) === entry.sha256);
  return bytes;
}
function sameStrings(left: unknown, right: unknown): boolean {
  if (!left || !right || typeof left !== "object" || typeof right !== "object" || Array.isArray(left) || Array.isArray(right)) return false;
  const a = left as Record<string,unknown>, b = right as Record<string,unknown>;
  return Object.keys(a).length === Object.keys(b).length && Object.keys(a).every(k => typeof a[k] === "string" && a[k] === b[k]);
}
/** Display admission is byte/cross-binding verification, NOT scientific replay.
 * It never reserializes the parent, rebuilds integer history or authenticates
 * provider/runtime origin. Python's independent replay remains separate.
 */
export async function loadCourseRecord(id: ScenarioId, signal: AbortSignal, fetcher: FetchBytes = fetch): Promise<VerifiedCourseRecord> {
  const started = performance.now(), catalogue = await verifiedCatalogue();
  const item = catalogue.find(record => record.scenario_id === id); expect(item);
  const parsed: Record<string, Record<string,unknown>> = {};
  let fetchedBytes = 0;
  for (const role of ["request", "result", "export_receipt"]) {
    const artifact = item.artifacts.find(a => a.role === role); expect(artifact);
    const raw = await readBoundArtifact(artifact, signal, fetcher); fetchedBytes += raw.length;
    parsed[role] = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(raw));
  }
  const request = parsed.request, result = parsed.result, receipt = parsed.export_receipt;
  exact(request, ["schema_version", "correction_result", "geometry", "config"]);
  exact(result, ["schema_version", "original_correction_result", "geometry", "config", "model", "selection", "split", "stations", "evaluation", "axes", "grids", "condition", "nonuniqueness", "uncertainty", "resolution", "provenance"]);
  exact(receipt, ["schema_version", "executed_utc", "request_sha256", "result_sha256", "files", "full_method_accepted"]);
  expect(request.schema_version === "gravity-transform-request-1" && result.schema_version === "gravity-transform-result-1");
  expect(receipt.schema_version === "gravity-transform-export-1" && receipt.full_method_accepted === false);
  expect(receipt.request_sha256 === item.request_sha256 && receipt.result_sha256 === item.result_sha256);
  expect(typeof receipt.executed_utc === "string" && Number.isFinite(Date.parse(receipt.executed_utc)));
  expect(Array.isArray(receipt.files) && receipt.files.length === 10);
  const manifest = new Set<string>();
  receipt.files.forEach(file => {
    exact(file, ["name", "bytes", "sha256"]);
    expect(typeof file.name === "string" && !manifest.has(file.name)); manifest.add(file.name);
    const artifact = item.artifacts.find(a => a.role !== "export_receipt" && a.path === id + "/" + file.name);
    expect(artifact && artifact.bytes === file.bytes && artifact.sha256 === file.sha256);
  });
  const p = result.provenance as Record<string,unknown>;
  expect(p.request_sha256 === item.request_sha256 && p.module_sha256 === item.source_pins["gravity_transforms.py"]);
  expect(p.corrections_reapplied === false && p.full_method_accepted === false && p.field_gate === "open");
  expect(p.python === item.runtime.python && sameStrings(p.engines, item.runtime.engines));
  const r = result as unknown as CourseResult;
  expect(Array.isArray(r.geometry.easting_m) && r.geometry.easting_m.length === 196);
  const n = r.geometry.easting_m.length;
  for (const a of [r.geometry.easting_m, r.geometry.northing_m, r.geometry.upward_m, r.stations.observed_mgal, r.stations.fit_sigma_mgal]) {
    expect(Array.isArray(a) && a.length === n && a.every(x => typeof x === "number" && Number.isFinite(x)));
  }
  expect(r.stations.fit_sigma_mgal.every(x => x > 0));
  expect(r.geometry.mask.length === n && r.geometry.mask.every(x => typeof x === "boolean"));
  expect(r.split.partition.length === n && hash(r.split.sha256));
  const train = new Set(r.split.train_indices), holdout = new Set(r.split.holdout_indices);
  expect(train.size === r.split.train_indices.length && holdout.size === r.split.holdout_indices.length &&
    [...train, ...holdout].every(x => Number.isInteger(x) && x >= 0 && x < n && !r.geometry.mask[x]) &&
    [...holdout].every(x => !train.has(x)));
  expect(r.axes.grid_axis_order === "northing,easting" && r.axes.unit === "mGal");
  expect(Array.isArray(r.grids) && r.grids.length === 3);
  r.grids.forEach(g => {
    const cells = r.axes.easting_m.length * r.axes.northing_m.length;
    expect(g.shape[0] === r.axes.northing_m.length && g.shape[1] === r.axes.easting_m.length && cells <= 12000);
    expect([g.predicted_mgal, g.conditional_sigma_mgal, g.covered, g.outside_hull, g.outside_radius, g.nearest_training_m].every(a => Array.isArray(a) && a.length === cells));
    g.covered.forEach((keep, i) => {
      expect(typeof keep === "boolean" && typeof g.outside_hull[i] === "boolean" && typeof g.outside_radius[i] === "boolean");
      expect(keep === (!g.outside_hull[i] && !g.outside_radius[i]));
      const v = g.predicted_mgal[i], sd = g.conditional_sigma_mgal[i];
      expect(keep ? typeof v === "number" && Number.isFinite(v) && typeof sd === "number" && Number.isFinite(sd) && sd >= 0 : v === null && sd === null);
    });
    expect(g.height_m >= Math.max(...r.geometry.upward_m));
  });
  expect(r.uncertainty.kind === "conditional_linear_noise_propagation" && r.uncertainty.excludes.includes("Geological uncertainty"));
  expect(r.selection.height_m === Math.min(...r.grids.filter(g => g.height_precision_passed).map(g => g.height_m)));
  if (signal.aborted) throw new DOMException("Aborted", "AbortError");
  return { index: item, request, result: r, receipt, load: { fetched_bytes: fetchedBytes, elapsed_ms: performance.now() - started, parsed_objects: 3 } };
}
