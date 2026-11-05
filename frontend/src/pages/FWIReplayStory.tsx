import { useEffect, useMemo, useState, type ReactNode } from "react";
import { useNavigate, useParams } from "react-router";
import { LinkedViewProvider, SceneCallouts, StoryFrame, useLinkedCursor, useLinkedItem, useShellLang, type StoryStep } from "@fasl-work/caos-app-shell";
import { Plot } from "../components/ScientificPlots";
import { loadArtifact, format } from "../science";

type ReplayRow = {
  case: string;
  variant: string;
  method: string;
  velocity_rmse: number;
  active_wrms: number;
  withheld_wrms: number;
  status: string;
};
type ReplayArtifact = { records: ReplayRow[] };
const artifactPath = "fwi-replay.json";
const sourceLabel = "data/v2/fwi-replay.json · M10";

function LinkedTargets({ side, items }: { side: "scene" | "panel"; items: { id: string; label: string }[] }) {
  return <div className={`fwi-linked-targets fwi-linked-targets-${side}`} aria-label={side === "scene" ? "Selectable plotted results" : "Linked result details"}>
    {items.map(item => <LinkedTarget key={item.id} side={side} item={item} />)}
  </div>;
}

function LinkedTarget({ side, item }: { side: "scene" | "panel"; item: { id: string; label: string } }) {
  const linked = useLinkedItem(item.id, side);
  return <button type="button" {...linked} className="fwi-linked-target">{item.label}</button>;
}

function LinkedScrubber({ side, label }: { side: "scene" | "panel"; label: string }) {
  const linked = useLinkedCursor();
  return <div className={`fwi-linked-scrubber fwi-linked-scrubber-${side}`}>
    <label>{label}<input aria-label={label} type="range" min="0" max="100" step="1" {...linked.inputProps} /></label>
    <span className="fwi-linked-readout" {...linked.markerProps}>{linked.cursor ?? 0}%</span>
  </div>;
}

function findRow(rows: ReplayRow[], variant: string, method = "fwi-l2") {
  const row = rows.find(item => item.case === "FWI_LAYERED" && item.variant === variant && item.method === method);
  if (!row) throw new Error(`The FWI replay artifact is missing ${variant}/${method}.`);
  return row;
}

