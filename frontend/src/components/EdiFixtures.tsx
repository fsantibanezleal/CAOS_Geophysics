import { useEffect, useState } from "react";
import { Callout, Cite, Refs, useShellLang } from "@fasl-work/caos-app-shell";
import { appBase, extent, format, loadArtifact, type Curves } from "../science";
import { calibrationSeries, ediInterval, ediPath, validateEdiFieldScreen, validateEdiRun, type EdiBundle, type EdiCalibration, type EdiFieldScreen, type EdiFieldScreenEntry, type EdiFixture, type EdiRun } from "../edi";
import { metricInfo, methodName } from "../data/metrics";
import { mtForward } from "../mt";
import { EvaluationStatus } from "./ScientificEvidence";
import { LayerColumn, Plot } from "./ScientificPlots";

export function EdiResult({ run, fixture }: { run: EdiRun; fixture: EdiFixture }) {
  const es = useShellLang() === "es";
  const t = (a: string, b: string) => es ? b : a;
  const [selected, setSelected] = useState("mt-lm");
  const [view, setView] = useState<"apparent" | "complex">("apparent");
  const methodId = run.methods[selected] ? selected : Object.keys(run.methods)[0];
  const method = run.methods[methodId];
  const initial = method.solver.initial_model;
  const baseline = mtForward(initial, run.thickness, run.frequencies);
  const intervals = ediInterval(method.uncertainty);
  const label = (key: keyof Curves) => ({ apparent: t("Apparent resistivity", "Resistividad aparente"), phase: t("Impedance phase", "Fase de impedancia"), real: t("Real impedance", "Impedancia real"), imag: t("Imaginary impedance", "Impedancia imaginaria") })[key];
  const plot = (key: keyof Curves) => <Plot title={label(key)} x={run.frequencies} series={[
    { name: t("Parsed EDI observations", "Observaciones EDI leídas"), values: run.observed[key], points: true },
    { name: t("Final-model prediction", "Predicción del modelo final"), values: method.predicted[key] },
    { name: t("Independent starting-model response", "Respuesta del modelo inicial independiente"), values: baseline[key], dashed: true },
  ]} xLabel={t("Frequency · Hz", "Frecuencia · Hz")} yLabel={key === "apparent" ? "Ω m" : key === "phase" ? "°" : "Ω"} logX logY={key === "apparent"} />;
  const rhoRange = extent([...initial, ...method.model, ...fixture.truth_ohm_m].map(Math.log10));
  return <div className="evidence-layout">
    <Callout variant="honest" title={t("Original synthetic EDI fixture", "Archivo EDI sintético original")}>
      {t("These transfer functions are authored analytic fixtures, not downloaded field measurements. The generic EDI inversion receives no subsurface truth. A separately stored fixture oracle is shown only for evaluation; it never supplies model initialization or layer resistivities to the inverse.", "Estas funciones de transferencia son archivos analíticos originales, no mediciones de campo descargadas. La inversión EDI genérica no recibe verdad del subsuelo. La referencia sintética guardada aparte se muestra sólo para evaluación; no aporta inicio ni resistividades al inversor.")}
    </Callout>
    <div className="benchmark-controls">
      <label className="select-control"><span>{t("EDI inverse method", "Método inverso EDI")}</span><select className="select" value={methodId} onChange={e => setSelected(e.target.value)}>{Object.entries(run.methods).map(([id, m]) => <option key={id} value={id}>{methodName(id, es, es ? m.name_es : m.name)}</option>)}</select></label>
      <label className="select-control"><span>{t("Response representation", "Representación de respuesta")}</span><select className="select" value={view} onChange={e => setView(e.target.value as typeof view)}><option value="apparent">{t("Apparent resistivity and phase", "Resistividad aparente y fase")}</option><option value="complex">{t("Complex impedance", "Impedancia compleja")}</option></select></label>
      <a className="btn" download href={appBase + "data/v2/" + ediPath(fixture.source)}>{t("Download original EDI", "Descargar EDI original")}</a>
      <a className="btn" download href={appBase + "data/v2/" + ediPath(fixture.artifact)}>{t("Download numerical result", "Descargar resultado numérico")}</a>
    </div>
    <div className="two-plots">{view === "apparent" ? <>{plot("apparent")}{plot("phase")}</> : <>{plot("real")}{plot("imag")}</>}</div>
    <p className="plot-note">{t("Observation error σ refers to each independent real/imaginary impedance component, not apparent-resistivity error bars. The displayed predictions belong to the final selected model. Baseline curves are recalculated by the parity-tested browser forward solver from the exported initial model.", "El error σ corresponde a cada componente real/imaginario de impedancia, no a barras de resistividad aparente. Las predicciones corresponden al modelo final. Las curvas de referencia se recalculan con el solver directo del navegador validado por paridad, desde el modelo inicial exportado.")}</p>
    <div className="three-plots">
      <LayerColumn rho={initial} thickness={run.thickness} range={rhoRange} title={t("Prescribed starting model", "Modelo inicial prescrito")} />
      <LayerColumn rho={method.model} thickness={run.thickness} range={rhoRange} title={t("Selected final model", "Modelo final seleccionado")} />
      <LayerColumn rho={fixture.truth_ohm_m} thickness={fixture.thickness_m} range={rhoRange} title={t("Independent synthetic fixture oracle", "Referencia sintética independiente")} />
    </div>
    <p className="plot-note">{t("All columns use the same log-resistivity colour scale. Layer thickness is imposed; the half-space drawing has symbolic height. The artifact retains truth = null, since ordinary supplied EDI data have no known geological target.", "Todas las columnas usan la misma escala logarítmica. El espesor es impuesto y el semiespacio tiene altura simbólica. El artefacto conserva verdad = null: los datos EDI ordinarios no tienen objetivo geológico conocido.")}</p>
    <EvaluationStatus method={method} />
    {run.tensor && <details><summary>{t("Parsed tensor and 1D compatibility", "Tensor leído y compatibilidad 1D")}</summary>
      <p>{t("Converted impedance E/H in Ω; σ is per real/imaginary component. Tensor rows retain the supplied common frame. A passed screen is necessary, not sufficient, for 1D geology.", "Impedancia E/H convertida en Ω; σ por componente real/imaginaria. Se conserva el marco común declarado. Pasar este control es necesario, no suficiente, para geología 1D.")}</p>
      <dl className="parameter-ledger"><div><dt>WRMS Zxx</dt><dd>{format(run.compatibility.xx_component_wrms)}</dd></div><div><dt>WRMS Zyy</dt><dd>{format(run.compatibility.yy_component_wrms)}</dd></div><div><dt>{t("Conservative antisymmetry WRMS", "WRMS conservador de antisimetría")}</dt><dd>{format(run.compatibility.antisymmetry_conservative_wrms)}</dd></div><div><dt>{t("Acceptance threshold", "Umbral de aceptación")}</dt><dd>{run.compatibility.threshold}</dd></div></dl>
      <div className="table-scroll"><table className="cmp-table"><thead><tr><th>Hz</th>{["xx", "xy", "yx", "yy"].map(k => <th key={k}>Z{k}: Re / Im / σ · Ω</th>)}</tr></thead><tbody>{run.frequencies.map((f, i) => <tr key={i}><th scope="row">{format(f)}</th>{[[0, 0], [0, 1], [1, 0], [1, 1]].map(([a, b]) => <td key={`${a}${b}`}>{[run.tensor!.real[i][a][b], run.tensor!.imag[i][a][b], run.tensor!.sigma[i][a][b]].map(format).join(" / ")}</td>)}</tr>)}</tbody></table></div>
    </details>}
    <div className="table-scroll"><table className="cmp-table"><caption>{t("Final-model data evidence", "Evidencia de datos del modelo final")}</caption><thead><tr><th>{t("Metric", "Métrica")}</th><th>{t("Value", "Valor")}</th><th>{t("Meaning", "Significado")}</th></tr></thead><tbody>{Object.entries(method.metrics).map(([key, value]) => { const info = metricInfo(key, "mt", methodId, es); return <tr key={key}><th scope="row">{info.label}</th><td>{typeof value === "number" ? format(value) : value === null ? t("Unavailable", "No disponible") : value ? t("Yes", "Sí") : "No"} {info.unit}</td><td>{info.description}</td></tr>; })}</tbody></table></div>
    {intervals && intervals.lower.length === method.model.length && <>
      <h3>{t("Conditional noise-bootstrap intervals", "Intervalos condicionales bootstrap de ruido")}</h3>
      <Plot title={t("Layer resistivity and empirical interval", "Resistividad por capa e intervalo empírico")} x={method.model.map((_, i) => i + 1)} series={[
        { name: t("Selected final model", "Modelo final seleccionado"), values: method.model },
        { name: t("Synthetic fixture oracle", "Referencia sintética"), values: fixture.truth_ohm_m, points: true },
      ]} band={{ name: `${format(intervals.quantiles[0] * 100)}–${format(intervals.quantiles[1] * 100)}%`, lower: intervals.lower, upper: intervals.upper }} xLabel={t("Layer index", "Índice de capa")} yLabel="Ω m" logY={intervals.lower.every(v => v > 0)} />
      <p className="plot-note">{t("Completed / requested noise realizations", "Realizaciones completas / solicitadas")}: {intervals.members} / {intervals.requested}; {t("failed fits", "ajustes fallidos")}: {intervals.failures}; {t("seed", "semilla")}: {intervals.seed}. {t("These are conditional repeatability intervals, not a geological posterior. Thickness, acquisition, noise model, bounds and inversion settings remain fixed. No empirical field coverage is inferred from the nominal quantile level.", "Son intervalos de repetibilidad condicional, no un posterior geológico. Se fijan espesores, adquisición, modelo de ruido, cotas y configuración. El nivel nominal no implica cobertura empírica de campo.")}</p>
    </>}
    {method.uncertainty && !intervals && <p role="alert">{t("No valid completed interval is available; failed ensemble fits are not replaced by fabricated bands.", "No hay intervalo completado válido; ajustes fallidos no se sustituyen por bandas fabricadas.")}</p>}
    <details><summary>{t("Units, orientation and source identity", "Unidades, orientación e identidad")}</summary>
      <dl className="parameter-ledger">
        <div><dt>{t("Input impedance units", "Unidades de impedancia originales")}</dt><dd>{run.provenance.original_units}</dd></div>
        <div><dt>{t("Multiplier to E/H · Ω", "Multiplicador a E/H · Ω")}</dt><dd>{format(run.provenance.units_multiplier_to_ohm)}</dd></div>
        <div><dt>{t("Time convention: input → output", "Convención temporal: entrada → salida")}</dt><dd>e<sup>{run.provenance.original_sign_convention}iωt</sup> → e<sup>{run.provenance.output_sign_convention}iωt</sup></dd></div>
        <div><dt>{t("Original tensor rotation · °", "Rotación original del tensor · °")}</dt><dd>{fixture.rotation_deg}</dd></div>
        <div><dt>{t("Selected tensor component", "Componente tensorial seleccionado")}</dt><dd>{run.component}</dd></div>
        <div><dt>{t("Noise added to fixture", "Ruido agregado al archivo")}</dt><dd>{fixture.noise_added ? t("Yes", "Sí") : "No"}</dd></div>
      </dl>
      <p className="plot-note">{t("The parser preserves orientation and explicit E/B-to-E/H units and sign transformations. Arbitrary error covariance is not invented. A necessary 1D tensor consistency screen is not a proof that field geology is one-dimensional.", "El lector conserva orientación y transformaciones explícitas de unidades E/B a E/H y signo. No se inventa covarianza. El control tensorial necesario de consistencia 1D no prueba que geología de campo sea unidimensional.")}</p>
      <p>SHA-256 · EDI: <code>{fixture.source_sha256}</code></p><p>SHA-256 · JSON: <code>{fixture.artifact_sha256}</code></p>
    </details>
  </div>;
}

