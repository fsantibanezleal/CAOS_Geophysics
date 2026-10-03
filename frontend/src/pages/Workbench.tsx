import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router";
import {
  Download,
  Pause,
  Play,
  RotateCcw,
  ChevronRight,
  ChevronLeft,
} from "lucide-react";
import { Tabs, useShellLang } from "@fasl-work/caos-app-shell";
import { EarthScene } from "../components/EarthScene";
import {
  Heatmap,
  LayerColumn,
  Legend,
  Plot,
} from "../components/ScientificPlots";
import {
  extent,
  familyLabels,
  flatten,
  format,
  loadArtifact,
  sliceVolume,
  type Catalog,
  type Curves,
  type Run,
} from "../science";
import { methodName, metricInfo, historyInfo } from "../data/metrics";
import { lessons } from "../data/lessons";
import { absoluteThreshold, casePropertyScale, physicalTarget, selectedModel, sharedScale, type ModelState } from "../recovery";
import { ApplicabilityWarning, DetectionEvidence, EvidenceMetrics, EvaluationStatus, PetrophysicalView, TargetEvidence, UncertaintyView } from "../components/ScientificEvidence";
import { provenanceDescription } from "../data/evidence";
import { deploymentMode } from "../lib/deployment";
import { ProjectDrawer } from "../components/ProjectDrawer";
import { ProjectProcessingWorkbench } from "../components/ProjectProcessingWorkbench";

const matrix = (v: number[], rows = 16, cols = 16) =>
  Array.from({ length: rows }, (_, i) => v.slice(i * cols, (i + 1) * cols));
const transpose = (v: number[][]) => v[0].map((_, j) => v.map((row) => row[j]));
const indices = (n: number) => Array.from({ length: n }, (_, i) => i);
const signed = (v: number[]): [number, number] => {
  const bounds = extent(v);
  const m = Math.max(Math.abs(bounds[0]), Math.abs(bounds[1]), 1e-12);
  return [-m, m];
};
function Range({
  label,
  value,
  min,
  max,
  step = 1,
  onChange,
  unit = "",
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step?: number;
  onChange: (v: number) => void;
  unit?: string;
}) {
  return (
    <label className="range-control">
      <span>
        {label}
        <output>
          {format(value)} {unit}
        </output>
      </span>
      <input
        aria-label={label}
        type="range"
        className="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(+e.target.value)}
      />
    </label>
  );
}

