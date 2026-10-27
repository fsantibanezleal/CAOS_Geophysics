import { useState } from "react";
import { useShellLang } from "@fasl-work/caos-app-shell";
import { Plot } from "./ScientificPlots";

const PROTOCOL = "m12-learned-residual/v3.1";
const MANIFEST_SCHEMA = "caos-geophysics.local-experiment-manifest/v1";
const RECEIPT_SCHEMA = "caos-geophysics.m12-residual/v3.1";
const FILES = ["receipt.json", "local-evidence-manifest.json", "m12-residual-v3.1.npz"] as const;
const COUNTS: Record<string, number> = { train: 1200, validation: 160, id_test: 160, family_only: 80, acquisition_only: 80, joint_ood: 160 };
const EVALUATION_COHORTS = ["validation", "id_test", "family_only", "acquisition_only", "joint_ood"] as const;
type Obj = Record<string, any>;
export type M12Evidence = { receipt: Obj; checkpointBytes: number; checkpointSha256: string };

const object = (v: unknown): v is Obj => !!v && typeof v === "object" && !Array.isArray(v);
const finite = (v: unknown): v is number => typeof v === "number" && Number.isFinite(v);
const sha256 = async (bytes: ArrayBuffer) => Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", bytes)), x => x.toString(16).padStart(2, "0")).join("");

/** Integrity admission only: a matching manifest does not authenticate a source or prove scientific validity. */
export async function admitM12Evidence(selected: Partial<Record<(typeof FILES)[number], File>>): Promise<M12Evidence> {
  for (const name of FILES) {
    const file = selected[name];
    if (!file) throw new Error(`Select ${name}.`);
    if (file.name !== name) throw new Error(`Expected exact filename ${name}; received ${file.name || "unnamed file"}.`);
  }
  const [receiptBytes, manifestBytes, checkpointBytes] = await Promise.all(FILES.map(name => selected[name]!.arrayBuffer()));
  let manifest: Obj, receipt: Obj;
  try { manifest = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(manifestBytes)); }
  catch { throw new Error("The local evidence manifest is unavailable or is not valid UTF-8 JSON."); }
  if (!object(manifest) || manifest.schema !== MANIFEST_SCHEMA || manifest.protocol !== PROTOCOL)
    throw new Error("Unsupported manifest schema or protocol.");
  const entries = manifest.files;
  const expected = ["m12-residual-v3.1.npz", "receipt.json"];
  if (!object(entries) || Object.keys(entries).length !== expected.length ||
      Object.keys(entries).sort().join("|") !== expected.sort().join("|") ||
      expected.some(name => !object(entries[name])))
    throw new Error("Manifest must name exactly receipt.json and m12-residual-v3.1.npz.");
  for (const [name, bytes] of [["receipt.json", receiptBytes], ["m12-residual-v3.1.npz", checkpointBytes]] as const) {
    const entry = entries[name];
    if (!Number.isSafeInteger(entry.bytes) || entry.bytes !== bytes.byteLength) throw new Error(`${name} byte length does not match the manifest.`);
    if (typeof entry.sha256 !== "string" || !/^[a-f\d]{64}$/.test(entry.sha256) || entry.sha256 !== await sha256(bytes))
      throw new Error(`${name} SHA-256 does not match the manifest.`);
  }
  try { receipt = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(receiptBytes)); }
  catch { throw new Error("The receipt is unavailable or is not valid UTF-8 JSON."); }
  validateReceipt(receipt);
  const checkpointSha256 = await sha256(checkpointBytes);
  if (receipt.checkpoint !== "m12-residual-v3.1.npz" || receipt.checkpoint_sha256 !== checkpointSha256)
    throw new Error("Receipt checkpoint filename or SHA-256 does not match the selected checkpoint.");
  return { receipt, checkpointBytes: checkpointBytes.byteLength, checkpointSha256 };
}

