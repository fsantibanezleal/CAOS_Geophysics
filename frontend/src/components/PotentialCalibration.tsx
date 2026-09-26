import { useShellLang } from "@fasl-work/caos-app-shell";
import calibrationJson from "../../../docs/validation/spatial-calibration.json?raw";
import { format } from "../science";

// Read the independent numerical report at build time; no frontend-fitted constants.
const report = JSON.parse(calibrationJson) as {
  schema: string; test_count: number; bootstrap_members: number;
  test_seed: number; test_noise_seed: number;
  mean_pointwise_coverage: number; mean_support_coverage: number;
  claim: string;
};

export function PotentialCalibration() {
  const es = useShellLang() === "es";
  const t = (en: string, sp: string) => es ? sp : en;
  if (report.schema !== "inverse-earth.prior-calibration/v1") return <p role="alert">{t("Independent calibration report is unavailable.", "Informe de calibración independiente no disponible.")}</p>;
  return <aside className="evaluation-status" data-evaluation="failed">
    <strong>{t("Independent gravity interval test: ", "Prueba independiente de intervalos gravimétricos: ")}{format(100 * report.mean_pointwise_coverage)}% {t("pointwise coverage; nominal 95% intervals.", "cobertura puntual; intervalos nominales 95%.")}</strong>
    <p>{report.test_count} {t("withheld synthetic models", "modelos sintéticos omitidos")}; {report.bootstrap_members} {t("conditional noise members per model", "miembros condicionales de ruido por modelo")}. {t("Mean target-support coverage", "Cobertura media del soporte objetivo")}: {format(100 * report.mean_support_coverage)}%. {t("Model / noise seeds", "Semillas de modelo / ruido")}: {report.test_seed} / {report.test_noise_seed}.</p>
    <p>{t("The intervals fail to cover the synthetic density target at their nominal level. They measure conditional estimator repeatability, excluding regularization bias and geological ambiguity. This is negative evidence for interpreting the bands as calibrated geological uncertainty, not a posterior result or a calibration of MT intervals.", "Los intervalos no cubren el objetivo de densidad al nivel nominal. Miden repetibilidad condicional del estimador, excluyendo sesgo de regularización y ambigüedad geológica. Es evidencia negativa para interpretarlos como incertidumbre geológica calibrada, no un resultado posterior ni calibración de intervalos MT.")}</p>
    <a href="https://github.com/fsantibanezleal/CAOS_Geophysics/blob/main/docs/validation/spatial-calibration.json">{t("Independent calibration record", "Registro de calibración independiente")}</a>
  </aside>;
}