function sourceLink(raw: string | undefined): string | undefined {
  if (!raw) return undefined;
  const url = /^10\.\d{4,9}\//.test(raw) ? `https://doi.org/${raw}` : raw;
  try { return new URL(url).protocol === "https:" ? url : undefined; } catch { return undefined; }
}

export function EdiFieldScreenResult({ screen, entry }: { screen: EdiFieldScreen; entry: EdiFieldScreenEntry }) {
  const es = useShellLang() === "es";
  const t = (a: string, b: string) => es ? b : a;
  const [view, setView] = useState<"apparent" | "complex">("apparent");
  const release = screen.source_release ?? entry.source_release;
  const stationUrl = sourceLink(release?.station_url);
  const releaseDoi = sourceLink(release?.release_doi);
  const transferDoi = sourceLink(release?.transfer_function_doi);
  const comparison = (key: keyof Curves) => <Plot
    title={({ apparent: t("Apparent resistivity", "Resistividad aparente"), phase: t("Impedance phase", "Fase de impedancia"), real: t("Real impedance", "Impedancia real"), imag: t("Imaginary impedance", "Impedancia imaginaria") })[key]}
    x={screen.frequencies_hz}
    series={(["xy", "yx"] as const).map(component => ({ name: component === "xy" ? `Zxy · ${t("measured", "medido")}` : `−Zyx · ${t("sign-corrected", "signo corregido")}`, values: screen.observed[component][key], points: true }))}
    xLabel={t("Frequency · Hz", "Frecuencia · Hz")}
    yLabel={key === "apparent" ? "Ω m" : key === "phase" ? "°" : "Ω"}
    logX logY={key === "apparent"}
  />;
  const c = screen.compatibility;
  return <section className="evidence-layout" data-source-kind="measured-edi-screen">
    <Callout variant="honest" title={c.passes_screen ? t("Measured transfer functions · 1D screen passed", "Funciones de transferencia medidas · control 1D aprobado") : t("Measured transfer functions · 1D screen rejected", "Funciones de transferencia medidas · control 1D rechazado")}>
      {c.passes_screen
        ? t("The necessary tensor-consistency screen passes, but no inversion has been performed and one-dimensional geology is not established.", "El control necesario de consistencia tensorial pasa, pero no se ha invertido y no se establece geología unidimensional.")
        : t("The tensor fails the declared necessary isotropic-1D consistency screen. No 1D inversion was performed. The observed curves below are measurements, not predictions or a recovered subsurface model.", "El tensor no cumple el control necesario declarado de consistencia isotrópica 1D. No se realizó inversión 1D. Las curvas siguientes son mediciones, no predicciones ni un modelo del subsuelo recuperado.")}
    </Callout>
    <div className="benchmark-controls">
      <label className="select-control"><span>{t("Measured response", "Respuesta medida")}</span><select className="select" aria-label={t("Measured response", "Respuesta medida")} value={view} onChange={event => setView(event.target.value as typeof view)}><option value="apparent">{t("Apparent resistivity and phase", "Resistividad aparente y fase")}</option><option value="complex">{t("Complex impedance", "Impedancia compleja")}</option></select></label>
      <a className="btn" download href={appBase + "data/v2/" + ediPath(entry.artifact)}>{t("Download measured screen", "Descargar control medido")}</a>
      {entry.source && <a className="btn" download href={appBase + "data/v2/" + ediPath(entry.source)}>{t("Download source EDI", "Descargar EDI original")}</a>}
    </div>
    <div className="two-plots">{view === "apparent" ? <>{comparison("apparent")}{comparison("phase")}</> : <>{comparison("real")}{comparison("imag")}</>}</div>
    <Plot title={t("Impedance-component measurement uncertainty", "Incertidumbre de componentes de impedancia")} x={screen.frequencies_hz} series={(["xy", "yx"] as const).map(component => ({ name: `σ Z${component.toUpperCase()}`, values: screen.observed[component].sigma_real_imag_ohm }))} xLabel={t("Frequency · Hz", "Frecuencia · Hz")} yLabel="Ω" logX logY />
    <p className="plot-note">{t("The XY curve is Zxy; the YX curve is −Zyx, sign-corrected by the parser for comparison with the 1D antisymmetric convention. The full tensor without this YX sign flip remains in the downloadable artifact. σ applies separately to real and imaginary impedance; it is not an apparent-resistivity uncertainty interval. No model curves or geological truth are available.", "La curva XY es Zxy; la curva YX es −Zyx, con signo corregido por el lector para compararla con la convención antisimétrica 1D. El tensor completo sin esa corrección de signo YX permanece en el artefacto descargable. σ corresponde por separado a impedancia real e imaginaria; no es un intervalo de resistividad aparente. No hay curvas de modelo ni verdad geológica.")}</p>
    <h3>{t("Necessary 1D tensor-compatibility screen", "Control necesario de compatibilidad tensorial 1D")}</h3>
    <dl className="parameter-ledger">
      <div><dt>WRMS Zxx</dt><dd>{format(c.xx_component_wrms)}</dd></div>
      <div><dt>WRMS Zyy</dt><dd>{format(c.yy_component_wrms)}</dd></div>
      <div><dt>{t("Conservative antisymmetry WRMS", "WRMS conservador de antisimetría")}</dt><dd>{format(c.antisymmetry_conservative_wrms)}</dd></div>
      <div><dt>{t("Declared acceptance threshold", "Umbral de aceptación declarado")}</dt><dd>{format(c.threshold)}</dd></div>
      <div><dt>{t("1D inversion eligible", "Apto para inversión 1D")}</dt><dd>{screen.one_d_inversion_eligible ? t("Yes", "Sí") : t("No", "No")}</dd></div>
      <div><dt>{t("Inversion performed", "Inversión realizada")}</dt><dd>{t("No", "No")}</dd></div>
    </dl>
    <p className="plot-note">{t("A failed necessary screen rejects this isotropic-1D interpretation under the stated threshold; it does not determine whether a 2D or 3D geological model is correct. Tensor dimensionality, processing assumptions and site effects require separate analysis.", "Fallar este control necesario rechaza la interpretación isotrópica 1D con el umbral declarado; no determina si un modelo geológico 2D o 3D es correcto. Dimensionalidad del tensor, supuestos de procesamiento y efectos locales requieren análisis aparte.")}</p>
    <h3>{t("Source and parsing record", "Fuente y registro de lectura")}</h3>
    <p>{release?.citation ?? t("Source citation not included in this artifact.", "La cita de origen no figura en este artefacto.")}</p>
    <div className="benchmark-controls">
      {stationUrl && <a href={stationUrl} target="_blank" rel="noopener noreferrer">{t("USGS station record", "Registro de estación USGS")}</a>}
      {releaseDoi && <a href={releaseDoi} target="_blank" rel="noopener noreferrer">{t("EarthScope release DOI", "DOI de publicación EarthScope")}: {release?.release_doi}</a>}
      {transferDoi && <a href={transferDoi} target="_blank" rel="noopener noreferrer">{t("Transfer-function DOI", "DOI de funciones de transferencia")}: {release?.transfer_function_doi}</a>}
    </div>
    {release?.rights && <p>{t("Data rights", "Derechos de datos")}: {release.rights}</p>}
    {release?.note && <p className="plot-note">{release.note}</p>}
    <dl className="parameter-ledger">
      <div><dt>{t("Sounding", "Sondeo")}</dt><dd>{screen.id}</dd></div>
      <div><dt>{t("Frequency samples", "Frecuencias")}</dt><dd>{screen.frequencies_hz.length}</dd></div>
      <div><dt>{t("Parser", "Lector")}</dt><dd>{screen.provenance.parser} · {screen.provenance.parser_version}</dd></div>
      <div><dt>{t("Input → output impedance units", "Unidades de impedancia entrada → salida")}</dt><dd>{screen.provenance.original_units} → {screen.provenance.output_units}</dd></div>
      <div><dt>{t("Orientation handling", "Tratamiento de orientación")}</dt><dd>{screen.provenance.rotation_action}</dd></div>
    </dl>
    <p>SHA-256 · EDI: <code>{entry.source_sha256}</code></p><p>SHA-256 · JSON: <code>{entry.artifact_sha256}</code></p>
  </section>;
}