export default function FWIReplayStory() {
  const { step = "reference" } = useParams();
  const navigate = useNavigate();
  const es = useShellLang() === "es";
  const [artifact, setArtifact] = useState<ReplayArtifact>();
  const [error, setError] = useState("");

  useEffect(() => {
    const controller = new AbortController();
    loadArtifact<ReplayArtifact>(artifactPath, controller.signal)
      .then(setArtifact)
      .catch(reason => { if (reason.name !== "AbortError") setError(String(reason)); });
    return () => controller.abort();
  }, []);

  const steps = useMemo<StoryStep[]>(() => {
    if (!artifact) return [];
    const rows = artifact.records;
    const reference = findRow(rows, "reference");
    const referenceMulti = findRow(rows, "reference", "fwi-multiscale");
    const coverage = findRow(rows, "coverage");
    const regularization = findRow(rows, "regularization");
    const targets = new Set(rows.map(row => row.case)).size;
    const conditions = new Set(rows.map(row => row.variant)).size;
    const coverageIncrease = (coverage.withheld_wrms / reference.withheld_wrms - 1) * 100;
    const regularizationRatio = regularization.velocity_rmse / reference.velocity_rmse;
    const source = (en: string, sp: string) => ({ en, es: sp });
    const stage = (chart: ReactNode, calls: Parameters<typeof SceneCallouts>[0]["items"]) => (
      <div className="caos-story-scene">
        {chart}
        <SceneCallouts items={calls} placement="anchored" />
      </div>
    );
    const callout = (
      id: string,
      en: string,
      sp: string,
      value: string,
      unitEn: string,
      unitEs: string,
      anchor: { x: number; y: number },
      state: "alarm" | "warning" | "normal" | "selected" | "inactive" = "normal",
      trend?: "up" | "down" | "flat",
    ) => ({ id, eyebrow: source(en, sp), value, unit: source(unitEn, unitEs), anchor, state, source: source(sourceLabel, sourceLabel), trend });
    const baseCalls = [
      callout("records", es ? "Registros M10" : "M10 records", "M10", String(rows.length), es ? "filas" : "rows", es ? "filas" : "rows", { x: 0.2, y: 0.72 }, "selected"),
      callout("targets", es ? "Blancos sintéticos" : "Synthetic targets", es ? "casos" : "cases", String(targets), es ? "casos" : "targets", es ? "casos" : "targets", { x: 0.8, y: 0.72 }),
      callout("variants", es ? "Variantes" : "Variants", es ? "adquisición" : "acquisition", String(conditions), es ? "casos" : "cases", es ? "sets" : "sets", { x: 0.5, y: 0.38 }),
    ];
    const steps: StoryStep[] = [
      {
        id: "reference", number: 1, accent: 1, href: "/story/reference",
        verb: source("Read the reference", "Leer la referencia"),
        headline: source(`${rows.length} replays span ${targets} synthetic targets`, `${rows.length} replays cubren ${targets} blancos sintéticos`),
        summary: source("M10 pairs L2 and frequency continuation across four synthetic structures and six acquisition variants.", "M10 compara L2 y continuación de frecuencia en cuatro estructuras sintéticas y seis variantes de adquisición."),
        stage: stage(
          <><Plot fillStage x={[1, 2]} pointLabels={["L2", "Continuation"]} series={[
            { name: es ? "WRMS ajustado" : "Fitted WRMS", values: [reference.active_wrms, referenceMulti.active_wrms], points: true },
            { name: es ? "WRMS retenido" : "Withheld WRMS", values: [reference.withheld_wrms, referenceMulti.withheld_wrms], points: true },
          ]} title={es ? "Caso estratificado · referencia" : "Layered case · reference survey"} xLabel={es ? "Programa de inversión" : "Inversion schedule"} yLabel="WRMS" /><LinkedTargets side="scene" items={[{ id: "fit", label: es ? "Ajustado" : "Fitted" }, { id: "holdout", label: es ? "Retenido" : "Withheld" }]} /><LinkedScrubber side="scene" label={es ? "Índice del replay" : "Replay index"} /></>,
          baseCalls,
        ),
        panel: <section><h2>{es ? "Qué contiene el benchmark" : "What the benchmark contains"}</h2><p>{es ? `El archivo contiene ${rows.length} registros, ${targets} geometrías y ${conditions} condiciones. En la referencia estratificada, L2 y continuación se comparan con el mismo objetivo sintético.` : `The artifact contains ${rows.length} records, ${targets} geometries, and ${conditions} conditions. In the layered reference, L2 and continuation are compared against the same synthetic target.`}</p><p>{es ? `WRMS ajustado: ${format(reference.active_wrms)} (L2), ${format(referenceMulti.active_wrms)} (continuación). WRMS retenido: ${format(reference.withheld_wrms)} y ${format(referenceMulti.withheld_wrms)}.` : `Fitted WRMS: ${format(reference.active_wrms)} (L2), ${format(referenceMulti.active_wrms)} (continuation). Withheld WRMS: ${format(reference.withheld_wrms)} and ${format(referenceMulti.withheld_wrms)}.`}</p><LinkedTargets side="panel" items={[{ id: "fit", label: es ? "Seleccionar métricas ajustadas" : "Select fitted metrics" }, { id: "holdout", label: es ? "Seleccionar métricas retenidas" : "Select withheld metrics" }]} /><LinkedScrubber side="panel" label={es ? "Índice compartido del replay" : "Shared replay index"} /><p>{es ? "La unidad es el WRMS normalizado del artefacto; no es un error de velocidad ni una medición de campo." : "Values are the artifact’s normalized WRMS; they are neither velocity error nor field measurements."}</p><a href="/data/v2/fwi-replay.json">{es ? "Descargar artefacto de replay" : "Open replay source artifact"}</a></section>,
      },
      {
        id: "coverage", number: 2, accent: 2, href: "/story/coverage",
        verb: source("Remove observations", "Quitar observaciones"),
        headline: source(`Coverage loss raises withheld WRMS ${format(coverageIncrease)}%`, `Menos cobertura eleva WRMS retenido ${format(coverageIncrease)}%`),
        summary: source("Withheld receivers test transfer beyond the reduced acquisition coverage.", "Los receptores retenidos prueban la transferencia con cobertura de adquisición reducida."),
        stage: stage(
          <><Plot fillStage x={[1, 2]} pointLabels={["Reference", "Coverage"]} series={[
            { name: es ? "WRMS ajustado" : "Fitted WRMS", values: [reference.active_wrms, coverage.active_wrms], points: true },
            { name: es ? "WRMS retenido" : "Withheld WRMS", values: [reference.withheld_wrms, coverage.withheld_wrms], points: true },
          ]} title={es ? "Receptores usados y retenidos" : "Used and withheld receivers"} xLabel={es ? "Condición de observación" : "Observation condition"} yLabel="WRMS" /><LinkedTargets side="scene" items={[{ id: "coverage-base", label: es ? "Base" : "Baseline" }, { id: "coverage-test", label: es ? "Cobertura" : "Coverage" }]} /><LinkedScrubber side="scene" label={es ? "Índice del replay" : "Replay index"} /></>,
          [
            callout("reference-holdout", es ? "Retenido · base" : "Holdout · base", "WRMS", format(reference.withheld_wrms), "WRMS", "WRMS", { x: 0.16, y: 0.64 }),
            callout("coverage-holdout", es ? "Retenido · cobertura" : "Holdout · coverage", "WRMS", format(coverage.withheld_wrms), "WRMS", "WRMS", { x: 0.88, y: 0.34 }, "warning", "up"),
            callout("coverage-change", es ? "Cambio" : "Change", "%", `${format(coverageIncrease)}%`, es ? "vs. base" : "vs. baseline", es ? "vs. base" : "vs. baseline", { x: 0.52, y: 0.82 }, "warning", "up"),
          ],
        ),
        panel: <section><h2>{es ? "El ajuste no resume la transferencia" : "Fit does not summarize transfer"}</h2><p>{es ? `WRMS retenido aumenta de ${format(reference.withheld_wrms)} a ${format(coverage.withheld_wrms)} (${format(coverageIncrease)}%). El WRMS ajustado cambia de ${format(reference.active_wrms)} a ${format(coverage.active_wrms)}.` : `Withheld WRMS rises from ${format(reference.withheld_wrms)} to ${format(coverage.withheld_wrms)} (${format(coverageIncrease)}%). Fitted WRMS changes from ${format(reference.active_wrms)} to ${format(coverage.active_wrms)}.`}</p><p>{es ? "La comparación usa las filas reference y coverage del mismo caso y del método fwi-l2. El conjunto retenido evalúa receptores excluidos del ajuste según el protocolo del artefacto." : "This compares the reference and coverage rows for the same case and fwi-l2 method. The withheld set evaluates receivers excluded from fitting under the artifact protocol."}</p><LinkedTargets side="panel" items={[{ id: "coverage-base", label: es ? "Seleccionar base" : "Select baseline" }, { id: "coverage-test", label: es ? "Seleccionar cobertura" : "Select coverage" }]} /><LinkedScrubber side="panel" label={es ? "Índice compartido del replay" : "Shared replay index"} /><p>{es ? "Es evidencia de un benchmark sintético; no estima desempeño en una adquisición natural." : "This is evidence from a synthetic benchmark; it does not estimate performance on a natural survey."}</p><a href="/data/v2/fwi-replay.json">{es ? "Abrir artefacto de replay" : "Open replay source artifact"}</a></section>,
      },
      {
        id: "regularization", number: 3, accent: 3, href: "/story/regularization",
        verb: source("Inspect the failed control", "Inspeccionar el control fallido"),
        headline: source(`Regularization raises model RMSE ${format(regularizationRatio)}×`, `Regularización eleva RMSE del modelo ${format(regularizationRatio)}×`),
        summary: source("An adverse regularization control remains a recorded negative result.", "El control de regularización adverso se conserva como resultado negativo."),
        stage: stage(
          <><Plot fillStage x={[1, 2]} pointLabels={["Reference", "Regularization"]} series={[
            { name: es ? "RMSE velocidad" : "Velocity RMSE", values: [reference.velocity_rmse, regularization.velocity_rmse], points: true },
          ]} title={es ? "RMSE contra verdad sintética" : "RMSE against synthetic truth"} xLabel={es ? "Condición" : "Condition"} yLabel="Velocity RMSE (m/s)" /><LinkedTargets side="scene" items={[{ id: "rmse-reference", label: es ? "Referencia" : "Reference" }, { id: "rmse-control", label: es ? "Control" : "Control" }]} /><LinkedScrubber side="scene" label={es ? "Índice del replay" : "Replay index"} /></>,
          [
            callout("reference-rmse", es ? "RMSE · base" : "RMSE · baseline", "m/s", format(reference.velocity_rmse), "m/s", "m/s", { x: 0.14, y: 0.8 }),
            callout("regularization-rmse", es ? "RMSE · control" : "RMSE · control", "m/s", format(regularization.velocity_rmse), "m/s", "m/s", { x: 0.9, y: 0.18 }, "alarm", "up"),
            callout("control-status", es ? "Estado" : "Status", es ? "resultado" : "outcome", regularization.status, es ? "artefacto" : "artifact", es ? "estado" : "state", { x: 0.54, y: 0.58 }, "alarm"),
          ],
        ),
        panel: <section><h2>{es ? "Un control negativo útil" : "A useful negative control"}</h2><p>{es ? `El RMSE de velocidad aumenta de ${format(reference.velocity_rmse)} a ${format(regularization.velocity_rmse)} m/s, un factor de ${format(regularizationRatio)}. El WRMS ajustado/retenido del control es ${format(regularization.active_wrms)} / ${format(regularization.withheld_wrms)}; el estado guardado es “${regularization.status}”.` : `Velocity RMSE rises from ${format(reference.velocity_rmse)} to ${format(regularization.velocity_rmse)} m/s, a factor of ${format(regularizationRatio)}. The control’s fitted/withheld WRMS is ${format(regularization.active_wrms)} / ${format(regularization.withheld_wrms)}; its recorded status is “${regularization.status}”.`}</p><p>{es ? "La verdad solo se consulta después de invertir porque el experimento es sintético. El fallo muestra sensibilidad a la regularización y limita cualquier afirmación general sobre el método." : "Truth is consulted only after inversion because this experiment is synthetic. The failure exposes regularization sensitivity and limits any general claim about the method."}</p><LinkedTargets side="panel" items={[{ id: "rmse-reference", label: es ? "Seleccionar referencia" : "Select reference" }, { id: "rmse-control", label: es ? "Seleccionar control" : "Select control" }]} /><LinkedScrubber side="panel" label={es ? "Índice compartido del replay" : "Shared replay index"} /><a href="/data/v2/fwi-replay.json">{es ? "Abrir artefacto de replay" : "Open replay source artifact"}</a> · <a href="https://github.com/fsantibanezleal/CAOS_Geophysics/blob/main/notebooks/en/06-seismology/05-m10-fwi-case-matrix.ipynb" target="_blank" rel="noreferrer">{es ? "Notebook M10" : "M10 notebook"}</a></section>,
      },
    ];
    return steps;
  }, [artifact, es]);

  if (error) return <div className="page-body" role="alert"><h1>{es ? "No se pudo cargar la evidencia M10" : "M10 evidence could not be loaded"}</h1><p>{error}</p></div>;
  if (!artifact) return <div className="page-body" role="status" aria-live="polite">{es ? "Cargando resultados M10…" : "Loading M10 results…"}</div>;
  const activeId = steps.some(item => item.id === step) ? step : "reference";
  return <LinkedViewProvider initial={{ selectedId: step === "coverage" ? "coverage-base" : step === "regularization" ? "rmse-reference" : "fit", cursor: 0 }}><StoryFrame
    steps={steps}
    activeId={activeId}
    onStepChange={id => navigate(`/story/${id}`)}
    onExit={() => navigate("/experiments")}
    labels={{ steps: es ? "Lectura del experimento" : "Experiment walkthrough", previous: es ? "Anterior" : "Previous", next: es ? "Siguiente" : "Next", play: es ? "Reproducir" : "Play", pause: es ? "Pausar" : "Pause", exit: es ? "Volver a experimentos" : "Back to experiments" }}
    autoAdvanceMs={8000}
    className="geophysics-fwi-story"
  /></LinkedViewProvider>;
}