function validateReceipt(r: unknown): asserts r is Obj {
  if (!object(r) || r.schema !== RECEIPT_SCHEMA || r.protocol !== PROTOCOL) throw new Error("Unsupported or malformed M12 receipt.");
  if (r.status !== "failed-held-out-comparator") throw new Error("Receipt status is not the required failed-held-out-comparator result; optimistic or unknown status is refused.");
  if (!object(r.counts) || Object.keys(COUNTS).some(k => r.counts[k] !== COUNTS[k]) || Object.keys(r.counts).length !== Object.keys(COUNTS).length)
    throw new Error("Receipt cohort counts do not match the declared M12 v3.1 populations.");
  if (!object(r.cpu_cuda_parity) || r.cpu_cuda_parity.status !== "pass" || !["max_abs_m_s", "p99_abs_m_s", "mean_abs_m_s"].every(k => finite(r.cpu_cuda_parity[k])))
    throw new Error("CPU/CUDA parity evidence is missing, non-finite, or not passed.");
  if (!Array.isArray(r.history) || r.history.length < 2 || r.history.some((p: unknown, i: number) => !object(p) || !Number.isSafeInteger(p.epoch) || p.epoch !== i || !finite(p.validation_velocity_rmse_m_s) || p.validation_velocity_rmse_m_s < 0))
    throw new Error("Training history must contain finite, sequential epoch and validation RMSE values.");
  const selected = r.history.find((p: Obj) => p.epoch === r.selected_epoch);
  const best = Math.min(...r.history.map((p: Obj) => p.validation_velocity_rmse_m_s));
  if (!Number.isSafeInteger(r.selected_epoch) || !selected || selected.validation_velocity_rmse_m_s !== best)
    throw new Error("Selected epoch does not match the minimum recorded validation RMSE.");
  if (!object(r.cohorts) || Object.keys(r.cohorts).length !== EVALUATION_COHORTS.length || EVALUATION_COHORTS.some(k => !object(r.cohorts[k]) || r.cohorts[k].count !== COUNTS[k]))
    throw new Error("One or more cohort results are missing or have unexpected counts.");
  for (const [name, c] of Object.entries(r.cohorts) as [string, Obj][]) {
    if (!(name in COUNTS) || !finite(c.learned_velocity_rmse_m_s) || !finite(c.classical_velocity_rmse_m_s) ||
        !finite(c.learned_oracle_rmse_ms) || !finite(c.classical_oracle_rmse_ms) ||
        !finite(c.learned_to_classical_velocity_ratio) || !finite(c.learned_to_classical_oracle_ratio))
      throw new Error(`Cohort ${name} has an unknown name or non-finite metrics.`);
  }
  const joint = r.cohorts.joint_ood;
  if (joint.learned_to_classical_velocity_ratio < 1 && joint.learned_to_classical_oracle_ratio < 1)
    throw new Error("Receipt claims comparator failure while both joint held-out ratios favor the learned method; status is inconsistent.");
  if (!Array.isArray(r.limitations) || r.limitations.length === 0) throw new Error("Receipt limitations are missing.");
}

