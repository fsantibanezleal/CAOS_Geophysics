import { useEffect, useState, type ReactNode } from "react";
import {
  Callout,
  Cite,
  Equation,
  InlineMath,
  Refs,
  SubTabs,
  Tabs,
  useShellLang,
} from "@fasl-work/caos-app-shell";
import { Plot } from "../components/ScientificPlots";
import { MethodDiagram } from "../components/MethodDiagram";
import { EdiFixtures } from "../components/EdiFixtures";
import { LiveMT } from "../components/LiveMT";
import { chapters, type Algorithm, type Chapter } from "../data/methods";
import { lessons } from "../data/lessons";
import { methodName, metricInfo, metricValue } from "../data/metrics";
import {
  appBase,
  familyLabels,
  format,
  loadArtifact,
  type Catalog,
  type Family,
  type DetectionValidation,
} from "../science";
import { ApplicabilityWarning, DetectionEvidence, EvaluationStatus } from "../components/ScientificEvidence";
const source = "https://github.com/fsantibanezleal/CAOS_Geophysics/blob/main/";
function useText() {
  const es = useShellLang() === "es";
  return (en: string, sp: string) => (es ? sp : en);
}
function useCatalog() {
  const [catalog, setCatalog] = useState<Catalog>();
  const [error, setError] = useState("");
  useEffect(() => {
    const c = new AbortController();
    loadArtifact<Catalog>("catalog.json", c.signal)
      .then(setCatalog)
      .catch((e) => {
        if (e.name !== "AbortError") setError(String(e));
      });
    return () => c.abort();
  }, []);
  return { catalog, error };
}
function Head({ title, children }: { title: string; children: ReactNode }) {
  return (
    <header className="page-head">
      <h1>{title}</h1>
      <p className="lede">{children}</p>
    </header>
  );
}
function Sources({ ids }: { ids: string[] }) {
  const t = useText();
  return <Refs ids={ids} label={t("References", "Referencias")} />;
}