export function EdiCalibrationResult({ data }: { data: EdiCalibration }) {
  const es = useShellLang() === "es";
  const t = (a: string, b: string) => es ? b : a;
  const [selected, setSelected] = useState(0);
  const layer = Math.min(selected, data.calibration_model.length - 1);
  const series = calibrationSeries(data, layer);
  return <section className="evidence-layout">
    <label className="select-control"><span>{t("Calibration layer", "Capa de calibración")}</span><select className="select" value={layer} onChange={e => setSelected(+e.target.value)}>{data.calibration_model.map((v, i) => <option key={i} value={i}>{i + 1} · {v} Ω m</option>)}</select></label>
    <Plot title={t("Independent repeat-inversion intervals", "Intervalos de inversiones independientes")} x={series.x} series={[{ name: t("Recovered layer", "Capa recuperada"), values: series.models, points: true }, { name: t("Independent calibration truth", "Verdad independiente de calibración"), values: series.oracle, dashed: true }]} band={{ name: `${data.confidence * 100}%`, lower: series.lower, upper: series.upper }} xLabel={t("Independent realization", "Realización independiente")} yLabel="Ω m" />
    <div className="table-scroll"><table className="cmp-table"><thead><tr><th>{t("Layer", "Capa")}</th><th>{t("Measured coverage", "Cobertura medida")}</th><th>{t("Wilson 95% limits", "Límites Wilson 95%")}</th><th>{t("Monte Carlo SE", "Error estándar Monte Carlo")}</th><th>{t("Mean interval width · Ω m", "Ancho medio · Ω m")}</th><th>{t("Model bias · Ω m", "Sesgo · Ω m")}</th></tr></thead><tbody>{data.calibration_model.map((_, i) => <tr key={i}><th scope="row">{i + 1}</th><td>{format(data.coverage_per_layer[i] * 100)}%</td><td>{format(data.coverage_wilson95_lower[i] * 100)}–{format(data.coverage_wilson95_upper[i] * 100)}%</td><td>{format(data.coverage_monte_carlo_standard_error[i])}</td><td>{format(data.mean_width_ohm_m[i])}</td><td>{format(data.bias_ohm_m[i])}</td></tr>)}</tbody></table></div>
    <p className="plot-note">{data.realizations} {t("independent realizations", "realizaciones independientes")}; {data.bootstrap_samples_per_realization} {t("bootstrap members per realization", "miembros bootstrap por realización")}; {data.failures} {t("failed intervals (counted as noncoverage)", "intervalos fallidos (cuentan como no cobertura)")}; {t("seed", "semilla")} {data.seed}. {t("Wilson bounds quantify sampling error of the coverage estimate, not geological resistivity uncertainty. Results apply only to the specified synthetic model and independent Gaussian error law.", "Los límites Wilson cuantifican error muestral de cobertura, no incertidumbre geológica de resistividad. Los resultados se limitan al modelo sintético y ruido gaussiano independiente declarados.")}</p>
  </section>;
}