export function M12ResidualEvidence() {
  const es = useShellLang() === "es";
  const t = (en: string, sp: string) => es ? sp : en;
  const [files, setFiles] = useState<Partial<Record<(typeof FILES)[number], File>>>({});
  const [evidence, setEvidence] = useState<M12Evidence | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const choose = (name: (typeof FILES)[number], file?: File) => { setFiles(old => ({ ...old, [name]: file })); setEvidence(null); setError(""); };
  const inspect = async () => {
    setBusy(true); setEvidence(null); setError("");
    try { setEvidence(await admitM12Evidence(files)); }
    catch (e) { setError(e instanceof Error ? e.message : t("File reading failed.", "Falló la lectura de archivos.")); }
    finally { setBusy(false); }
  };
  const r = evidence?.receipt;
  const names = ["validation", "id_test", "family_only", "acquisition_only", "joint_ood"];
  const cohorts = r ? names.map(name => r.cohorts[name]) : [];
  return <section className="evidence-layout" aria-labelledby="m12-evidence-title">
    <h2 id="m12-evidence-title">{t("M12 residual v3.1 · local experiment evidence", "M12 residual v3.1 · evidencia de experimento local")}</h2>
    <p>{t("Choose the three files from one experiment directory. Bytes are read and checked in this browser; no file is uploaded and no network or solver is used.", "Seleccione los tres archivos de un mismo directorio de experimento. Los bytes se leen y verifican en este navegador; no se suben archivos ni se usa red o solver.")}</p>
    <div className="parameter-ledger">
      {FILES.map(name => <label key={name}>{name}<input type="file" accept={name.endsWith(".npz") ? ".npz,application/octet-stream" : ".json,application/json"} aria-label={name} onChange={e => choose(name, e.currentTarget.files?.[0])} /></label>)}
    </div>
    <button className="btn" type="button" onClick={inspect} disabled={busy}>{busy ? t("Checking…", "Verificando…") : t("Inspect local evidence", "Examinar evidencia local")}</button>
    {error && <p role="alert" className="evaluation-status" data-evaluation="failed">{error}</p>}
    {r && <div aria-live="polite">
      <p role="status" className="evaluation-status" data-evaluation="failed"><strong>{t("Scientific outcome: FAILED — held-out comparator", "Resultado científico: FALLÓ — comparador reservado")}</strong></p>
      <p>{t("Manifest agreement establishes file integrity only. It does not authenticate who produced these files.", "La coincidencia del manifiesto solo establece integridad de archivos. No autentica quién los produjo.")}</p>
      <dl className="parameter-ledger">
        <div><dt>{t("Selected epoch", "Época seleccionada")}</dt><dd>{r.selected_epoch} / {r.epochs_run}</dd></div>
        <div><dt>{t("Cohort counts · train / validation / ID / family-only / acquisition-only / joint OOD", "Conteos · entrenamiento / validación / ID / familia / adquisición / OOD conjunto")}</dt><dd>{Object.values(COUNTS).join(" / ")}</dd></div>
        <div><dt>{t("Checkpoint SHA-256 · bytes", "SHA-256 del checkpoint · bytes")}</dt><dd><code>{evidence.checkpointSha256}</code> · {evidence.checkpointBytes}</dd></div>
        <div><dt>{t("CPU/CUDA parity", "Paridad CPU/CUDA")}</dt><dd>{t("Passed", "Aprobada")} · max {r.cpu_cuda_parity.max_abs_m_s} m/s; p99 {r.cpu_cuda_parity.p99_abs_m_s} m/s; mean {r.cpu_cuda_parity.mean_abs_m_s} m/s</dd></div>
      </dl>
      <Plot title={t("Validation history · velocity RMSE", "Historial de validación · RMSE de velocidad")} x={r.history.map((p: Obj) => p.epoch)} xLabel={t("Epoch [1]", "Época [1]")} yLabel="Velocity RMSE [m/s]" series={[{ name: t("Validation", "Validación"), values: r.history.map((p: Obj) => p.validation_velocity_rmse_m_s) }, { name: t("Selected epoch", "Época seleccionada"), values: r.history.map((p: Obj) => p.epoch === r.selected_epoch ? p.validation_velocity_rmse_m_s : Number.NaN), points: true }]} />
      <Plot title={t("Learned / classical error ratios · lower is better", "Razones de error aprendido / clásico · menor es mejor")} x={cohorts.map((_: Obj, i: number) => i + 1)} xLabel={t("Evaluation cohort [1]", "Cohorte de evaluación [1]")} yLabel="Dimensionless ratio [1]" series={[{ name: t("Velocity RMSE ratio", "Razón RMSE de velocidad"), values: cohorts.map((c: Obj) => c.learned_to_classical_velocity_ratio), points: true }, { name: t("Independent oracle travel-time RMSE ratio", "Razón RMSE de tiempo de viaje del oráculo independiente"), values: cohorts.map((c: Obj) => c.learned_to_classical_oracle_ratio), points: true }, { name: t("No difference", "Sin diferencia"), values: cohorts.map(() => 1), dashed: true }]} />
      <ol aria-label={t("Cohort names", "Nombres de cohortes")}>{names.map(n => <li key={n}>{n.replaceAll("_", " ")} — n={r.cohorts[n].count}</li>)}</ol>
      <p className="evaluation-status" data-evaluation="failed"><strong>{t("Joint held-out cohort failed the preregistered comparator.", "La cohorte conjunta reservada falló el comparador preregistrado.")}</strong> {t("Velocity ratio", "Razón de velocidad")} {r.cohorts.joint_ood.learned_to_classical_velocity_ratio}; {t("independent travel-time ratio", "razón de tiempo de viaje independiente")} {r.cohorts.joint_ood.learned_to_classical_oracle_ratio}. {t("Ratios below 1 favor learned; both joint ratios must be below 1 to pass.", "Razones menores que 1 favorecen el método aprendido; ambas razones conjuntas deben ser menores que 1 para aprobar.")}</p>
      <p>{t("Units: velocity RMSE in m/s; independent oracle travel-time RMSE in ms; ratios dimensionless. This bounded synthetic straight-ray experiment is not field validation, ray-bending tomography, or waveform FWI. The learned residual is not an accepted inversion method or a geological probability.", "Unidades: RMSE de velocidad en m/s; RMSE del tiempo de viaje del oráculo independiente en ms; razones adimensionales. Este experimento sintético acotado de rayos rectos no valida datos de campo, tomografía con rayos curvos ni FWI de formas de onda. El residual aprendido no es un método de inversión aceptado ni una probabilidad geológica.")}</p>
      <ul>{r.limitations.map((item: string, i: number) => <li key={i}>{item}</li>)}</ul>
    </div>}
  </section>;
}
