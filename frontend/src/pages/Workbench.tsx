import { useCallback, useEffect, useMemo, useState } from "react";
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
import { lessons } from "../data/lessons";

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
  const [mode, setMode] = useState("truth");
  const [section, setSection] = useState(6);
  const [cut, setCut] = useState(960);
  const [opacity, setOpacity] = useState(1);
  const [survey, setSurvey] = useState(true);
  const [angle, setAngle] = useState(0);
  const [angleStep, setAngleStep] = useState(15);
  const [speed, setSpeed] = useState(8);
  const [orbit, setOrbit] = useState(false);
  const [reset, setReset] = useState(0);
  const [frame, setFrame] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [blend,setBlend]=useState(0);
  const [shot, setShot] = useState(1);
  const [controlsOpen, setControlsOpen] = useState(false);
  const [gain, setGain] = useState(8);
  const [playbackKind, setPlaybackKind] = useState("wave");
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
  const artifact = entry?.variants.find((v) => v.id === variant);
  useEffect(() => {
    if (!artifact) return;
    const controller = new AbortController();
    setLoading(true);
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
          run?.id === r.id && r.methods[methodId] ? methodId : preferred;
        setMethodId(nextId);
        setFrame(
          r.family === "seismic" && playbackKind === "wave"
            ? Math.floor((r.wavefields?.length ?? 1) * 0.4)
            : Math.max(0, r.methods[nextId].frames.length - 1),
        );
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
    if (!playing || count < 2) {setBlend(0);return;}
    if(run?.family==='seismic'&&playbackKind==='wave'){
      const start=performance.now(),initial=frame;let handle=0,last=0;
      const tick=(now:number)=>{if(now-last>=32){const progress=initial+(now-start)/120;const current=Math.floor(progress)%count;setFrame(current);setBlend(current===count-1?0:progress%1);last=now;}handle=requestAnimationFrame(tick);};
      handle=requestAnimationFrame(tick);return()=>cancelAnimationFrame(handle);
    }
    const id = setInterval(() => setFrame((f) => (f + 1) % count), 120);
    return () => clearInterval(id);
  }, [playing, count,run?.family,playbackKind]);
  const waveRange=useMemo(()=>run?.wavefields?signed(run.wavefields.flat(2)):[-1,1] as [number,number],[run]);
  const values = useMemo(
    () =>
      !run || !method
        ? []
        : flatten(
            mode === "truth"
              ? run.truth
              : (method.frames[frame] ?? method.model),
          ),
    [run, method, frame, mode],
  );
  const pickCell = useCallback(
    (i: number) => setSection(Math.floor(i / 14) % 12),
    [],
  );
  const select = (id: string) => {
    setSelected(id);
    setVariant("reference");
    setMode("truth");
    setFrame(0);
    setReset((n) => n + 1);
    setCut(960);
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
    const truth = flatten(run.truth);
    const history = (
      <div className="convergence-panel">
        <Plot
          title={t("Recorded objective", "Objetivo registrado")}
          x={indices(method.history.length)}
          series={[
            { name: t("Objective", "Objetivo"), values: method.history },
          ]}
          xLabel={t(
            "Saved evaluation / update",
            "Evaluación / actualización guardada",
          )}
          yLabel={t("Objective value", "Valor del objetivo")}
          logY={method.history.every((v) => v > 0)}
        />
        <div className="metric-grid">
          {Object.entries(method.metrics).map(([key, value]) => (
            <div key={key}>
              <span>{key.replaceAll("_", " ")}</span>
              <strong>
                {typeof value === "boolean"
                  ? value
                    ? t("Yes", "Sí")
                    : t("No", "No")
                  : format(value)}
              </strong>
            </div>
          ))}
        </div>
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
      const bounds = signed(s.observed);
      const predicted = method.predicted as number[];
      earth = (
        <div className="earth-view">
          <div className="scene-toolbar">
            <div className="segmented">
              <button
                className={mode === "truth" ? "active" : ""}
                onClick={() => setMode("truth")}
              >
                {t("Known geology", "Geología conocida")}
              </button>
              <button
                className={mode === "recovered" ? "active" : ""}
                onClick={() => {
                  setMode("recovered");
                  setFrame(Math.max(0, count - 1));
                }}
              >
                {t("Recovered", "Recuperada")}
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
            <button className="text-button" onClick={() => setOrbit((v) => !v)}>
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
            angle={angle}
            speed={speed}
            playing={orbit}
            reset={reset}
            label={
              mode === "truth"
                ? t("Known geology", "Geología conocida")
                : t("Recovered model", "Modelo recuperado")
            }
            onCell={pickCell}
          />
          <div className="scene-bottom">
            <Legend
              range={
                extent(values)[0] < -signed(values)[1] * 0.1
                  ? signed(values)
                  : [0, signed(values)[1]]
              }
              unit={run.units}
              palette={
                extent(values)[0] < -signed(values)[1] * 0.1 ? "field" : "earth"
              }
            />
            <span>
              {t(
                "Cells below 10% of maximum |m| are hidden.",
                "Se ocultan celdas bajo 10% del máximo |m|.",
              )}
            </span>
          </div>
          <div className="scene-adjustments">
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
                aria-label={t("Rotate left", "Girar izquierda")}
                onClick={() => setAngle((v) => (v - angleStep + 360) % 360)}
              >
                <ChevronLeft size={16} />
              </button>
              <button
                aria-label={t("Rotate right", "Girar derecha")}
                onClick={() => setAngle((v) => (v + angleStep) % 360)}
              >
                <ChevronRight size={16} />
              </button>
            </div>
          </div>
        </div>
      );
      measurements = (
        <div className="evidence-layout">
          <div className="three-plots">
            {[
              [s.observed, t("Observed field", "Campo observado")],
              [predicted, t("Predicted field", "Campo predicho")],
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
              "Black survey markers identify active stations. Coverage experiments fit alternate stations; predictions at omitted stations remain visible.",
              "Marcadores negros identifican estaciones activas. Los experimentos de cobertura ajustan estaciones alternas; las predicciones en estaciones omitidas siguen visibles.",
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
            max={11}
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
                range={signed(truth)}
                xLabel={t("Easting · m", "Este · m")}
                yLabel={t("Depth · m", "Profundidad · m")}
                xRange={[-1120, 1120]}
                yRange={[0, 1120]}
              />
            ))}
          </div>
          {run.family === "joint" && method.secondary_model && (
            <div className="two-plots">
              <Heatmap
                title={t(
                  "Recovered susceptibility",
                  "Susceptibilidad recuperada",
                )}
                data={sliceVolume(
                  method.secondary_model,
                  run.grid.shape,
                  section,
                )}
                unit="SI"
                xLabel="E · m"
                yLabel={t("Depth · m", "Profundidad · m")}
                xRange={[-1120, 1120]}
                yRange={[0, 1120]}
              />
              <Heatmap
                title={t(
                  "Structural disagreement |∇ρ × ∇χ|",
                  "Desacuerdo estructural |∇ρ × ∇χ|",
                )}
                data={sliceVolume(
                  method.cross_gradient!,
                  run.grid.shape,
                  section,
                )}
                unit={t("normalized", "normalizado")}
                xLabel="E · m"
                yLabel={t("Depth · m", "Profundidad · m")}
                xRange={[-1120, 1120]}
                yRange={[0, 1120]}
                palette="error"
              />
            </div>
          )}
          {history}
        </div>
      );
    } else if (run.family === "mt") {
      const obs = run.observed as Curves,
        fit = method.predicted as Curves;
      const f = run.frequencies!;
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
              rho={(method.frames[frame] as number[]) ?? final}
              thickness={run.thickness!}
              title={t(
                "Recovered earth · replay",
                "Tierra recuperada · reproducción",
              )}
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
                "Curves show the final fitted solution. Column animation follows saved optimizer evaluations.",
                "Las curvas muestran la solución final. La columna animada sigue evaluaciones guardadas del optimizador.",
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
              title={t("Known resistivities", "Resistividades conocidas")}
            />
            <LayerColumn
              rho={final}
              thickness={run.thickness!}
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
      const gather = obs[Math.min(shot, obs.length - 1)];
      const nt = gather[0].length;
      const time = indices(nt).map((i) => i * run.dt!);
      const savedWave =
        playbackKind === "wave"
          ? run.wavefields![Math.min(frame, count - 1)]
          : (method.frames[Math.min(frame, count - 1)] as number[][]);
      const wave=playbackKind==='wave'&&playing&&blend>0?savedWave.map((row,y)=>row.map((v,x)=>v*(1-blend)+run.wavefields![Math.min(frame+1,count-1)][y][x]*blend)):savedWave;
      const fullWaveRange = waveRange;
      const wr: [number, number] = [
        fullWaveRange[0] / gain,
        fullWaveRange[1] / gain,
      ];
      const bounds = extent(truth);
      const vel = (data: number[][], title: string) => (
        <Heatmap
          data={data}
          title={title}
          palette="velocity"
          range={bounds}
          unit="m/s"
          xLabel={t("Distance · m", "Distancia · m")}
          yLabel={t("Depth · m", "Profundidad · m")}
          xRange={[-12.5, 1587.5]}
          yRange={[-12.5, 1187.5]}
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
              ? ((frame+blend) * run.wavefield_dt! + run.dt! / 2) / (nt * run.dt!)
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
              xRange={[-12.5, 1587.5]}
              yRange={[-12.5, 1187.5]}
              markers={[{ x: 32.5 / 64, y: 3.5 / 48, label: "S" }]}
            />
            <div className="wave-clock">
              <strong>
                {playbackKind === "wave"
                  ? ((frame+blend) * run.wavefield_dt!).toFixed(3)
                  : frame * 2}{" "}
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
            <select value={shot} onChange={(e) => setShot(+e.target.value)}>
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
            {vel(run.initial!, t("Starting model", "Modelo inicial"))}
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
              xRange={[-12.5, 1587.5]}
              yRange={[-12.5, 1187.5]}
            />
          </div>
          {history}
        </div>
      );
    } else if (run.family === "learned") {
      const cnn = methodId === "cnn";
      const ref = cnn ? run.column_truth! : matrix(run.survey!.observed);
      const predicted = cnn
        ? (method.model as number[][])
        : matrix(method.predicted as number[]);
      const errorMap = cnn
        ? (method.residual as unknown as number[][])
        : (method.model as number[][]);
      const bounds = extent(ref.flat());
      earth = (
        <div className="learned-view">
          <div className="learning-contract">
            <span className="small-caps">
              {cnn ? "CNN · 800 / 160 / 160" : "AUTOENCODER · LATENT 12"}
            </span>
            <h2>
              {cnn
                ? t(
                    "A projection, not a 3D earth",
                    "Una proyección, no una Tierra 3D",
                  )
                : t(
                    "Where the learned prior fails",
                    "Dónde falla el prior aprendido",
                  )}
            </h2>
            <p>{lesson.read[lang]}</p>
          </div>
          <div className="three-plots">
            <Heatmap
              data={ref}
              title={
                cnn
                  ? t("Known column density", "Densidad integrada conocida")
                  : t("Observed field", "Campo observado")
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
              title={t("Reconstruction error", "Error de reconstrucción")}
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
  return (
    <div className="page-body wide workbench">
      <aside className={`instrument-sidebar ${controlsOpen ? "expanded" : ""}`}>
        <div className="instrument-brand">
          <span className="small-caps">
            {t("GEOPHYSICAL OBSERVATORY", "OBSERVATORIO GEOFÍSICO")}
          </span>
          <h1>{t("Beneath the surface.", "Bajo la superficie.")}</h1>
        </div>
        <label className="select-control">
          <span>01 / {t("Geological case", "Caso geológico")}</span>
          <select
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
        <div className="case-question">
          <span>{t("THE QUESTION", "LA PREGUNTA")}</span>
          <p>{lesson.question[lang]}</p>
        </div>
        <button
          className="mobile-controls-toggle"
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
        <label className="select-control">
          <span>02 / {t("Experiment", "Experimento")}</span>
          <select
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
            aria-label={t("Inverse method", "Método inverso")}
            value={methodId}
            onChange={(e) => {
              setMethodId(e.target.value);
              setFrame(0);
              setPlaying(false);
            }}
          >
            {Object.entries(run?.methods ?? {}).map(([id, m]) => (
              <option key={id} value={id}>
                {es ? m.name_es : m.name}
              </option>
            ))}
          </select>
        </label>
        <div className="playback">
          {run?.family === "seismic" && (
            <>
              <label className="select-control">
                <span>
                  {t("Animate a physical process", "Animar un proceso físico")}
                </span>
                <select
                  aria-label={t("Animation process", "Proceso animado")}
                  value={playbackKind}
                  onChange={(e) => {
                    setPlaybackKind(e.target.value);
                    setFrame(0);
                    setPlaying(false);
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
              className="play-button"
              disabled={count < 2 || loading}
              aria-label={
                playing ? t("Pause", "Pausar") : t("Play", "Reproducir")
              }
              onClick={() => {
                setPlaying((v) => !v);
                if (run?.family !== "seismic") setMode("recovered");
              }}
            >
              {playing ? <Pause size={19} /> : <Play size={19} />}
            </button>
            <input
              aria-label={t("Replay frame", "Cuadro de reproducción")}
              type="range"
              min={0}
              max={Math.max(0, count - 1)}
              value={Math.min(frame, Math.max(0, count - 1))}
              disabled={count < 2}
              onChange={(e) => {
                setFrame(+e.target.value);
                setPlaying(false);
                setMode("recovered");
              }}
            />
            <output>
              {count ? frame + 1 : 0}/{count}
            </output>
          </div>
          <small>
            {count < 2
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
            onClick={() => {
              setReset((n) => n + 1);
              setAngle(0);
              setFrame(0);
              setPlaying(false);
              setOrbit(false);
              setCut(960);
              setOpacity(1);
            }}
          >
            <RotateCcw size={14} />
            {t("Reset view", "Restablecer vista")}
          </button>
          <button onClick={exportRun} disabled={!run}>
            <Download size={14} />
            {t("Export run", "Exportar ejecución")}
          </button>
        </div>
        <div className="source-caption">
          <span className="source-dot" />
          {t("Original synthetic geology", "Geología sintética original")}
          <small>
            {run?.engine} · {run?.provenance?.version}
            <br />
            {t(
              "Offline solve / interactive inspection",
              "Cálculo offline / inspección interactiva",
            )}
          </small>
        </div>
      </aside>
      <section className="instrument-main">
        <header className="case-heading">
          <div>
            <span className="small-caps">
              {entry && familyLabels[entry.family][lang]} /{" "}
              {String(
                (catalog?.cases.findIndex((c) => c.id === selected) ?? 0) + 1,
              ).padStart(2, "0")}
            </span>
            <h2>{es ? entry?.name_es : entry?.name}</h2>
          </div>
          <span className="case-counter">
            20 {t("geological questions", "preguntas geológicas")}
          </span>
        </header>
        {error ? (
          <div role="alert" className="load-state">
            {error}
            <button onClick={() => location.reload()}>
              {t("Retry", "Reintentar")}
            </button>
          </div>
        ) : loading ? (
          <div className="load-state">
            <span className="loading-orbit" />
            {t("Loading computed evidence…", "Cargando evidencia calculada…")}
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
                  label: t("Earth & physics", "Tierra y física"),
                  content: earth,
                },
                {
                  id: "observations",
                  label: t("Measurements", "Mediciones"),
                  content: measurements,
                },
                {
                  id: "recovery",
                  label: t("Recovery & residual", "Recuperación y residuo"),
                  content: recovery,
                },
                {
                  id: "question",
                  label: t("Question & context", "Pregunta y contexto"),
                  content: (
                    <div className="context-view">
                      <span className="small-caps">
                        {t("READ THE EXPERIMENT", "LEA EL EXPERIMENTO")}
                      </span>
                      <h2>{lesson.question[lang]}</h2>
                      <p>{lesson.read[lang]}</p>
                      <div className="investigation">
                        <span>01</span>
                        <div>
                          <h3>
                            {t(
                              "Try this comparison",
                              "Pruebe esta comparación",
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
                              "What this cannot establish",
                              "Lo que esto no establece",
                            )}
                          </h3>
                          <p>{lesson.limit[lang]}</p>
                        </div>
                      </div>
                      <dl className="parameter-ledger">
                        {Object.entries(run.parameters).map(([k, v]) => (
                          <div key={k}>
                            <dt>{k.replaceAll("_", " ")}</dt>
                            <dd>{format(v)}</dd>
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
    </div>
  );
}