function EdiCalibrationView({ filename }: { filename: string }) {
  const es = useShellLang() === "es";
  const [data, setData] = useState<EdiCalibration>();
  const [error, setError] = useState("");
  useEffect(() => { const controller = new AbortController(); setData(undefined); setError(""); loadArtifact<EdiCalibration>(ediPath(filename), controller.signal).then(value => { if (value.kind !== "independent_seeded_conditional_bootstrap_coverage" || !value.calibration_model.length || value.rows.length !== value.realizations) throw new Error("Calibration contract mismatch"); setData(value); }).catch(e => { if (e.name !== "AbortError") setError(String(e)); }); return () => controller.abort(); }, [filename]);
  return error ? <p role="alert">{error}</p> : data ? <EdiCalibrationResult key={filename} data={data} /> : <p role="status">{es ? "Cargando calibración…" : "Loading calibration…"}</p>;
}

export function EdiFixtures() {
  const es = useShellLang() === "es";
  const t = (a: string, b: string) => es ? b : a;
  const [bundle, setBundle] = useState<EdiBundle>();
  const [selected, setSelected] = useState("");
  const [run, setRun] = useState<EdiRun>();
  const [error, setError] = useState("");
  const [selectedField, setSelectedField] = useState("");
  const [fieldScreen, setFieldScreen] = useState<EdiFieldScreen>();
  const [fieldError, setFieldError] = useState("");
  useEffect(() => { const controller = new AbortController(); loadArtifact<EdiBundle>("edi/manifest.json", controller.signal).then(data => {
    if (data.schema !== "inverse-earth/edi-bundle/v1" || !data.fixtures.length) throw new Error("EDI bundle contract mismatch");
    data.fixtures.forEach(f => { ediPath(f.source); ediPath(f.artifact); });
    data.field_screens?.forEach(f => { ediPath(f.artifact); if (f.source) ediPath(f.source); });
    setBundle(data); setSelected(data.fixtures[0].id); setSelectedField(data.field_screens?.[0]?.id ?? "");
  }).catch(e => { if (e.name !== "AbortError") setError(String(e)); }); return () => controller.abort(); }, []);
  const fixture = bundle?.fixtures.find(f => f.id === selected);
  const fieldEntry = bundle?.field_screens?.find(f => f.id === selectedField);
  useEffect(() => { if (!fixture) return; const controller = new AbortController(); setRun(undefined); setError(""); loadArtifact<EdiRun>(ediPath(fixture.artifact), controller.signal).then(data => { validateEdiRun(data, fixture); setRun(data); }).catch(e => { if (e.name !== "AbortError") setError(String(e)); }); return () => controller.abort(); }, [fixture]);
  useEffect(() => { if (!fieldEntry) return; const controller = new AbortController(); setFieldScreen(undefined); setFieldError(""); loadArtifact<EdiFieldScreen>(ediPath(fieldEntry.artifact), controller.signal).then(data => { validateEdiFieldScreen(data, fieldEntry); setFieldScreen(data); }).catch(e => { if (e.name !== "AbortError") setFieldError(String(e)); }); return () => controller.abort(); }, [fieldEntry]);
  return <section className="evidence-layout">
    <h2>{t("EDI evidence: measured screening and synthetic inversion", "Evidencia EDI: control medido e inversión sintética")}</h2>
    <p>{t("The measured sounding is screened without inversion. Separate authored synthetic EDI fixtures exercise the full parsing and fixed-thickness inverse workflow; their models and independent oracle must not be read as field results.", "El sondeo medido se evalúa sin inversión. Archivos EDI sintéticos independientes ejercitan lectura e inversión de espesores fijos; sus modelos y referencia independiente no son resultados de campo.")} <Cite id="mtpy" paren /></p>
    {error ? <p role="alert">{t("EDI evidence could not be loaded; no synthetic fallback was generated.", "No se pudo cargar evidencia EDI; no se generó reemplazo sintético.")} {error}</p> : !bundle ? <p role="status">{t("Loading EDI evidence…", "Cargando evidencia EDI…")}</p> : <>
      {!!bundle.field_screens?.length && <section className="evidence-layout">
        <h3>{t("Measured EDI · tensor screen only", "EDI medido · sólo control tensorial")}</h3>
        {bundle.field_screens.length > 1 && <label className="select-control"><span>{t("Measured sounding", "Sondeo medido")}</span><select className="select" value={selectedField} onChange={event => setSelectedField(event.target.value)}>{bundle.field_screens.map(f => <option key={f.id} value={f.id}>{f.label ?? f.id}</option>)}</select></label>}
        {fieldError ? <p role="alert">{t("Measured EDI screening record could not be loaded; no inversion is substituted.", "No se pudo cargar el control EDI medido; no se sustituye por una inversión.")} {fieldError}</p> : fieldScreen && fieldEntry ? <EdiFieldScreenResult key={fieldEntry.id} screen={fieldScreen} entry={fieldEntry} /> : <p role="status">{t("Loading measured tensor screen…", "Cargando control tensorial medido…")}</p>}
      </section>}
      <h3>{t("Authored synthetic EDI inversion fixtures", "Archivos EDI sintéticos con inversión")}</h3>
      <label className="select-control"><span>{t("Original EDI fixture", "Archivo EDI original")}</span><select className="select" value={selected} onChange={e => setSelected(e.target.value)}>{bundle.fixtures.map((f, i) => <option key={f.id} value={f.id}>{i + 1} · {f.truth_ohm_m.length === 1 ? t("Half-space", "Semiespacio") : t("Layered earth", "Tierra estratificada")} · {f.input_units} · {f.rotation_deg}° · {f.noise_added ? t("with noise", "con ruido") : t("no added noise", "sin ruido agregado")}</option>)}</select></label>
      {run && fixture ? <EdiResult key={fixture.id} run={run} fixture={fixture} /> : <p role="status">{t("Loading computed inversion…", "Cargando inversión calculada…")}</p>}
      {!!bundle.calibration?.length && <section>
        <h3>{t("Independent interval-coverage experiments", "Experimentos independientes de cobertura")}</h3>
        <p className="plot-note">{t("Calibration models differ from the displayed fixtures. Reported coverage includes failed interval fits as noncoverage; it is specific to these synthetic models and the stated Gaussian noise law.", "Los modelos de calibración difieren de los archivos mostrados. La cobertura cuenta ajustes fallidos como no cobertura; es específica de estos modelos sintéticos y ruido gaussiano.")}</p>
        <div className="table-scroll"><table className="cmp-table"><thead><tr><th>{t("Calibration", "Calibración")}</th><th>{t("Realizations", "Realizaciones")}</th><th>{t("Layer coverage", "Cobertura por capa")}</th><th>{t("Failures", "Fallos")}</th><th>{t("Record", "Registro")}</th></tr></thead><tbody>{bundle.calibration.map(c => <tr key={c.id}><td>{c.id === "halfspace" ? t("Half-space", "Semiespacio") : t("Layered calibration", "Calibración estratificada")}</td><td>{c.realizations}</td><td>{c.coverage_per_layer.map(v => format(v * 100) + "%").join(" · ")}</td><td>{c.failures}</td><td><a download href={appBase + "data/v2/" + ediPath(c.artifact)}>{t("Download", "Descargar")}</a></td></tr>)}</tbody></table></div>
        {bundle.calibration.map(c => <details key={c.id}><summary>{c.id === "halfspace" ? t("Half-space calibration intervals", "Intervalos de calibración del semiespacio") : t("Layered calibration intervals", "Intervalos de calibración estratificada")}</summary><EdiCalibrationView filename={c.artifact} /></details>)}
      </section>}
      <p className="plot-note">{t("Fixture license", "Licencia de archivos")}: {bundle.license}. {t("Parser dependency", "Dependencia del lector")}: {bundle.parser_dependency}.</p>
    </>}
    <Refs ids={["mtpy", "heagy2017", "scipytrf"]} label={t("References", "Referencias")} />
  </section>;
}