export default function Workbench() {
  const es = useShellLang() === "es";
  const t = (a: string, b: string) => (es ? b : a);
  const [catalog, setCatalog] = useState<Catalog>();
  const [selected, setSelected] = useState("GRAVITY_INTRUSION");
  const [variant, setVariant] = useState("reference");
  const [run, setRun] = useState<Run>();
  const [methodId, setMethodId] = useState("irls");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [mode, setMode] = useState("recovered");
  const [section, setSection] = useState(12);
  const [cut, setCut] = useState(960);
  const [representation, setRepresentation] = useState<"surface" | "cells">(
    "surface",
  );
  const [threshold, setThreshold] = useState<number | null>(null);
  const [opacity, setOpacity] = useState(1);
  const [survey, setSurvey] = useState(true);
  const [angle, setAngle] = useState(0);
  const [angleStep, setAngleStep] = useState(15);
  const [speed, setSpeed] = useState(8);
  const [orbit, setOrbit] = useState(false);
  const [reset, setReset] = useState(0);
  const [frame, setFrame] = useState(0);
  const [modelState, setModelState] = useState<ModelState>("final");
  const [playing, setPlaying] = useState(false);
  const [blend, setBlend] = useState(0);
  const [shot, setShot] = useState(1);
  const [controlsOpen, setControlsOpen] = useState(false);
  const [sidebarPanel, setSidebarPanel] = useState<"experiment" | "replay" | "evidence">("experiment");
  const [projectsOpen, setProjectsOpen] = useState(false);
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedProjectId = searchParams.get("project") ?? "";
  const processingProjectId = deploymentMode === "single-origin" && /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(requestedProjectId) ? requestedProjectId : "";
  const selectProcessingProject = (id: string) => {
    setSearchParams(current => {
      const next = new URLSearchParams(current);
      if (id) next.set("project", id); else next.delete("project");
      return next;
    }, {replace: true});
    if (id) { setOrbit(false); setPlaying(false); }
  };
  const projectLauncher = useRef<HTMLButtonElement>(null);
  const closeProjects = () => {
    setProjectsOpen(false);
    window.requestAnimationFrame(() => projectLauncher.current?.focus());
  };
  const [gain, setGain] = useState(8);
  const [playbackKind, setPlaybackKind] = useState("inverse");
  useEffect(() => {
    const controller = new AbortController();
    loadArtifact<Catalog>("catalog.json", controller.signal)
      .then(setCatalog)
      .catch((e) => {
        if (e.name !== "AbortError") setError(String(e));
      });
    return () => controller.abort();
  }, []);
  const entry = catalog?.cases.find((c) => c.id === selected);
  const artifact = entry?.variants.find((v) => v.id === variant) ?? entry?.variants[0];
  useEffect(() => {
    if (!artifact) return;
    const controller = new AbortController();
    setLoading(true);
    setModelState("final");
    setPlaybackKind("inverse");
    setError("");
    setPlaying(false);
    setFrame(0);
    loadArtifact<Run>(artifact.path, controller.signal)
      .then((r) => {
        setRun(r);
        const preferred = {
          gravity: "irls",
          magnetics: "l2",
          mt: "mt-lm",
          seismic: "fwi-multiscale",
          joint: "joint",
          learned: selected === "LEARNED_AUTOENCODER" ? "autoencoder" : "cnn",
        }[r.family];
        const nextId =
          run?.id === r.id && r.methods[methodId] ? methodId : r.methods[preferred] ? preferred : Object.keys(r.methods)[0];
        setMethodId(nextId);
        setFrame(0);
        setLoading(false);
      })
      .catch((e) => {
        if (e.name !== "AbortError") {
          setError(String(e));
          setLoading(false);
        }
      });
    return () => controller.abort();
  }, [artifact, selected]);
  const method = run?.methods[methodId] ?? Object.values(run?.methods ?? {})[0];
  const count =
    run?.family === "seismic" && playbackKind === "wave"
      ? (run.wavefields?.length ?? 0)
      : (method?.frames.length ?? 0);
  useEffect(() => {
    if (!playing || count < 2) {
      setBlend(0);
      return;
    }
    if (run?.family === "seismic" && playbackKind === "wave") {
      const start = performance.now(),
        initial = frame;
      let handle = 0,
        last = 0;
      const tick = (now: number) => {
        if (now - last >= 32) {
          const progress = initial + (now - start) / 120;
          const current = Math.floor(progress) % count;
          setFrame(current);
          setBlend(current === count - 1 ? 0 : progress % 1);
          last = now;
        }
        handle = requestAnimationFrame(tick);
      };
      handle = requestAnimationFrame(tick);
      return () => cancelAnimationFrame(handle);
    }
    const id = setInterval(() => setFrame((f) => (f + 1) % count), 120);
    return () => clearInterval(id);
  }, [playing, count, run?.family, playbackKind]);
  const waveRange = useMemo(
    () =>
      run?.wavefields
        ? signed(run.wavefields.flat(2))
        : ([-1, 1] as [number, number]),
    [run],
  );
  const comparisonScale = useMemo(() => {
    if (!run || !method) return sharedScale([]);
    return casePropertyScale(run, methodId, entry?.display_scales);
  }, [run, methodId, method, entry]);
  const thresholdGroup = methodId === "vector" ? "vector-amplitude" : "volume";
  const displayThreshold = threshold === null
    ? entry?.default_thresholds?.[thresholdGroup] ?? absoluteThreshold(comparisonScale, 0.35)
    : absoluteThreshold(comparisonScale, threshold);
  const displayedModel = useMemo(() => method ? selectedModel(method, modelState, frame) : [], [method, modelState, frame]);
  const values = useMemo(() => !run ? [] : flatten(mode === "truth" ? physicalTarget(run, methodId) : displayedModel), [run, displayedModel, mode, methodId]);
  const returnToFinal = () => {
    setModelState("final"); setPlaying(false); setPlaybackKind("inverse"); setMode("recovered");
  };
  const displayedState = modelState === "final"
    ? t("Selected final model", "Modelo final seleccionado")
    : t("Model replay · saved state", "Reproducción del modelo · estado guardado") + " " + (frame + 1);
  const pickCell = useCallback(
    (i: number) => {
      if (run?.grid)
        setSection(Math.floor(i / run.grid.shape[2]) % run.grid.shape[1]);
    },
    [run],
  );
  const select = (id: string) => {
    setSelected(id);
    setControlsOpen(false);
    setSidebarPanel("experiment");
    setVariant("reference");
    setMode("recovered");
    setModelState("final");
    setPlaybackKind("inverse");
    setFrame(0);
    setReset((n) => n + 1);
    setCut(960);
    setThreshold(null);
    setPlaying(false);
  };
  const lesson = lessons[selected];
  const lang = es ? 1 : 0;
  const physical =
    (run && ["gravity", "magnetics", "joint"].includes(run.family)) ||
    (run?.family === "learned" && ["l2", "irls"].includes(methodId));
  const exportRun = () => {
    if (!run) return;
    const url = URL.createObjectURL(
      new Blob([JSON.stringify(run)], { type: "application/json" }),
    );
    const link = document.createElement("a");
    link.href = url;
    link.download = `${run.id}-${variant}.json`;
    link.click();
    URL.revokeObjectURL(url);
  };
  let earth: React.ReactNode = null,
    measurements: React.ReactNode = null,
    recovery: React.ReactNode = null;
  if (run && method) {
    const final = flatten(method.model);
    const truth = flatten(physicalTarget(run, methodId));
    const h = historyInfo(methodId, es);
    const history = (
      <div className="convergence-panel">
        <Plot
          title={h.label}
          x={method.history_indices ?? method.states?.map(s => s.step) ?? indices(method.history.length).map((i) => i * h.stride)}
          series={[{ name: h.label, values: method.history }]}
          xLabel={h.axis}
          yLabel={h.label + " · 1"}
          logY={method.history.every((v) => v > 0)}
        />
        <div className="metric-grid">
          {Object.entries(method.metrics).map(([key, value]) => (
            <div
              key={key}
              title={metricInfo(key, run.family, methodId, es).description}
            >
              <span>{metricInfo(key, run.family, methodId, es).label}</span>
              <strong>
                {typeof value === "boolean"
                  ? value
                    ? t("Yes", "Sí")
                    : t("No", "No")
                  : value == null ? t("Unavailable", "No disponible") : format(value)}{" "}
                {metricInfo(key, run.family, methodId, es).unit}
              </strong>
            </div>
          ))}
        </div>
        <p className="plot-note">{h.description}</p>
        <p className="plot-note">
          {t(
            "Metrics describe the final selected solution, not the replay frame. Lower data error does not guarantee correct geology.",
            "Las métricas describen la solución final, no el cuadro reproducido. Menor error de datos no garantiza geología correcta.",
          )}
        </p>
      </div>
    );
    if (physical && run.grid && run.survey) {
      const s = run.survey;
      const bounds = sharedScale([s.observed, ...Object.values(run.methods).flatMap(m => Array.isArray(m.predicted) && !Array.isArray(m.predicted[0]) ? [m.predicted as number[]] : [])], true).range;
      const predicted = method.predicted as number[];
      earth = (
        <div className="earth-view">
          <div className="scene-toolbar">
            <div className="segmented">
              <button
                className={`chip ${mode === "truth" ? "on" : ""}`}
                onClick={() => { setMode("truth"); setPlaying(false); }}
              >
                {t("Synthetic target", "Objetivo sintético")}
              </button>
              <button
                className={`chip ${mode === "recovered" ? "on" : ""}`}
                onClick={() => {
                  setMode("recovered");
                  returnToFinal();
                }}
              >
                {t("Final model", "Modelo final")}
              </button>
            </div>
            <label>
              <input
                type="checkbox"
                checked={survey}
                onChange={(e) => setSurvey(e.target.checked)}
              />
              {t("Survey plane", "Plano de medición")}
            </label>
            <button
              className="btn text-button"
              onClick={() => setOrbit((v) => !v)}
            >
              {orbit ? <Pause size={14} /> : <Play size={14} />}{" "}
              {t("Orbit", "Orbitar")}
            </button>
          </div>
          <EarthScene
            run={run}
            values={values}
            opacity={opacity}
            cut={cut}
            showSurvey={survey}
            surveyMaxAbs={entry?.survey_max_abs}
            angle={angle}
            speed={speed}
            playing={orbit}
            reset={reset}
            label={
              mode === "truth"
                ? t("Synthetic target", "Objetivo sintético")
                : displayedState
            }
            onCell={pickCell}
            representation={representation}
            threshold={displayThreshold}
            range={comparisonScale.range}
          />
          <div className="scene-bottom">
            <Legend
              range={comparisonScale.range}
              unit={method.target?.units ?? run.units}
              palette={comparisonScale.signed ? "field" : "earth"}
            />
            <span>
              {run.grid.shape.slice().reverse().join(" × ")} {t("computed cells", "celdas calculadas")}; Δx, Δy, Δz = {run.grid.spacing.join(", ")} m.{" "}
              {entry?.display_scales ? t(
                "Model colours and the reference-inverse display threshold are fixed across six conditions for each property; the threshold is adjustable. Interpolated surfaces add no resolution.",
                "El color y el umbral de visualización derivado de la inversión de referencia son fijos entre seis condiciones para cada propiedad; el umbral es ajustable. Las superficies interpoladas no agregan resolución.",
              ) : t(
                "Fixed colour scale and absolute threshold across target, methods and saved states. A surface interpolates computed cells; it does not add resolution.",
                "Escala y umbral absoluto fijos entre objetivo, métodos y estados. La superficie interpola celdas calculadas; no agrega resolución.",
              )}
              {survey && entry?.survey_max_abs ? ` ${t("Survey colours", "Colores del levantamiento")} ±${format(entry.survey_max_abs)} ${run.data_units}.` : ""}
            </span>
          </div>
          <details className="scene-settings">
            <summary>
              {t(
                "View controls: threshold, cut and rotation",
                "Controles de vista: umbral, corte y rotación",
              )}
            </summary>
            <div className="scene-adjustments">
              <label className="select-control">
                <span>{t("Representation", "Representación")}</span>
                <select
                  className="select"
                  aria-label={t("Representation", "Representación")}
                  value={representation}
                  onChange={(e) =>
                    setRepresentation(e.target.value as "surface" | "cells")
                  }
                >
                  <option value="surface">
                    {t("Isosurfaces", "Isosuperficies")}
                  </option>
                  <option value="cells">
                    {t("Computed cells", "Celdas calculadas")}
                  </option>
                </select>
              </label>
              <Range
                label={t("Property threshold", "Umbral de propiedad")}
                value={displayThreshold}
                min={0}
                max={comparisonScale.maximum || 1}
                step={(comparisonScale.maximum || 1) / 100}
                unit={method.target?.units ?? run.units}
                onChange={(v) => setThreshold(v / (comparisonScale.maximum || 1))}
              />
              <Range
                label={t("Northing cut", "Corte norte")}
                value={cut}
                min={-960}
                max={960}
                step={80}
                unit="m"
                onChange={setCut}
              />
              <Range
                label={t("Opacity", "Opacidad")}
                value={opacity}
                min={0.2}
                max={1}
                step={0.05}
                onChange={setOpacity}
              />
              <Range
                label={t("Orbit speed", "Velocidad orbital")}
                value={speed}
                min={1}
                max={24}
                unit="°/s"
                onChange={setSpeed}
              />
              <div className="angle-control">
                <Range
                  label={t("Angle step", "Paso angular")}
                  value={angleStep}
                  min={1}
                  max={90}
                  unit="°"
                  onChange={setAngleStep}
                />
                <button
                  className="btn"
                  aria-label={t("Rotate left", "Girar izquierda")}
                  onClick={() => setAngle((v) => (v - angleStep + 360) % 360)}
                >
                  <ChevronLeft size={16} />
                </button>
                <button
                  className="btn"
                  aria-label={t("Rotate right", "Girar derecha")}
                  onClick={() => setAngle((v) => (v + angleStep) % 360)}
                >
                  <ChevronRight size={16} />
                </button>
              </div>
            </div>
          </details>
        </div>
      );
      measurements = (
        <div className="evidence-layout">
          <div className="three-plots">
            {[
              [s.observed, t("Observed field", "Campo observado")],
              [predicted, t("Final-model predicted field", "Campo predicho por el modelo final")],
              [
                method.residual as number[],
                t("Data residual", "Residuo de datos"),
              ],
            ].map(([data, title], i) => (
              <Heatmap
                key={i}
                title={title as string}
                data={matrix(data as number[])}
                range={bounds}
                unit={run.data_units}
                xLabel={t("Easting · m", "Este · m")}
                yLabel={t("Northing · m", "Norte · m")}
                xRange={[-1120, 1120]}
                yRange={[-960, 960]}
              />
            ))}
          </div>
          <Plot
            title={t(
              "Central survey line · shared scale",
              "Línea central · escala compartida",
            )}
            x={s.locations.slice(128, 144).map((p) => p[0])}
            series={[
              {
                name: t("Observed", "Observado"),
                values: s.observed.slice(128, 144),
                points: true,
              },
              {
                name: t("Predicted", "Predicho"),
                values: predicted.slice(128, 144),
              },
            ]}
            xLabel={t("Easting · m", "Este · m")}
            yLabel={run.data_units}
          />
          <p className="plot-note">
            {t(
              "Survey markers identify active stations. Coverage experiments fit alternate stations; predictions at omitted stations remain visible.",
              "Los marcadores identifican estaciones activas. Los experimentos de cobertura ajustan estaciones alternas; las predicciones en estaciones omitidas siguen visibles.",
            )}
          </p>
        </div>
      );
      recovery = (
        <div className="evidence-layout">
          <Range
            label={t("Northing section", "Sección norte")}
            value={section}
            min={0}
            max={run.grid.shape[1] - 1}
            onChange={setSection}
          />
          <div className="two-plots">
            {[
              [truth, t("Known section", "Sección conocida")],
              [final, t("Recovered section", "Sección recuperada")],
            ].map(([v, title], i) => (
              <Heatmap
                key={i}
                data={sliceVolume(v as number[], run.grid!.shape, section)}
                title={title as string}
                unit={run.units}
                range={comparisonScale.range}
                xLabel={t("Easting · m", "Este · m")}
                yLabel={t("Depth · m", "Profundidad · m")}
                xRange={[-1120, 1120]}
                yRange={[0, 1120]}
              />
            ))}
          </div>
          {run.family === "joint" && <PetrophysicalView run={run} methodId={methodId} section={section} caseRange={entry?.display_scales?.secondary?.range} />}
          {history}
        </div>
      );
    } else if (run.family === "mt") {
      const obs = run.observed as Curves,
        fit = method.predicted as Curves;
      const f = run.frequencies!;
      const resistivityRange = extent([truth, ...Object.values(run.methods).flatMap(m => [flatten(m.model), ...m.frames.map(flatten)])].flat().filter(v => v > 0).map(Math.log10));
      const curves = (
        key: keyof Curves,
        title: string,
        unit: string,
        logY = false,
      ) => (
        <Plot
          title={title}
          x={f}
          series={[
            {
              name: t("Observed", "Observado"),
              values: obs[key],
              points: true,
            },
            { name: t("Fitted", "Ajustado"), values: fit[key] },
          ]}
          xLabel={t("Frequency · Hz", "Frecuencia · Hz")}
          yLabel={unit}
          logX
          logY={logY}
        />
      );
      earth = (
        <div className="mt-view">
          <div className="mt-column">
            <LayerColumn
              rho={flatten(displayedModel)}
              thickness={run.thickness!}
              range={resistivityRange}
              title={displayedState}
            />
            <p className="plot-note">
              {t(
                "Known layer thicknesses. Bottom layer is a half-space; its drawn height is symbolic.",
                "Espesores conocidos. La capa inferior es un semiespacio; su altura dibujada es simbólica.",
              )}
            </p>
          </div>
          <div className="mt-curves">
            {curves(
              "apparent",
              t("Apparent resistivity", "Resistividad aparente"),
              "Ω m",
              true,
            )}
            {curves("phase", t("Impedance phase", "Fase de impedancia"), "°")}
            <p className="plot-note">
              {t(
                "Impedance curves and metrics always use the selected final model. Model replay changes only the layer column; no replay-frame predictions are claimed.",
                "Las curvas de impedancia y métricas siempre usan el modelo final seleccionado. La reproducción sólo cambia la columna; no se muestran predicciones del cuadro.",
              )}
            </p>
          </div>
        </div>
      );
      measurements = (
        <div className="two-plots">
          {curves("real", t("Real impedance", "Impedancia real"), "Ω")}
          {curves(
            "imag",
            t("Imaginary impedance", "Impedancia imaginaria"),
            "Ω",
          )}
        </div>
      );
      recovery = (
        <div className="evidence-layout">
          <div className="two-columns">
            <LayerColumn
              rho={truth}
              thickness={run.thickness!}
              range={resistivityRange}
              title={t("Known resistivities", "Resistividades conocidas")}
            />
            <LayerColumn
              rho={final}
              thickness={run.thickness!}
              range={resistivityRange}
              title={t("Recovered resistivities", "Resistividades recuperadas")}
            />
          </div>
          {history}
        </div>
      );
    } else if (run.family === "seismic") {
      const obs = run.observed as number[][][],
        pred = method.predicted as number[][][],
        res = method.residual as number[][][];
      const [nz, nx] = run.grid!.shape;
      const dx = run.grid!.spacing[0];
      const seismicX: [number, number] = [-dx / 2, (nx - 0.5) * dx];
      const seismicY: [number, number] = [-dx / 2, (nz - 0.5) * dx];
      const gather = obs[Math.min(shot, obs.length - 1)];
      const nt = gather[0].length;
      const time = indices(nt).map((i) => i * run.dt!);
      const savedWave =
        playbackKind === "wave"
          ? run.wavefields![Math.min(frame, count - 1)]
          : (displayedModel as number[][]);
      const wave =
        playbackKind === "wave" && playing && blend > 0
          ? savedWave.map((row, y) =>
              row.map(
                (v, x) =>
                  v * (1 - blend) +
                  run.wavefields![Math.min(frame + 1, count - 1)][y][x] * blend,
              ),
            )
          : savedWave;
      const fullWaveRange = waveRange;
      const wr: [number, number] = [
        fullWaveRange[0] / gain,
        fullWaveRange[1] / gain,
      ];
      const bounds = comparisonScale.range;
      const vel = (data: number[][], title: string) => (
        <Heatmap
          data={data}
          title={title}
          palette="velocity"
          range={bounds}
          unit="m/s"
          xLabel={t("Distance · m", "Distancia · m")}
          yLabel={t("Depth · m", "Profundidad · m")}
          xRange={seismicX}
          yRange={seismicY}
        />
      );
      const gatherPlot = (data: number[][], title: string) => (
        <Heatmap
          data={transpose(data)}
          title={title}
          unit={t("relative amplitude", "amplitud relativa")}
          range={signed(gather.flat()).map((v) => v / gain) as [number, number]}
          cursorY={
            playbackKind === "wave"
              ? ((frame + blend) * run.wavefield_dt! + run.dt! / 2) /
                (nt * run.dt!)
              : undefined
          }
          xLabel={t("Receiver position · m", "Posición receptor · m")}
          yLabel={t("Time · s", "Tiempo · s")}
          xRange={[75, 1500]}
          yRange={[-run.dt! / 2, (nt - 0.5) * run.dt!]}
          xCoordinates={run.receivers}
          yCoordinates={time}
        />
      );
      earth = (
        <div className="seismic-view">
          <div className="wave-stage">
            <Heatmap
              data={wave}
              title={
                playbackKind === "wave"
                  ? t(
                      "Propagating wave · central shot",
                      "Onda propagándose · disparo central",
                    )
                  : t(
                      "Velocity update · inversion replay",
                      "Actualización de velocidad · inversión",
                    )
              }
              unit={
                playbackKind === "wave"
                  ? t("relative pressure", "presión relativa")
                  : "m/s"
              }
              range={playbackKind === "wave" ? wr : bounds}
              palette={playbackKind === "wave" ? "field" : "velocity"}
              boundaries={run.truth as number[][]}
              xLabel={t("Distance · m", "Distancia · m")}
              yLabel={t("Depth · m", "Profundidad · m")}
              xRange={seismicX}
              yRange={seismicY}
              markers={[
                {
                  x: (run.sources![1][0] + dx / 2) / (nx * dx),
                  y: (run.sources![1][1] + dx / 2) / (nz * dx),
                  label: "S₂",
                },
              ]}
            />
            <div className="wave-clock">
              <strong>
                {playbackKind === "wave"
                  ? ((frame + blend) * run.wavefield_dt!).toFixed(3)
                  : modelState === "final" ? method.state_identity?.selected_iteration ?? t("final", "final") : method.frame_history_indices?.[frame] ?? method.frame_indices?.[frame] ?? frame + 1}{" "}
                <small>
                  {playbackKind === "wave" ? "s" : t("update", "paso")}
                </small>
              </strong>
              <span>
                {playbackKind === "wave"
                  ? t(
                      "Computed pressure · interpolated playback",
                      "Presión calculada · reproducción interpolada",
                    )
                  : t(
                      "Outlines: known interfaces",
                      "Contornos: interfaces conocidas",
                    )}{" "}
                · {run.frequency} Hz
              </span>
            </div>
          </div>
          <div className="two-plots">
            {vel(
              run.truth as number[][],
              t("Known velocity", "Velocidad conocida"),
            )}
            {gatherPlot(
              gather,
              t("Recorded receiver arrivals", "Arribos registrados"),
            )}
          </div>
        </div>
      );
      measurements = (
        <div className="evidence-layout">
          <label className="inline-control">
            {t("Source position", "Posición de fuente")}
            <select
              className="select"
              value={shot}
              onChange={(e) => setShot(+e.target.value)}
            >
              {run.sources!.map((p, i) => (
                <option key={i} value={i}>
                  S{i + 1} · {p[0]} m
                </option>
              ))}
            </select>
          </label>
          <div className="three-plots">
            {gatherPlot(gather, t("Observed", "Observado"))}
            {gatherPlot(pred[shot], t("Predicted", "Predicho"))}
            {gatherPlot(res[shot], t("Residual", "Residuo"))}
          </div>
          <Plot
            title={t("Central receiver trace", "Traza del receptor central")}
            x={time}
            series={[
              {
                name: t("Observed", "Observado"),
                values: gather[Math.floor(gather.length / 2)],
              },
              {
                name: t("Predicted", "Predicho"),
                values: pred[shot][Math.floor(gather.length / 2)],
              },
            ]}
            xLabel={t("Time · s", "Tiempo · s")}
            yLabel={t("Amplitude", "Amplitud")}
          />
        </div>
      );
      recovery = (
        <div className="evidence-layout">
          <div className="three-plots">
            {run.initial && vel(run.initial as number[][], t("Starting model", "Modelo inicial"))}
            {vel(
              method.model as number[][],
              t("Recovered velocity", "Velocidad recuperada"),
            )}
            <Heatmap
              title={t("Velocity error", "Error de velocidad")}
              data={(method.model as number[][]).map((r, i) =>
                r.map((v, j) => v - (run.truth as number[][])[i][j]),
              )}
              unit="m/s"
              xLabel={t("Distance · m", "Distancia · m")}
              yLabel={t("Depth · m", "Profundidad · m")}
              xRange={seismicX}
              yRange={seismicY}
            />
          </div>
          {history}
        </div>
      );
    } else if (run.family === "learned") {
      const cnn = methodId === "cnn";
      const networkInput = !cnn && method.network_input?.length === run.survey!.observed.length
        ? method.network_input : undefined;
      const ref = cnn ? run.column_truth! : matrix(networkInput ?? run.survey!.observed);
      const predicted = cnn
        ? (method.model as number[][])
        : matrix(method.predicted as number[]);
      const errorMap = cnn
        ? (method.residual as unknown as number[][])
        : (method.model as number[][]);
      const classicalColumns = cnn ? Object.entries(run.methods).filter(([, m]) => m.column_model) : [];
      const bounds = sharedScale([ref, predicted, ...classicalColumns.map(([, m]) => m.column_model!)], cnn).range;
      earth = (
        <div className="learned-view">
          <ApplicabilityWarning method={method} />
          <div className="learning-contract">
            <span className="small-caps">
              {cnn ? "CNN · 800 / 160 / 160" : "AUTOENCODER · LATENT 12"}
            </span>
            <h2>
              {cnn
                ? t(
                    "Depth-integrated density prediction",
                    "Predicción de densidad integrada",
                  )
                : t(
                    "Observation reconstruction error",
                    "Error de reconstrucción de observaciones",
                  )}
            </h2>
            <p>{lesson.read[lang]}</p>
            {!cnn && !networkInput && <p role="note" className="plot-note">{t(
              "This artifact does not export the network input. The first map shows recorded observations; its preprocessing support cannot be checked against the exported error map here.",
              "Este artefacto no exporta la entrada de la red. El primer mapa muestra observaciones registradas; aquí no se puede comprobar su soporte de preprocesamiento frente al mapa de error exportado.",
            )}</p>}
            {!cnn && networkInput && run.variant === "coverage" && <p className="plot-note">{t(
              "Missing stations are interpolated in the network input. The score and error map compare reconstruction with that input; the separate raw-observation MSE retains the comparison with recorded stations.",
              "Las estaciones omitidas se interpolan en la entrada de la red. Puntaje y mapa de error comparan reconstrucción con esa entrada; el MSE separado frente a observaciones originales conserva la comparación con estaciones registradas.",
            )}</p>}
          </div>
          <div className="three-plots">
            <Heatmap
              data={ref}
              title={
                cnn
                  ? t("Known column density", "Densidad integrada conocida")
                  : networkInput ? t("Network input", "Entrada de la red") : t("Recorded observations", "Observaciones registradas")
              }
              range={bounds}
              unit={cnn ? "g/cm³ m" : "mGal"}
              xLabel="E · m"
              yLabel="N · m"
              xRange={[-1120, 1120]}
              yRange={[-960, 960]}
            />
            <Heatmap
              data={predicted}
              title={t("Network reconstruction", "Reconstrucción de la red")}
              range={bounds}
              unit={cnn ? "g/cm³ m" : "mGal"}
              xLabel="E · m"
              yLabel="N · m"
              xRange={[-1120, 1120]}
              yRange={[-960, 960]}
            />
            <Heatmap
              data={errorMap}
              title={cnn ? t("Column error", "Error de columna") : networkInput ? t("Squared error versus network input", "Error cuadrático frente a entrada de red") : t("Exported squared-error map", "Mapa de error cuadrático exportado")}
              unit={
                cnn
                  ? "g/cm³ m"
                  : t(
                      "normalized squared error",
                      "error cuadrático normalizado",
                    )
              }
              xLabel="E · m"
              yLabel="N · m"
              xRange={[-1120, 1120]}
              yRange={[-960, 960]}
              palette={cnn ? "field" : "error"}
            />
          </div>
          {!!classicalColumns.length && <section>
            <h3>{t("Matched classical column estimates", "Estimaciones clásicas de columna comparables")}</h3>
            <p className="plot-note">{t("These are exported depth integrals of the classical 3D estimates, compared with the same column target and observations as the CNN. All column maps share the same signed physical colour scale.", "Son integrales de profundidad exportadas de estimados 3D clásicos, comparadas con el mismo objetivo y observaciones que la CNN. Todos los mapas comparten escala física con signo.")}</p>
            <div className="two-plots">{classicalColumns.map(([id, m]) => <Heatmap key={id} data={m.column_model!} title={methodName(id, es)} unit="g/cm³ m" range={bounds} xLabel="E · m" yLabel="N · m" xRange={[-1120,1120]} yRange={[-960,960]} />)}</div>
          </section>}
          {!cnn && <DetectionEvidence data={method.detection_validation} />}
          <p className="plot-note">
            {t(
              "Oblique and ring geometries are excluded from training. Weights are selected on validation data, never on this case.",
              "Las geometrías oblicua y anular se excluyen del entrenamiento. Los pesos se seleccionan en validación, nunca con este caso.",
            )}
          </p>
        </div>
      );
      measurements = earth;
      recovery = (
        <div className="evidence-layout">
          {history}
          <p className="plot-note">
            {t(
              "Learning curves are validation MSE recorded every five epochs. Checkpoint SHA-256:",
              "Las curvas son MSE de validación cada cinco épocas. SHA-256 del checkpoint:",
            )}{" "}
            <code>{method.checkpoint}</code>
          </p>
        </div>
      );
    }
  }
  if (processingProjectId) return <>
    <ProjectProcessingWorkbench key={processingProjectId} projectId={processingProjectId} es={es} onManage={() => setProjectsOpen(true)} onCurated={() => selectProcessingProject("")} />
    {projectsOpen && <ProjectDrawer es={es} onClose={closeProjects} onOwnerCleared={() => selectProcessingProject("")} onOpenWorkbench={id => { selectProcessingProject(id); setProjectsOpen(false); }} />}
  </>;
  return (
    <div className="page-body wide workbench">
      <aside className={`instrument-sidebar ${controlsOpen ? "expanded" : ""}`}>
        <div className="instrument-brand">
          <span className="small-caps">{entry && familyLabels[entry.family][lang]} / {String((catalog?.cases.findIndex((c) => c.id === selected) ?? 0) + 1).padStart(2, "0")}</span>
          <h1>{es ? entry?.name_es : entry?.name}</h1>
        </div>
        <label className="select-control">
          <span>01 / {t("Geological case", "Caso geológico")}</span>
          <select
            className="select"
            aria-label={t("Geological case", "Caso geológico")}
            value={selected}
            onChange={(e) => select(e.target.value)}
          >
            {Object.entries(familyLabels).map(([family, labels]) => (
              <optgroup key={family} label={labels[lang]}>
                {catalog?.cases
                  .filter((c) => c.family === family)
                  .map((c) => (
                    <option key={c.id} value={c.id}>
                      {es ? c.name_es : c.name}
                    </option>
                  ))}
              </optgroup>
            ))}
          </select>
        </label>
        <button
          className="btn mobile-controls-toggle"
          aria-expanded={controlsOpen}
          onClick={() => setControlsOpen((v) => !v)}
        >
          {controlsOpen
            ? t("Close experiment controls", "Cerrar controles")
            : t(
                "Experiment & method controls",
                "Controles de experimento y método",
              )}{" "}
          {controlsOpen ? "−" : "+"}
        </button>
        <div className="sidebar-panel-switch" role="group" aria-label={t("Control sections", "Secciones de control")}>
          {([
            ["experiment", t("Experiment", "Experimento")],
            ["replay", t("Replay", "Reproducción")],
            ["evidence", t("Evidence", "Evidencia")],
          ] as const).map(([id, label]) => <button key={id} className={`chip ${sidebarPanel === id ? "on" : ""}`} aria-pressed={sidebarPanel === id} onClick={() => setSidebarPanel(id)}>{label}</button>)}
        </div>
        {sidebarPanel === "experiment" && <>
        <label className="select-control">
          <span>02 / {t("Experiment", "Experimento")}</span>
          <select
            className="select"
            aria-label={t("Experiment", "Experimento")}
            value={variant}
            onChange={(e) => setVariant(e.target.value)}
          >
            {entry?.variants.map((v) => (
              <option key={v.id} value={v.id}>
                {es ? v.name_es : v.name}
              </option>
            ))}
          </select>
        </label>
        <label className="select-control">
          <span>03 / {t("Inverse method", "Método inverso")}</span>
          <select
            className="select"
            aria-label={t("Inverse method", "Método inverso")}
            value={methodId}
            onChange={(e) => {
              setMethodId(e.target.value);
              setFrame(0);
              setPlaying(false);
              setModelState("final");
              setPlaybackKind("inverse");
            }}
          >
            {Object.entries(run?.methods ?? {}).map(([id, m]) => (
              <option key={id} value={id}>
                {methodName(id, es, es ? m.name_es : m.name)}
              </option>
            ))}
          </select>
        </label>
        {method && <EvaluationStatus method={method} methodId={methodId} variant={run?.variant} compact />}
        </>}
        {sidebarPanel === "replay" && <>
        <div className="playback">
          <button className="btn" aria-pressed={modelState === "final" && playbackKind === "inverse"} onClick={returnToFinal}>{t("Show final model", "Mostrar modelo final")}</button>
          {run?.family === "seismic" && (
            <>
              <label className="select-control">
                <span>{t("Recorded process", "Proceso registrado")}</span>
                <select
                  className="select"
                  aria-label={t("Animation process", "Proceso animado")}
                  value={playbackKind}
                  onChange={(e) => {
                    setPlaybackKind(e.target.value);
                    setFrame(0);
                    setPlaying(false);
                    setModelState(e.target.value === "wave" ? "final" : "replay");
                  }}
                >
                  <option value="wave">
                    {t("Wave propagation", "Propagación de ondas")}
                  </option>
                  <option value="inverse">
                    {t("Inversion updates", "Actualizaciones inversas")}
                  </option>
                </select>
              </label>
              <Range
                label={t(
                  "Amplitude display gain",
                  "Ganancia visual de amplitud",
                )}
                value={gain}
                min={1}
                max={30}
                unit="×"
                onChange={setGain}
              />
              <small>
                {t(
                  "Fixed gain; colours clip at legend limits.",
                  "Ganancia fija; colores saturan en límites de leyenda.",
                )}
              </small>
            </>
          )}
          <span className="small-caps">
            {run?.family === "seismic" && playbackKind === "wave"
              ? t("WAVE PROPAGATION", "PROPAGACIÓN DE ONDAS")
              : t("INVERSION REPLAY", "REPRODUCCIÓN INVERSA")}
          </span>
          <div className="playback-row">
            <button
              className="btn play-button"
              disabled={count < 2 || loading}
              aria-label={
                playing ? t("Pause", "Pausar") : t("Play", "Reproducir")
              }
              onClick={() => {
                setPlaying((v) => !v);
                if (playbackKind !== "wave") setModelState("replay");
                setMode("recovered");
              }}
            >
              {playing ? <Pause size={19} /> : <Play size={19} />}
            </button>
            <input
              aria-label={t("Replay frame", "Cuadro de reproducción")}
              type="range"
              className="range"
              min={0}
              max={Math.max(0, count - 1)}
              value={Math.min(frame, Math.max(0, count - 1))}
              disabled={count < 2}
              onChange={(e) => {
                setFrame(+e.target.value);
                setPlaying(false);
                if (playbackKind !== "wave") setModelState("replay");
                setMode("recovered");
              }}
            />
            <output>
              {modelState === "final" && playbackKind !== "wave" ? t("final", "final") : count ? `${frame + 1}/${count}` : t("final", "final")}
            </output>
          </div>
          <small>
            {count === 0
              ? t(
                  "Final prediction; validation history is in Inversion.",
                  "Predicción final; historial de validación en Inversión.",
                )
              : count < 2
                ? t(
                    "This method has a single saved solution.",
                    "Este método tiene una solución guardada.",
                  )
                : t(
                    "Computed states · pause and scrub to inspect",
                    "Estados calculados · pause e inspeccione",
                  )}
          </small>
        </div>
        <div className="sidebar-actions">
          <button
            className="btn"
            onClick={() => {
              setReset((n) => n + 1);
              setAngle(0);
              setFrame(0);
              setPlaying(false);
              setOrbit(false);
              returnToFinal();
              setCut(960);
              setOpacity(1);
            }}
          >
            <RotateCcw size={14} />
            {t("Reset view", "Restablecer vista")}
          </button>
          <button className="btn" onClick={exportRun} disabled={!run}>
            <Download size={14} />
            {t("Export run", "Exportar ejecución")}
          </button>
        </div>
        {method && <EvaluationStatus method={method} methodId={methodId} variant={run?.variant} compact />}
        </>}
        {sidebarPanel === "evidence" && <>
        <div className="case-question">
          <span>{t("Case hypothesis", "Hipótesis del caso")}</span>
          <p>{lesson.question[lang]}</p>
        </div>
        <div className="source-caption">
          <span className="source-dot" />
          {run?.provenance.synthetic ? t("Constructed synthetic target", "Objetivo sintético construido") : t("External observations", "Observaciones externas")}
          <small>
            {run?.engine} · {run?.provenance?.version}
            <br />
            {t(
              "Offline solve / interactive inspection",
              "Cálculo offline / inspección interactiva",
            )}
          </small>
          {run && <p>{provenanceDescription(run, es)}</p>}
          {method && <EvaluationStatus method={method} methodId={methodId} variant={run?.variant} />}
        </div>
        </>}
      </aside>
      <section className="instrument-main" aria-label={es ? entry?.name_es : entry?.name}>
        {deploymentMode === "single-origin" && <div className="project-launch"><span className="project-launch-context">{t("Curated case view · private originals are separate", "Caso curado · los originales privados son independientes")}</span><button ref={projectLauncher} className="btn" onClick={() => setProjectsOpen(true)}>{t("Projects & raw data", "Proyectos y datos originales")}</button></div>}
        {error ? (
          <div role="alert" className="load-state">
            {error}
            <button className="btn" onClick={() => location.reload()}>
              {t("Retry", "Reintentar")}
            </button>
          </div>
        ) : loading ? (
          <div className="load-state">
            <span className="loading-orbit" />
            {t("Loading numerical result…", "Cargando resultado numérico…")}
          </div>
        ) : (
          run &&
          method && (
            <Tabs
              key={selected}
              ariaLabel={t("Scientific views", "Vistas científicas")}
              tabs={[
                {
                  id: "earth",
                  label: t("Model", "Modelo"),
                  content: <>{run.family !== "learned" && !physical && <p className="plot-note" role="status">{playbackKind === "wave" && run.family === "seismic" ? t("Synthetic-target wavefield; not propagation in the recovered model.", "Campo de ondas del objetivo sintético; no propagación en el modelo recuperado.") : displayedState}. {t("Data predictions and evaluation remain at the selected final model.", "Las predicciones y evaluación corresponden al modelo final seleccionado.")}</p>}{earth}</>,
                },
                {
                  id: "observations",
                  label: t("Data", "Datos"),
                  content: <div className="evidence-layout"><p className="plot-note">{t("Predictions and residuals are evaluated at the selected final model. Scrubbing a model replay does not recompute these data.", "Predicciones y residuos se evalúan en el modelo final seleccionado. Mover la reproducción del modelo no recalcula estos datos.")}</p>{measurements}</div>,
                },
                {
                  id: "recovery",
                  label: t("Inversion", "Inversión"),
                  content: <div className="evidence-layout"><TargetEvidence run={run} methodId={methodId} />{recovery}<UncertaintyView run={run} method={method} section={section} /></div>,
                },
                {
                  id: "question",
                  label: t("Case analysis", "Análisis del caso"),
                  content: (
                    <div className="context-view">
                      <span className="small-caps">
                        {t(
                          "Experimental conditions",
                          "Condiciones experimentales",
                        )}
                      </span>
                      <h2>{lesson.question[lang]}</h2>
                      <p>{lesson.read[lang]}</p>
                      <h3>{t("Selected result", "Resultado seleccionado")}</h3>
                      <p>
                        {methodName(methodId, es)} ·{" "}
                        {es ? artifact?.name_es : artifact?.name}
                      </p>
                      <TargetEvidence run={run} methodId={methodId} />
                      <EvidenceMetrics run={run} methodId={methodId} />
                      <h3>
                        {t("Recorded trajectory", "Trayectoria registrada")}
                      </h3>
                      <p>{historyInfo(methodId, es).description}</p>
                      <div className="investigation">
                        <span>01</span>
                        <div>
                          <h3>
                            {t(
                              "Comparison protocol",
                              "Protocolo de comparación",
                            )}
                          </h3>
                          <p>{lesson.try[lang]}</p>
                        </div>
                      </div>
                      <div className="investigation">
                        <span>02</span>
                        <div>
                          <h3>
                            {t(
                              "Limits of interpretation",
                              "Límites de interpretación",
                            )}
                          </h3>
                          <p>{lesson.limit[lang]}</p>
                        </div>
                      </div>
                      <dl className="parameter-ledger">
                        {Object.entries(run.parameters).map(([k, v]) => (
                          <div key={k}>
                            <dt>
                              {(
                                {
                                  contrast: t(
                                    "Property contrast factor",
                                    "Factor de contraste",
                                  ),
                                  noise: t(
                                    "Noise condition",
                                    "Condición de ruido",
                                  ),
                                  height: t(
                                    "Receiver height · m",
                                    "Altura de receptores · m",
                                  ),
                                  inclination: t(
                                    "Inclination · °",
                                    "Inclinación · °",
                                  ),
                                  beta: t(
                                    "Regularization β",
                                    "Regularización β",
                                  ),
                                  frequency: t(
                                    "Source frequency · Hz",
                                    "Frecuencia de fuente · Hz",
                                  ),
                                  receivers: t(
                                    "Receiver count",
                                    "Cantidad de receptores",
                                  ),
                                  coverage: t(
                                    "Coverage fraction",
                                    "Fracción de cobertura",
                                  ),
                                  coupling: t(
                                    "Structural coupling λ",
                                    "Acoplamiento estructural λ",
                                  ),
                                } as Record<string, string>
                              )[k] ?? k}
                            </dt>
                            <dd>{typeof v === "number" ? format(v) : typeof v === "boolean" ? v ? t("Yes", "Sí") : t("No", "No") : Array.isArray(v) ? v.map(format).join(", ") : v}</dd>
                          </div>
                        ))}
                      </dl>
                      <p className="plot-note">
                        {t("Deterministic seed", "Semilla determinista")}:{" "}
                        {run.seed} · SHA-256 <code>{artifact?.sha256}</code>
                      </p>
                    </div>
                  ),
                },
              ]}
            />
          )
        )}
      </section>
      {projectsOpen && <ProjectDrawer es={es} onClose={closeProjects} onOpenWorkbench={id => { selectProcessingProject(id); setProjectsOpen(false); }} />}
    </div>
  );
}