export function Introduction() {
  const t = useText();
  return (
    <div className="page-body prose">
      <Head
        title={t(
          "Geophysical inverse problems",
          "Problemas inversos geofísicos",
        )}
      >
        {t(
          "Geophysical inversion estimates subsurface properties from measured physical responses. This application compares density, magnetic susceptibility, resistivity and acoustic velocity in controlled synthetic experiments. The relation ",
          "La inversión geofísica estima propiedades del subsuelo a partir de respuestas físicas medidas. Esta aplicación compara densidad, susceptibilidad, resistividad y velocidad acústica en experimentos sintéticos controlados. La relación ",
        )}
        <InlineMath tex="d=F(m)+\epsilon" />
        {t(
          " separates the unknown model, the forward operator and observation error.",
          " separa modelo desconocido, operador directo y error de observación.",
        )}
      </Head>
      <section>
        <h2>
          {t(
            "1. Physical properties and observations",
            "1. Propiedades físicas y observaciones",
          )}
        </h2>
        <p className="measure">
          {t(
            "Gravity anomalies respond to density contrasts; magnetic anomalies respond to magnetization; magnetotelluric impedance responds to electrical resistivity; seismic waveforms respond here to acoustic velocity. These quantities are not interchangeable geological images. Each method requires a different acquisition model, forward equation and interpretation of spatial resolution. The examples include sedimentary basins, intrusive bodies, dipping dykes, conductive layers, faults, salt and low-velocity channels.",
            "La gravedad responde a contrastes de densidad; el magnetismo, a magnetización; la impedancia magnetotelúrica, a resistividad eléctrica; las ondas sísmicas, aquí a velocidad acústica. No son imágenes geológicas intercambiables. Cada método requiere adquisición, ecuación directa e interpretación de resolución diferentes. Los ejemplos incluyen cuencas, intrusiones, diques inclinados, capas conductoras, fallas, sal y canales lentos.",
          )}
        </p>
        <div className="table-scroll">
          <table className="cmp-table">
            <thead>
              <tr>
                {[
                  t("Method", "Método"),
                  t("Unknown", "Incógnita"),
                  t("Observation", "Observación"),
                  t("Geometry", "Geometría"),
                ].map((x) => (
                  <th key={x}>{x}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              <tr>
                <td>{t("Gravity", "Gravedad")}</td>
                <td>Δρ · g/cm³</td>
                <td>g𝓏 · mGal</td>
                <td>
                  {t(
                    "3D prisms / surface stations",
                    "Prismas 3D / estaciones superficiales",
                  )}
                </td>
              </tr>
              <tr>
                <td>{t("Magnetics", "Magnetismo")}</td>
                <td>χ / mₓ,mᵧ,m𝓏 · SI</td>
                <td>TMI · nT</td>
                <td>
                  {t(
                    "3D prisms / uniform inducing field",
                    "Prismas 3D / campo inductor uniforme",
                  )}
                </td>
              </tr>
              <tr>
                <td>MT</td>
                <td>ρ · Ω m</td>
                <td>Z(f) · Ω</td>
                <td>
                  {t(
                    "1D layers / known thicknesses",
                    "Capas 1D / espesores conocidos",
                  )}
                </td>
              </tr>
              <tr>
                <td>FWI</td>
                <td>v · m/s</td>
                <td>
                  {t("Receiver pressure histories", "Historias de presión")}
                </td>
                <td>
                  {t(
                    "2D constant-density acoustics",
                    "Acústica 2D de densidad constante",
                  )}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <Sources ids={["cockett2015", "heagy2017", "virieux2009"]} />
      </section>
      <section>
        <h2>
          {t(
            "2. Forward modelling and discretization",
            "2. Modelación directa y discretización",
          )}
        </h2>
        <p className="measure">
          {t(
            "The forward operator predicts what a specified survey would measure for a candidate earth. It includes receiver locations, source parameters and boundary conditions; these cannot be separated from the interpretation of a result. Potential fields use integrated prism kernels. MT uses complex impedance recursion through layers. Seismic uses finite-difference propagation. Refining a grid improves the representation of geometry and numerical propagation, but cannot replace missing observations.",
            "El operador directo predice lo que mediría un levantamiento para un subsuelo candidato. Incluye receptores, fuentes y fronteras, inseparables de la interpretación. Los campos potenciales usan núcleos prismáticos integrados; MT, recursión compleja entre capas; sísmica, propagación por diferencias finitas. Refinar una malla mejora geometría y propagación numérica, pero no sustituye datos ausentes.",
          )}
        </p>
        <Equation
          tex={String.raw`d_i^{obs}=F_i(m_{true})+\epsilon_i,\qquad G_{ij}=\frac{\partial F_i}{\partial m_j}`}
          caption={t(
            "dᵒᵇˢ is observed data; mtrue is the synthetic model; ε is measurement noise; Gᵢⱼ is sensitivity of observation i to parameter j. For linear potential fields, G does not depend on m.",
            "dᵒᵇˢ son datos observados; mtrue es modelo sintético; ε es ruido; Gᵢⱼ es sensibilidad del dato i al parámetro j. En campos potenciales lineales, G no depende de m.",
          )}
        />
        <MethodDiagram kind="potential" />
        <Sources ids={["simpeggravity", "deepwave"]} />
      </section>
      <section>
        <h2>
          {t(
            "3. Regularization and identifiability",
            "3. Regularización e identificabilidad",
          )}
        </h2>
        <p className="measure">
          {t(
            "Different subsurface models can reproduce similar observations. Regularization selects among these possibilities using explicit preferences such as small coefficients, sparse support, smooth layer transitions or shared boundaries. It does not establish that the selected preference is geologically correct. A reduced data residual and a reduced model error are therefore different outcomes. The benchmark reports both where synthetic truth is available, with no combined score across physical units.",
            "Distintos modelos pueden reproducir datos similares. La regularización selecciona usando preferencias explícitas: coeficientes pequeños, soporte disperso, transiciones suaves o límites compartidos. No establece que esa preferencia sea correcta geológicamente. Reducir residuo de datos y reducir error de modelo son resultados distintos. El benchmark informa ambos cuando existe verdad sintética, sin combinar unidades físicas en un puntaje.",
          )}
        </p>
        <Equation
          tex={String.raw`\widehat m=\arg\min_m\{\Phi_d(F(m),d^{obs})+\beta\Phi_m(m)\}`}
          caption={t(
            "Φd measures data disagreement; Φm encodes a model preference; β controls their relative weight. Each implemented algorithm defines these terms separately; not every history curve includes both.",
            "Φd mide desacuerdo de datos; Φm expresa preferencia de modelo; β pondera ambos. Cada algoritmo define sus términos; no toda curva histórica incluye los dos.",
          )}
        />
        <Equation
          tex={String.raw`\mathrm{RMSE}_m=\sqrt{\frac1M\sum_{j=1}^M(\widehat m_j-m_{true,j})^2}`}
          caption={t(
            "M is the number of model parameters. Model RMSE uses the property units and requires known truth. It does not measure uncertainty and is not available for an unknown field subsurface.",
            "M es número de parámetros. RMSE usa unidades de propiedad y requiere verdad conocida. No mide incertidumbre ni está disponible para un subsuelo de campo desconocido.",
          )}
        />
        <Sources ids={["cockett2015", "crossgradient"]} />
      </section>
      <section>
        <h2>
          {t(
            "4. Experimental calculation and interpretation",
            "4. Cálculo e interpretación experimental",
          )}
        </h2>
        <ol className="measure">
          <li>
            {t(
              "Define the geological geometry, property contrasts and physical units.",
              "Definir geometría, contrastes y unidades.",
            )}
          </li>
          <li>
            {t(
              "Set receivers, sources, frequencies and the numerical domain.",
              "Configurar receptores, fuentes, frecuencias y dominio numérico.",
            )}
          </li>
          <li>
            {t(
              "Generate the forward response; add seeded observation noise and apply the acquisition mask.",
              "Generar respuesta directa; agregar ruido con semilla y aplicar máscara de adquisición.",
            )}
          </li>
          <li>
            {t(
              "Run each inverse algorithm from its declared initialization without using the known solution for checkpoint selection.",
              "Ejecutar cada inversor desde su inicialización declarada sin usar la solución conocida para seleccionar checkpoints.",
            )}
          </li>
          <li>
            {t(
              "Compare predicted observations, residuals and recovered properties. Use the noise and coverage variants to assess sensitivity, not to construct an unsupported probability interval.",
              "Comparar predicciones, residuos y propiedades. Usar variantes de ruido y cobertura para sensibilidad, no para construir intervalos probabilísticos no sustentados.",
            )}
          </li>
        </ol>
        <p className="measure">
          {t(
            "On the App page, Model shows geometry or physical response, Data shows observations and predictions, and Inversion shows recovered properties and numerical histories. Case analysis explains the specific geological question. Experiment selection loads separately computed results; camera rotation and display gain only alter the view. The MT calculator is a separate browser forward calculation.",
            "En App, Modelo muestra geometría o respuesta física; Datos, observaciones y predicciones; Inversión, propiedades recuperadas e historiales. Análisis del caso explica la pregunta geológica. Elegir un experimento carga resultados calculados separadamente; cámara y ganancia sólo modifican la vista. La calculadora MT es un cálculo directo separado en navegador.",
          )}
        </p>
        <Sources ids={["deepwave", "heagy2017"]} />
      </section>
      <section>
        <h2>
          {t(
            "5. Notation and scope of validation",
            "5. Notación y alcance de validación",
          )}
        </h2>
        <ul className="method-symbols">
          {[
            [
              "m: subsurface model; m̂: recovered model.",
              "m: modelo del subsuelo; m̂: modelo recuperado.",
            ],
            [
              "d: observations; F: forward operator.",
              "d: observaciones; F: operador directo.",
            ],
            [
              "G: sensitivity matrix; N: observation count.",
              "G: matriz de sensibilidad; N: cantidad de observaciones.",
            ],
            [
              "M: cell/parameter count; ε: noise.",
              "M: cantidad de celdas/parámetros; ε: ruido.",
            ],
            [
              "σ: component noise standard deviation.",
              "σ: desviación del ruido por componente.",
            ],
            [
              "β: model-penalty weight; λ: structural-coupling weight.",
              "β: peso de penalización; λ: peso de acoplamiento.",
            ],
            [
              "Δρ: density contrast (g/cm³); χ: susceptibility (SI).",
              "Δρ: contraste de densidad (g/cm³); χ: susceptibilidad (SI).",
            ],
            [
              "ρ: electrical resistivity (Ω m); h: layer thickness (m).",
              "ρ: resistividad (Ω m); h: espesor (m).",
            ],
            [
              "Z: complex impedance (Ω); f: frequency (Hz).",
              "Z: impedancia compleja (Ω); f: frecuencia (Hz).",
            ],
            [
              "v: acoustic velocity (m/s); t: time (s).",
              "v: velocidad acústica (m/s); t: tiempo (s).",
            ],
            [
              "θ: neural weights; J: objective function.",
              "θ: pesos neuronales; J: función objetivo.",
            ],
            [
              "c: column density (g/cm³ m) or cross-gradient, as defined locally.",
              "c: densidad integrada (g/cm³ m) o gradiente cruzado según definición local.",
            ],
          ].map(([en, sp]) => (
            <li key={en}>{t(en, sp)}</li>
          ))}
        </ul>
        <Callout
          variant="honest"
          title={t("Synthetic validation", "Validación sintética")}
        >
          {t(
            "Known-model recovery, independent prism checks, homogeneous MT identities and directional gradient tests verify specific calculations. They do not establish field accuracy, unique geology, posterior uncertainty or a new inversion method. External tutorial data are handled separately from the synthetic benchmark.",
            "Recuperación de modelos conocidos, pruebas prismáticas independientes, identidades MT y pruebas de gradiente verifican cálculos específicos. No establecen precisión de campo, geología única, incertidumbre posterior ni un método nuevo. Los datos externos de tutorial se manejan separados del benchmark sintético.",
          )}
        </Callout>
        <Sources ids={["cockett2015", "virieux2009", "goyes2024"]} />
      </section>
    </div>
  );
}

function TheoryChapter({ chapter }: { chapter: Chapter }) {
  const i = useShellLang() === "es" ? 1 : 0;
  const t = useText();
  return (
    <article className="method-article">
      <h2>{chapter.title[i]}</h2>
      {chapter.paragraphs.map((p, k) => (
        <p key={k}>
          {p[i]}
          {k === 0 && (
            <>
              {" "}
              <Cite id={chapter.refs[0]} paren />
            </>
          )}
        </p>
      ))}
      {chapter.equations.map((e, k) => (
        <Equation key={k} tex={e.tex} caption={e.caption[i]} />
      ))}
      <MethodDiagram kind={chapter.id} />
      <Callout
        variant="honest"
        title={t("Assumptions and limitations", "Supuestos y limitaciones")}
      >
        {chapter.assumptions[i]}
      </Callout>
      <Sources ids={chapter.refs} />
    </article>
  );
}
export function Methodology() {
  const t = useText();
  const i = useShellLang() === "es" ? 1 : 0;
  return (
    <div className="page-body prose">
      <Head
        title={t(
          "Forward models and inverse formulations",
          "Modelos directos y formulaciones inversas",
        )}
      >
        {t(
          "These six sections explain what each method measures, its unknown parameters, the governing equations and the assumptions that limit interpretation. The Implementation page specifies the numerical algorithms and constants used to compute the results; the equations here distinguish the physical problem from its discretization.",
          "Estas seis secciones explican lo que mide cada método, sus incógnitas, ecuaciones y supuestos. Implementación especifica los algoritmos numéricos y constantes usados para obtener resultados; aquí se distingue el problema físico de su discretización.",
        )}
      </Head>
      <SubTabs
        orientation="vertical"
        ariaLabel={t("Physical method families", "Familias de métodos físicos")}
        tabs={chapters.map((c) => ({
          id: c.id,
          label: c.title[i],
          content: <TheoryChapter chapter={c} />,
        }))}
      />
    </div>
  );
}

function AlgorithmSection({
  algorithm,
  chapter,
}: {
  algorithm: Algorithm;
  chapter: Chapter;
}) {
  const i = useShellLang() === "es" ? 1 : 0;
  const t = useText();
  return (
    <article className="method-article">
      <h2>{algorithm.title[i]}</h2>
      <p>
        {algorithm.explanation[i]} <Cite id={chapter.refs[0]} paren />
      </p>
      <Equation
        tex={algorithm.equation.tex}
        caption={algorithm.equation.caption[i]}
      />
      <h3>{t("Numerical sequence", "Secuencia numérica")}</h3>
      <ol>
        {algorithm.steps.map((s, k) => (
          <li key={k}>{s[i]}</li>
        ))}
      </ol>
      <h3>
        {t("Constants and stopping rule", "Constantes y regla de parada")}
      </h3>
      <p>{algorithm.settings[i]}</p>
      <h3>
        {t("What the saved history measures", "Qué mide el historial guardado")}
      </h3>
      <p>{algorithm.history[i]}</p>
      <MethodDiagram kind={chapter.id} />
      <Callout
        variant="honest"
        title={t("Interpretation limits", "Límites de interpretación")}
      >
        {algorithm.limitation[i]}
      </Callout>
      <p className="small">
        {t(
          "The inverse calculation runs in the local numerical pipeline. The browser displays its saved models, data predictions and histories; changing the case does not launch a new inverse solve.",
          "El cálculo inverso se ejecuta en el procesamiento numérico local. El navegador muestra modelos, predicciones e historiales guardados; cambiar caso no inicia una nueva inversión.",
        )}
      </p>
      <p>
        <a
          href={
            source +
            "data-pipeline/" +
            {
              potential: "potential",
              mt: "electromagnetics",
              seismic: "seismic",
              joint: "joint",
              cnn: "learning",
              ae: "learning",
            }[chapter.id] +
            ".py"
          }
        >
          {t(
            "Numerical source for this method",
            "Código numérico de este método",
          )}
        </a>
      </p>
      <Sources ids={chapter.refs} />
    </article>
  );
}
function ValidationSection() {
  const t = useText();
  return (
    <article className="method-article">
      <h2>
        {t(
          "Numerical checks and reproducibility",
          "Verificación numérica y reproducibilidad",
        )}
      </h2>
      <p>
        {t(
          "A numerical check needs an oracle independent of the output it is checking. Gravity is compared with a separate prism implementation; MT with homogeneous-halfspace identities and split-layer equivalence; differentiable MT and acoustic propagation with central directional differences. Passing these checks establishes local numerical agreement, not geological uniqueness.",
          "Una prueba necesita una referencia independiente de su salida. Gravedad se compara con otra implementación prismática; MT con identidades de semiespacio y equivalencia al dividir capas; gradientes MT y acústicos con diferencias direccionales centrales. Aprobar establece acuerdo numérico local, no unicidad geológica.",
        )}
      </p>
      <Equation
        tex={String.raw`\frac{J(m+\epsilon q)-J(m-\epsilon q)}{2\epsilon}\approx\nabla J(m)^Tq`}
        caption={t(
          "q is a chosen perturbation direction and ε a small step. Agreement checks the directional derivative. MT uses relative tolerance 10⁻⁶; the float64 CUDA acoustic test uses 2×10⁻³. These are test tolerances, not model accuracy claims.",
          "q es dirección de perturbación y ε un paso pequeño. El acuerdo verifica derivada direccional. MT usa tolerancia relativa 10⁻⁶; la prueba acústica CUDA float64 usa 2×10⁻³. Son tolerancias de prueba, no precisión de modelo.",
        )}
      />
      <h3>
        {t(
          "Saved arrays and exact reproduction",
          "Arreglos guardados y reproducción",
        )}
      </h3>
      <p>
        {t(
          "Potential fields are stored depth–northing–easting with easting fastest. Seismic sections are depth–distance; gathers are shot–receiver–time. Export retains seven significant digits, so checking observed minus predicted against a stored residual requires a rounding tolerance. Checkpoints carry layer dimensions and weight values; reloaded CPU predictions are compared with saved results. GPU floating-point execution need not be bitwise identical across hardware.",
          "Campos potenciales se guardan profundidad–norte–este, con este más rápido. Secciones sísmicas: profundidad–distancia; registros: disparo–receptor–tiempo. Se exportan siete cifras significativas; verificar observación menos predicción requiere tolerancia de redondeo. Checkpoints contienen dimensiones y pesos; sus predicciones CPU se comparan con resultados guardados. GPU no garantiza identidad bit a bit entre equipos.",
        )}
      </p>
      <h3>
        {t(
          "Running the numerical calculation",
          "Ejecución del cálculo numérico",
        )}
      </h3>
      <pre className="codeblock">
        <code>
          {
            "./scripts/setup.ps1 -Gpu\n./scripts/precompute.ps1\n.venv-pipeline/Scripts/python tests/run_validation.py\ncd frontend\nnpm ci\nnpm test\nnpm run build"
          }
        </code>
      </pre>
      <p>
        {t(
          "The build copies already computed results. SimPEG/SciPy solve potential-field systems; PyTorch/Deepwave run differentiable and learned computations on the local GPU when available. GitHub Pages and the VPS serve static files. Only the layered MT forward calculator recomputes a physical response in the browser.",
          "El build copia resultados calculados. SimPEG/SciPy resuelven campos potenciales; PyTorch/Deepwave ejecutan cálculos diferenciables y aprendidos en GPU local disponible. Pages y VPS sirven archivos estáticos. Sólo la calculadora directa MT recalcula respuesta física en navegador.",
        )}
      </p>
      <Callout
        variant="honest"
        title={t("What is not validated", "Qué no está validado")}
      >
        {t(
          "Numerical checks do not establish field-scale performance, posterior coverage or universal learned generalization. The joint methods use a matched uncoupled comparator and an explicit GMM prior; synthetic recovery is scored separately from execution. Conditional noise-bootstrap coverage is measured, not assumed to equal the nominal interval level. Mesh refinement is numerical discretization, not extra survey information.",
          "Las pruebas numéricas no establecen rendimiento de campo, cobertura posterior ni generalización universal. Los métodos conjuntos usan referencia desacoplada equivalente y prior GMM explícito; recuperación sintética se evalúa separada de ejecución. Se mide cobertura de ruido bootstrap, sin suponer que iguala nivel nominal. Refinar malla es discretización, no información adicional.",
        )}
      </Callout>
      <Sources ids={["cockett2015", "deepwave", "scipytrf"]} />
    </article>
  );
}
export function Implementation() {
  const t = useText();
  const i = useShellLang() === "es" ? 1 : 0;
  const groups = [
    ...chapters
      .slice(0, 4)
      .map((c) => ({
        id: c.id,
        label: c.title[i],
        content: (
          <SubTabs
            orientation="vertical"
            ariaLabel={t("Numerical algorithms", "Algoritmos numéricos")}
            tabs={c.algorithms.map((a) => ({
              id: a.id,
              label: a.title[i],
              content: <AlgorithmSection algorithm={a} chapter={c} />,
            }))}
          />
        ),
      })),
    {
      id: "learning",
      label: t("Neural models", "Modelos neuronales"),
      content: (
        <SubTabs
          orientation="vertical"
          ariaLabel={t("Neural algorithms", "Algoritmos neuronales")}
          tabs={chapters
            .slice(4)
            .map((c) => ({
              id: c.id,
              label: c.title[i],
              content: (
                <AlgorithmSection algorithm={c.algorithms[0]} chapter={c} />
              ),
            }))}
        />
      ),
    },
    {
      id: "validation",
      label: t("Numerical checks", "Verificación numérica"),
      content: <ValidationSection />,
    },
  ];
  return (
    <div className="page-body prose">
      <Head
        title={t(
          "Numerical algorithms and solver settings",
          "Algoritmos numéricos y configuración de solvers",
        )}
      >
        {t(
          "This page specifies how the implemented inverse calculations are performed: parameter transformations, discrete objectives, matrix solves or gradient updates, regularization, initialization and stopping rules. Each algorithm also identifies what its recorded history measures, because data error, penalized loss and validation error are different quantities.",
          "Esta página especifica cómo se calculan las inversiones: transformaciones, objetivos discretos, soluciones matriciales o gradientes, regularización, inicialización y parada. También identifica qué mide cada historial: error de datos, pérdida penalizada y error de validación son cantidades distintas.",
        )}
      </Head>
      <Tabs
        ariaLabel={t("Algorithm groups", "Grupos de algoritmos")}
        tabs={groups}
      />
    </div>
  );
}

function CaseProtocol() {
  const t = useText();
  const i = useShellLang() === "es" ? 1 : 0;
  const { catalog, error } = useCatalog();
  const [selected, setSelected] = useState("GRAVITY_INTRUSION");
  const l = lessons[selected];
  return (
    <>
      <label className="select-control">
        <span>{t("Geological case", "Caso geológico")}</span>
        <select
          className="select"
          value={selected}
          onChange={(e) => setSelected(e.target.value)}
        >
          {catalog?.cases.map((c) => (
            <option key={c.id} value={c.id}>
              {i ? c.name_es : c.name}
            </option>
          ))}
        </select>
      </label>
      {error && <p role="alert">{error}</p>}
      <h3>{l.question[i]}</h3>
      <p>{l.read[i]}</p>
      <h3>{t("Comparison", "Comparación")}</h3>
      <p>{l.try[i]}</p>
      <Callout
        variant="honest"
        title={t("Inference limit", "Límite de inferencia")}
      >
        {l.limit[i]}
      </Callout>
    </>
  );
}
export function Experiments() {
  const t = useText();
  return (
    <div className="page-body prose">
      <Head
        title={t(
          "Experimental design and controlled conditions",
          "Diseño experimental y condiciones controladas",
        )}
      >
        {t(
          "Each synthetic geometry is evaluated under a reference survey and five modified conditions. The comparisons separate changes in property contrast, noise, acquisition, available observations and regularization. A case uses a fixed random seed, but the same seed does not make every modified dataset an identical-noise paired experiment.",
          "Cada geometría sintética se evalúa con un levantamiento de referencia y cinco modificaciones. Se comparan contraste, ruido, adquisición, observaciones disponibles y regularización. Cada caso usa semilla fija, pero eso no convierte todos los datos modificados en pares con ruido idéntico.",
        )}
      </Head>
      <Tabs
        ariaLabel={t("Experiment protocols", "Protocolos experimentales")}
        tabs={[
          {
            id: "cases",
            label: t("Case design", "Diseño de casos"),
            content: (
              <section>
                <h2>{t("Geological hypotheses", "Hipótesis geológicas")}</h2>
                <p>
                  {t(
                    "Potential-field cases vary geometry and sign, not just the position of one common anomaly. MT changes the layer sequence; seismic changes interfaces and lateral structure. Shared and conflicting joint cases test the structural prior. The learned cases test geometries withheld from training. Reference and modified conditions are separate forward/inverse calculations; changing colour limits or camera position is not an experiment.",
                    "Los campos potenciales varían geometría y signo, no sólo posición de una anomalía común. MT cambia capas; sísmica cambia interfaces y estructura lateral. Los casos conjuntos prueban el prior estructural. Los aprendidos prueban geometrías excluidas. Referencia y modificaciones son cálculos directos/inversos separados; cambiar color o cámara no es un experimento.",
                  )}
                </p>
                <CaseProtocol />
                <Sources ids={["cockett2015", "crossgradient"]} />
              </section>
            ),
          },
          {
            id: "acquisition",
            label: t("Acquisition", "Adquisición"),
            content: (
              <section>
                <h2>
                  {t(
                    "Sampling and information loss",
                    "Muestreo y pérdida de información",
                  )}
                </h2>
                <p>
                  {t(
                    "Potential-field acquisition raises the receiver plane from 60 to 180 m without changing the subsurface. Coverage retains alternating stations. MT acquisition extends the frequency range to 0.001–100 Hz while keeping 36 logarithmic samples; it therefore changes frequency spacing as well as the low-frequency endpoint. Seismic acquisition changes the source to 5 Hz; reduced coverage uses 20 receivers instead of 40. These are different physical perturbations, not a common severity axis.",
                    "En potenciales se eleva el plano de 60 a 180 m sin cambiar subsuelo; cobertura retiene estaciones alternas. MT extiende a 0,001–100 Hz conservando 36 muestras logarítmicas, por lo que cambia espaciado además del extremo inferior. Sísmica cambia fuente a 5 Hz; cobertura usa 20 receptores en vez de 40. Son perturbaciones físicas distintas, no un eje común de severidad.",
                  )}
                </p>
                <div className="table-scroll">
                  <table className="cmp-table">
                    <thead>
                      <tr>
                        <th>{t("Family", "Familia")}</th>
                        <th>{t("Reference", "Referencia")}</th>
                        <th>{t("Reduced coverage", "Cobertura reducida")}</th>
                        <th>{t("Scoring population", "Población evaluada")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>{t("Potential fields", "Campos potenciales")}</td>
                        <td>256 · 60 m</td>
                        <td>128</td>
                        <td>
                          {t(
                            "Active stations for scalar WRMS",
                            "Estaciones activas para WRMS escalar",
                          )}
                        </td>
                      </tr>
                      <tr>
                        <td>MT</td>
                        <td>36 · 0.01–100 Hz</td>
                        <td>18</td>
                        <td>
                          {t("Active / withheld real components separately; legacy complex WRMS over all frequencies", "Componentes reales activas / omitidas por separado; WRMS complejo legado en todas las frecuencias")}
                        </td>
                      </tr>
                      <tr>
                        <td>FWI</td>
                        <td>3 × 40</td>
                        <td>3 × 20</td>
                        <td>
                          {t(
                            "Active and withheld receiver traces separately",
                            "Trazas activas y receptores omitidos por separado",
                          )}
                        </td>
                      </tr>
                      <tr>
                        <td>{t("Joint", "Conjunta")}</td>
                        <td>256 + 256</td>
                        <td>128 + 128</td>
                        <td>
                          {t(
                            "Active and withheld gravity/magnetic stations separately",
                            "Estaciones gravimétricas/magnéticas activas y omitidas por separado",
                          )}
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <MethodDiagram kind="seismic" />
                <Sources ids={["simpeggravity", "deepwave", "heagy2017"]} />
              </section>
            ),
          },
          {
            id: "noise",
            label: t("Noise and contrast", "Ruido y contraste"),
            content: (
              <section>
                <h2>
                  {t("Observation-noise definitions", "Definiciones del ruido")}
                </h2>
                <p>
                  {t(
                    "Potential-field noise is independent Gaussian with standard deviation 2.5% of the clean-field standard deviation, increased to 14% in the noisy condition. Gravity uses a 0.006 mGal floor and magnetics a 0.2 nT floor. MT noise scales each real and imaginary component by 2.5% of clean impedance magnitude, or 10%. Seismic noise is 1% or 8% of clean pressure-amplitude standard deviation. These are simulator noise models, not a description of cultural interference or instrument drift.",
                    "El ruido potencial es gaussiano independiente con desviación de 2,5% de la desviación del campo limpio, elevada a 14%. Gravedad usa piso de 0,006 mGal y magnetismo de 0,2 nT. En MT cada componente real e imaginaria usa 2,5% de magnitud limpia o 10%. Sísmica usa 1% u 8% de desviación de amplitud. Son modelos sintéticos, no contaminación cultural ni deriva instrumental.",
                  )}
                </p>
                <Equation
                  tex={String.raw`\epsilon_g\sim\mathcal N(0,\sigma_g^2),\quad \epsilon_Z=\sigma_Z(\xi_1+i\xi_2),\quad \xi_1,\xi_2\sim\mathcal N(0,1)`}
                  caption={t(
                    "εg is real-valued potential-field noise; εZ is complex impedance noise; ξ₁ and ξ₂ are independent standard Gaussian values. Therefore E(|εZ/σZ|²) = 2.",
                    "εg es ruido real de campos potenciales; εZ ruido complejo; ξ₁ y ξ₂ son gaussianas estándar independientes. Por tanto E(|εZ/σZ|²) = 2.",
                  )}
                />
                <h3>{t("Property contrast", "Contraste de propiedades")}</h3>
                <p>
                  {t(
                    "Potential-property and MT-resistivity contrasts multiply by 1.5. Seismic multiplies the difference from 1,800 m/s by 1.15, not all velocities by 1.5. Signal-dependent noise scales may also change when contrast changes; a contrast comparison is not automatically a fixed-absolute-noise test.",
                    "Potenciales y resistividad MT se multiplican por 1,5. Sísmica multiplica la diferencia respecto a 1.800 m/s por 1,15, no todas las velocidades por 1,5. El ruido dependiente de señal puede cambiar al cambiar contraste; no es automáticamente una prueba de ruido absoluto fijo.",
                  )}
                </p>
                <Sources ids={["cockett2015", "heagy2017", "deepwave"]} />
              </section>
            ),
          },
          {
            id: "regularization",
            label: t("Regularization", "Regularización"),
            content: (
              <section>
                <h2>
                  {t(
                    "Changes in the imposed prior",
                    "Cambios en el prior impuesto",
                  )}
                </h2>
                <p>
                  {t(
                    "The potential-field condition multiplies discrepancy-selected beta by 0.25/0.018; beta itself depends on observed data and uncertainty. MT changes beta from 0.001 to 0.3; seismic from 0.001 to 0.03. Joint structural or mixture strength changes from 1 to 4 while retaining the matched independent initialization and spatial terms. CNN/autoencoder checkpoints remain frozen; that condition changes their classical comparator only.",
                    "En potenciales se multiplica beta elegida por discrepancia por 0,25/0,018; beta depende de datos e incertidumbre. MT cambia beta 0,001 a 0,3; sísmica 0,001 a 0,03. La fuerza conjunta estructural o de mezcla cambia 1 a 4 conservando inicialización independiente y términos espaciales. Checkpoints CNN/autoencoder se congelan; sólo cambia su comparador clásico.",
                  )}
                </p>
                <Equation
                  tex={String.raw`\Delta E_m=E_m(\text{modified})-E_m(\text{reference}),\quad \Delta E_d=E_d(\text{modified})-E_d(\text{reference})`}
                  caption={t(
                    "Em is a chosen model error and Ed a data error with unchanged definitions and units. Reporting both deltas separates model recovery from data fitting; it does not combine them into a score.",
                    "Em es error de modelo y Ed error de datos con definición y unidades fijas. Ambas diferencias separan recuperación de ajuste, sin combinarlos en un puntaje.",
                  )}
                />
                <MethodDiagram kind="joint" />
                <Callout
                  variant="honest"
                  title={t(
                    "Regularization is not validation",
                    "Regularizar no es validar",
                  )}
                >
                  {t(
                    "A smoother or more compact model can have larger error. The direction of the result must be read from the computed metrics, not assumed from the chosen penalty.",
                    "Un modelo más suave o compacto puede tener mayor error. El resultado debe leerse de las métricas calculadas, no suponerse por la penalización.",
                  )}
                </Callout>
                <Sources ids={["cockett2015", "crossgradient"]} />
              </section>
            ),
          },
          {
            id: "learning",
            label: t("Learning protocol", "Protocolo aprendido"),
            content: (
              <section>
                <h2>
                  {t(
                    "Splits, checkpoint selection and data provenance",
                    "Particiones, selección y procedencia",
                  )}
                </h2>
                <MethodDiagram kind="protocol" />
                <p>
                  {t(
                    "Training, validation and test contain 800, 160 and 160 independent complete realizations. Input normalization is fitted only on training data. Validation selects checkpoints and sets the autoencoder threshold; the test set does neither. Oblique and ring geometries are withheld from the generator families. No field observations enter network training.",
                    "Entrenamiento, validación y prueba contienen 800, 160 y 160 realizaciones completas independientes. Sólo entrenamiento fija la normalización. Validación selecciona checkpoints y umbral; prueba no hace ninguna de esas tareas. Geometrías oblicua y anular quedan excluidas del generador. No se entrena con observaciones de campo.",
                  )}
                </p>
                <div className="table-scroll">
                  <table className="cmp-table">
                    <thead>
                      <tr>
                        <th>{t("Source", "Fuente")}</th>
                        <th>{t("Use", "Uso")}</th>
                        <th>{t("Distribution", "Distribución")}</th>
                      </tr>
                    </thead>
                    <tbody>
                      <tr>
                        <td>
                          {t(
                            "Original synthetic geology",
                            "Geología sintética original",
                          )}
                        </td>
                        <td>
                          {t(
                            "Case matrix and network splits",
                            "Matriz de casos y particiones",
                          )}
                        </td>
                        <td>CC-BY-4.0</td>
                      </tr>
                      <tr>
                        <td>
                          {t(
                            "SimPEG tutorial archives",
                            "Archivos de tutorial SimPEG",
                          )}
                        </td>
                        <td>
                          {t(
                            "Local ingestion / preprocessing checks",
                            "Ingesta y preprocesamiento local",
                          )}
                        </td>
                        <td>
                          {t(
                            "Source link; raw archives not mirrored",
                            "Enlace a fuente; archivos sin redistribuir",
                          )}
                        </td>
                      </tr>
                      <tr>
                        <td>
                          {t(
                            "Python geophysical-inversion course",
                            "Curso de inversión geofísica Python",
                          )}
                        </td>
                        <td>
                          {t(
                            "Teaching reference; no copied data or notebooks",
                            "Referencia docente; sin copiar datos ni notebooks",
                          )}
                        </td>
                        <td>
                          <a href="https://github.com/Anagabrielamantilla/inversion-geofisica-python">
                            {t("Original repository", "Repositorio original")}
                          </a>
                        </td>
                      </tr>
                    </tbody>
                  </table>
                </div>
                <Callout
                  variant="honest"
                  title={t("Matched baseline and transfer limits", "Referencia comparable y límites de transferencia")}
                >
                  {t(
                    "The held-out classical and CNN comparison uses exactly identical noisy observations and the same integrated-column targets. Classical spatial L2 selects beta by discrepancy. Geometric transfer is evaluated separately on withheld families; mean test error does not establish superiority for each case or transfer to field surveys.",
                    "La comparación clásica/CNN usa observaciones ruidosas exactamente idénticas y los mismos objetivos de columnas. L2 espacial elige beta por discrepancia. La transferencia geométrica se evalúa aparte en familias omitidas; el error medio no establece superioridad en cada caso ni transferencia a campo.",
                  )}
                </Callout>
                <Sources ids={["cockett2015", "adam"]} />
              </section>
            ),
          },
          {
            id: "live",
            label: t("MT forward and EDI evidence", "MT directo y evidencia EDI"),
            content: (
              <>
                <SubTabs ariaLabel={t("MT experiments", "Experimentos MT")} tabs={[{id:"forward",label:t("Live forward response","Respuesta directa en vivo"),content:<LiveMT />},{id:"edi",label:t("EDI fixtures and inversion","Archivos EDI e inversión"),content:<EdiFixtures />}]} />
                <Sources ids={["heagy2017"]} />
              </>
            ),
          },
        ]}
      />
    </div>
  );
}

export function Benchmark() {
  const t = useText();
  const es = useShellLang() === "es";
  const { catalog, error } = useCatalog();
  const [family, setFamily] = useState<Family>("gravity");
  const [method, setMethod] = useState("l2");
  const [metric, setMetric] = useState("model_rmse");
  const [detection, setDetection] = useState<DetectionValidation>();
  useEffect(() => {
    if (family !== "learned") return;
    const c = new AbortController();
    loadArtifact<{ novelty_evaluation?: DetectionValidation }>("models/training.json", c.signal).then(data => setDetection(data.novelty_evaluation)).catch(e => { if (e.name !== "AbortError") setDetection(undefined); });
    return () => c.abort();
  }, [family]);
  const cases = catalog?.cases.filter((c) => c.family === family) ?? [];
  const methods = Object.assign({}, ...cases.flatMap(c => c.variants.map(v => v.methods)));
  const selectedMethod = methods[method] ? method : Object.keys(methods)[0];
  const metrics = Array.from(new Set(cases.flatMap(c => c.variants.flatMap(v => Object.entries(v.methods[selectedMethod]?.metrics ?? {}).filter(([, value]) => metricValue(value) !== undefined).map(([key]) => key)))));
  const selectedMetric = metrics.includes(metric)
    ? metric
    : ([
        "baseline_ratio",
        "model_rmse_ratio",
        "model_error_ratio",
        "model_rmse",
        "velocity_rmse",
        "log_model_rmse",
        "column_rmse",
        "wrms",
        "relative_mse",
        "reconstruction_mse",
      ].find((k) => metrics.includes(k)) ?? metrics[0]);
  const info = metricInfo(selectedMetric, family, selectedMethod, es);
  return (
    <div className="page-body prose">
      <Head
        title={t(
          "Data fit, model error and sensitivity to conditions",
          "Ajuste, error de modelo y sensibilidad a condiciones",
        )}
      >
        {t(
          "Results are evaluated against known synthetic models. Select a physical family, an algorithm and a metric to compare the six experimental conditions within each geometry. Metrics have different populations and units; a data-fit improvement is not equivalent to an improvement in recovered properties.",
          "Los resultados se evalúan contra modelos sintéticos conocidos. Seleccione familia, algoritmo y métrica para comparar seis condiciones en cada geometría. Las métricas tienen distintas poblaciones y unidades; mejorar ajuste no equivale a mejorar propiedades recuperadas.",
        )}
      </Head>
      {error && <p role="alert">{error}</p>}
      <div className="benchmark-controls">
        <label className="select-control">
          <span>{t("Physical family", "Familia física")}</span>
          <select
            className="select"
            aria-label={t("Family", "Familia")}
            value={family}
            onChange={(e) => setFamily(e.target.value as Family)}
          >
            {Object.entries(familyLabels).map(([k, v]) => (
              <option key={k} value={k}>
                {v[es ? 1 : 0]}
              </option>
            ))}
          </select>
        </label>
        <label className="select-control">
          <span>{t("Algorithm", "Algoritmo")}</span>
          <select
            className="select"
            aria-label={t("Method", "Método")}
            value={selectedMethod ?? ""}
            onChange={(e) => setMethod(e.target.value)}
          >
            {Object.keys(methods).map((k) => (
              <option key={k} value={k}>
                {methodName(k, es)}
              </option>
            ))}
          </select>
        </label>
        <label className="select-control">
          <span>{t("Metric", "Métrica")}</span>
          <select
            className="select"
            aria-label={t("Metric", "Métrica")}
            value={selectedMetric ?? ""}
            onChange={(e) => setMetric(e.target.value)}
          >
            {metrics.map((k) => (
              <option key={k} value={k}>
                {metricInfo(k, family, selectedMethod, es).label}
              </option>
            ))}
          </select>
        </label>
      </div>
      {catalog && selectedMetric && (
        <>
          <section>
            <h2>
              {info.label} · {info.unit}
            </h2>
            <p className="measure">{info.description}</p>
            <Plot
              title={t(
                "Condition comparison by geological case",
                "Comparación de condiciones por caso",
              )}
              x={Array.from({ length: Math.max(...cases.map(c => c.variants.length)) }, (_, i) => i + 1)}
              series={cases.map((c, i) => ({
                name: es ? c.name_es : c.name,
                values: c.variants.map((v) =>
                  metricValue(v.methods[selectedMethod]?.metrics[selectedMetric]) ?? NaN,
                ),
                color: [
                  "var(--color-accent)",
                  "var(--color-accent-2)",
                  "var(--color-magenta)",
                  "var(--color-warn)",
                ][i % 4],
              }))}
              xLabel={t(
                "1 Reference · 2 Contrast · 3 Noise · 4 Acquisition · 5 Coverage · 6 Regularization",
                "1 Referencia · 2 Contraste · 3 Ruido · 4 Adquisición · 5 Cobertura · 6 Regularización",
              )}
              yLabel={info.label + " [" + info.unit + "]"}
            />
            <div className="table-scroll">
              <table className="cmp-table">
                <thead>
                  <tr>
                    <th>{t("Case", "Caso")}</th>
                    {cases[0].variants.map((v) => (
                      <th key={v.id}>{es ? v.name_es : v.name}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {cases.map((c) => (
                    <tr key={c.id}>
                      <td>{es ? c.name_es : c.name}</td>
                      {c.variants.map((v) => (
                        <td key={v.id}>
                          <a
                            title={t(
                              "Download the numerical result",
                              "Descargar resultado numérico",
                            )}
                            href={appBase + "data/v2/" + v.path}
                          >
                            {metricValue(v.methods[selectedMethod]?.metrics[selectedMetric]) === undefined ? t("Unavailable", "No disponible") : format(metricValue(v.methods[selectedMethod]?.metrics[selectedMetric])!)}
                          </a>
                          {v.methods[selectedMethod] && <><EvaluationStatus method={v.methods[selectedMethod]} /><ApplicabilityWarning method={v.methods[selectedMethod]} /></>}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="small">
              {t(
                "Lines connect categorical conditions for readability; the horizontal axis is not a continuous parameter sweep. Each linked number opens the complete numerical result.",
                "Las líneas unen categorías para facilitar lectura; el eje no es un barrido continuo. Cada número enlaza al resultado numérico completo.",
              )}
            </p>
            <Sources
              ids={
                family === "mt"
                  ? ["heagy2017"]
                  : family === "seismic"
                    ? ["deepwave"]
                    : family === "joint"
                      ? ["crossgradient"]
                      : ["cockett2015"]
              }
            />
          </section>
          <section>
            <h2>
              {t(
                "Reference-condition method comparison",
                "Comparación de métodos en referencia",
              )}
            </h2>
            <p className="measure">
              {t(
                "The table compares the selected metric across algorithms for the same reference observations. A dash means that the algorithm does not export a comparable metric, not that its error is zero. Model norms and thresholds are not accuracy scores.",
                "La tabla compara la métrica elegida entre algoritmos para observaciones de referencia. Un guion significa que no hay una métrica comparable, no error cero. Normas y umbrales no son puntajes de precisión.",
              )}
            </p>
            <div className="table-scroll">
              <table className="cmp-table">
                <thead>
                  <tr>
                    <th>{t("Case", "Caso")}</th>
                    {Object.keys(methods).map((k) => (
                      <th key={k}>{methodName(k, es)}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {cases.map((c) => (
                    <tr key={c.id}>
                      <td>{es ? c.name_es : c.name}</td>
                      {Object.keys(methods).map((k) => (
                        <td key={k}>
                          {metricValue(c.variants[0].methods[k]?.metrics[selectedMetric]) !== undefined
                            ? format(
                                Number(
                                  c.variants[0].methods[k].metrics[
                                    selectedMetric
                                  ],
                                ),
                              )
                            : "–"}
                          {c.variants[0].methods[k] && <EvaluationStatus method={c.variants[0].methods[k]} />}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <Callout
              variant="honest"
              title={t(
                "Interpretation of the comparison",
                "Interpretación de la comparación",
              )}
            >
              {family === "learned"
                ? t(
                    "CNN column error is comparable only with the exported classical column projection on the same observations and target, not with 3D cell RMSE or autoencoder observation error. The comparison retains signs and physical units, and shows the CNN/classical ratio. Withheld-family misses remain visible in the detector confusion counts.",
                    "El error de columna CNN sólo se compara con la proyección clásica exportada en las mismas observaciones y objetivo, no con RMSE 3D ni error de observaciones del autoencoder. Se conservan signos y unidades y se muestra razón CNN/clásico. Fallos de familias omitidas permanecen en la matriz del detector.",
                  )
                : family === "mt"
                  ? t(
                      "The three MT solvers share resistivity bounds, starting profile and complete real-component objective normalization. Their parameterizations and optimizer budgets differ. Data agreement, local identifiability and known synthetic layer recovery are separate diagnostics; bootstrap spread is conditional, not posterior uncertainty.",
                      "Los tres métodos MT comparten cotas, perfil inicial y normalización completa por componente real. Difieren en parametrización y presupuesto. Ajuste, identificabilidad local y recuperación sintética son diagnósticos separados; dispersión bootstrap es condicional, no incertidumbre posterior.",
                    )
                  : t(
                      "The condition matrix consists of separate seeded experiments, not posterior samples. When an explicit noise ensemble is supplied, its conditioning and measured coverage are displayed separately. Use active and withheld residuals, baseline model error and the stated assumptions together; one synthetic geometry cannot establish field performance.",
                      "La matriz contiene experimentos con semillas separadas, no muestras posteriores. Cuando se aporta conjunto de ruido explícito se muestran aparte condicionamiento y cobertura medida. Considere residuos activos/omitidos, error respecto a referencia y supuestos; una geometría sintética no establece rendimiento de campo.",
                    )}
            </Callout>
            <Sources
              ids={
                family === "mt"
                  ? ["scipytrf", "goyes2024"]
                  : ["cockett2015", "adam"]
              }
            />
          </section>
        </>
      )}
      {family === "learned" && <DetectionEvidence data={detection} />}
      <section>
        <h2>
          {t(
            "Training and verification records",
            "Registros de entrenamiento y verificación",
          )}
        </h2>
        <p className="measure">
          {t(
            "The training record contains split counts, normalization, checkpoint hashes, validation curves and per-realization test errors. Numerical tests separately check forward identities, gradients and serialization. Neither record supplies posterior credible intervals.",
            "El registro contiene particiones, normalización, hashes, curvas y errores por realización de prueba. Las pruebas numéricas verifican identidades, gradientes y serialización por separado. Ninguno aporta intervalos posteriores.",
          )}
        </p>
        <p>
          <a href={appBase + "data/v2/models/training.json"}>
            {t(
              "Training and held-out results",
              "Entrenamiento y resultados independientes",
            )}
          </a>{" "}
          ·{" "}
          <a href={source + "docs/validation/results.md"}>
            {t("Numerical validation report", "Informe de validación numérica")}
          </a>
        </p>
        <Sources ids={["cockett2015", "deepwave", "adam"]} />
      </section>
    </div>
  );
}
