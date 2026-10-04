import { verifyProcessingBundle, type FlagResult, type GravityDataset, type ProcessingJob } from "../api/processing-contracts";
import { verifyMtBundle, type EdiDataset, type MtResult } from "../api/mt-contracts";
import type { MtProcessingJob } from "../api/processing-contracts";

type GravityContext = { kind: "gravity"; job: ProcessingJob; dataset: GravityDataset };
type MtContext = { kind: "mt"; job: MtProcessingJob; dataset: EdiDataset };
export function readSavedResult(blob: Blob, context: GravityContext): Promise<FlagResult>;
export function readSavedResult(blob: Blob, context: MtContext): Promise<MtResult>;
export async function readSavedResult(blob: Blob, context: GravityContext | MtContext) {
  // Reject from metadata before either verifier reads/decompresses any bytes.
  if (context.job.state !== "succeeded" || !Number.isSafeInteger(blob.size) || blob.size < 22 || blob.size > 17 * 1048576) throw new Error("A successful selected job and a 22-byte to 17-MiB saved ZIP are required");
  return context.kind === "gravity"
    ? (await verifyProcessingBundle(blob, context.job, context.dataset)).result
    : (await verifyMtBundle(blob, context.job, context.dataset)).result;
}
function indexIn(index: number, count: number) {
  if (!Number.isInteger(index) || index < 0 || index >= count) throw new Error("Inspection index is outside the returned data");
}
export function gravityInspection(dataset: GravityDataset, result: FlagResult | null, selected: number) {
  indexIn(selected, dataset.station_ids.length);
  return { schema: "geophysics.result-inspection/v1", kind: "gravity-station-qc", inspection_only: true,
    units: { position: "m", observation: "mGal", uncertainty: "mGal", robust_score: "1" },
    selected: { index: selected, station_id: dataset.station_ids[selected] }, dataset, result,
    prediction: null, residual: null, model: null,
    limitation: "Inspection snapshot, not original producer bytes. Flag QC preserves all observations and errors; no inverse." };
}
export function mtReadout(result: MtResult, selected: number) {
  indexIn(selected, result.frequency_hz.length);
  const m = result.inverse?.methods["mt-lm"];
  const component = (c: "xy" | "yx") => {
    const obs = result.screen.observed[c], sigma = obs.sigma_real_imag_ohm[selected];
    const observed = { real: obs.real[selected], imag: obs.imag[selected], apparent: obs.apparent[selected], phase: obs.phase[selected] };
    const predicted = m ? { real: m.predicted.real[selected], imag: m.predicted.imag[selected], apparent: m.predicted.apparent[selected], phase: m.predicted.phase[selected] } : null;
    const residual = predicted ? { real: observed.real - predicted.real, imag: observed.imag - predicted.imag } : null;
    return { observed, sigma_real_imag_ohm: sigma, predicted, residual,
      standardized_residual: residual ? { real: residual.real / sigma, imag: residual.imag / sigma } : null };
  };
  return { index: selected, frequency_hz: result.frequency_hz[selected], period_s: 1 / result.frequency_hz[selected],
    partition: result.inverse ? result.inverse.active[selected] ? "training" : "heldout" : "qc-only",
    components: { xy: component("xy"), yx: component("yx") } };
}
export function mtInspection(result: MtResult, selected: number) {
  return { schema: "geophysics.result-inspection/v1", kind: "mt", inspection_only: true,
    units: { frequency: "Hz", period: "s", impedance: "ohm E/H", sigma: "ohm SD per real/imaginary component", resistivity: "ohm m", phase: "degrees" },
    selected: mtReadout(result, selected), result,
    limitation: "Parsed inspection snapshot, not original producer bytes or geological truth. XY is fitted; -YX is sign-corrected and not independently fitted." };
}
export function recordedMtState(result: MtResult, frame: number) {
  const inverse = result.inverse;
  if (!inverse) throw new Error("M05 contains no recorded inverse states");
  const m = inverse.methods["mt-lm"];
  indexIn(frame, m.frames.length);
  return { schema: "geophysics.recorded-mt-state/v1", evaluation_kind: "residual-evaluation-record",
    dataset_id: result.dataset_id, job_id: result.job_id, request_sha256: result.request_sha256,
    dataset_sha256: result.dataset_sha256, raw_sha256: result.raw_sha256, engine_sha256: result.engine_sha256,
    source: result.source, physical_metadata: result.physical_metadata,
    frame_index: frame, state: m.states[frame], objective: m.history[frame], model_ohm_m: m.frames[frame],
    thickness_m: inverse.thickness, units: { model: "ohm m", thickness: "m", objective: "1" },
    historical_prediction: null,
    limitation: "Recorded residual evaluation, not necessarily an accepted optimizer iteration. No historical response arrays are supplied." };
}
/** Numeric JSON is an inspection sidecar, never a substitute for a verified ZIP. */
export function downloadInspection(value: unknown, filename: string) {
  const text = JSON.stringify(value, (_key, v: unknown) => {
    if (typeof v === "number" && !Number.isFinite(v)) throw new Error("Nonfinite inspection value cannot be exported");
    return v;
  }, 2);
  const url = URL.createObjectURL(new Blob([text], { type: "application/json" }));
  const link = document.createElement("a"); link.href = url; link.download = filename; link.click();
  setTimeout(() => URL.revokeObjectURL(url), 30_000);
}
