import { useEffect, useState } from "react";
import { Equation, Refs as ShellRefs, Tabs, useShellLang } from "@fasl-work/caos-app-shell";
function Refs({ids}:{ids:string[]}) { const es=useShellLang()==='es';return <ShellRefs ids={ids} label={es?'Referencias':'References'}/>; }
import { Plot } from "../components/ScientificPlots";
import { lessons } from "../data/lessons";
import {
  appBase,
  familyLabels,
  format,
  loadArtifact,
  type Catalog,
  type Family,
} from "../science";
const source = "https://github.com/fsantibanezleal/CAOS_Geophysics/blob/main/";
const useText = () => {
  const es = useShellLang() === "es";
  return (en: string, sp: string) => (es ? sp : en);
};
function useCatalog() {
  const [catalog, setCatalog] = useState<Catalog>();
  const [error, setError] = useState("");
  useEffect(() => {
    loadArtifact<Catalog>("catalog.json")
      .then(setCatalog)
      .catch((e) => setError(String(e)));
  }, []);
  return { catalog, error };
}
function Head({
  kicker,
  title,
  children,
}: {
  kicker: string;
  title: string;
  children: React.ReactNode;
}) {
  return (
    <header className="page-head">
      <span className="small-caps">{kicker}</span>
      <h1>{title}</h1>
      <p className="lede">{children}</p>
    </header>
  );
}

export function Introduction() {
  const t = useText();
  return (
    <div className="page-body prose">
      <Head
        kicker={t("FIELD NOTES / 01", "NOTAS DE CAMPO / 01")}
        title={t(
          "The earth is not a photograph.",
          "La Tierra no es una fotografía.",
        )}
      >
        {t(
          "We observe gravity, magnetic fields, electromagnetic impedance and travelling waves. Geology must be inferred from those responses. This observatory lets you inspect where that inference succeeds, where it is ambiguous, and where a convincing image is wrong.",
          "Observamos gravedad, campos magnéticos, impedancia electromagnética y ondas viajeras. La geología debe inferirse desde esas respuestas. Este observatorio permite inspeccionar dónde la inferencia funciona, dónde es ambigua y dónde una imagen convincente está equivocada.",
        )}
      </Head>
      <div className="process-diagram">
        {[
          [
            t("01 / EARTH", "01 / TIERRA"),
            t("Construct geology", "Construir geología"),
            t(
              "A basin, dyke, aquifer, fault or salt dome. Known truth makes error measurable.",
              "Cuenca, dique, acuífero, falla o domo salino. La verdad conocida permite medir el error.",
            ),
          ],
          [
            t("02 / PHYSICS", "02 / FÍSICA"),
            t("Predict a response", "Predecir respuesta"),
            t(
              "An integral kernel, complex impedance recursion or finite-difference wave equation maps the earth to a survey.",
              "Un núcleo integral, recursión de impedancia o ecuación de ondas transforma la Tierra en mediciones.",
            ),
          ],
          [
            t("03 / OBSERVATION", "03 / OBSERVACIÓN"),
            t("Limit what is seen", "Limitar lo observado"),
            t(
              "Finite coverage, bandwidth and seeded noise remove information before inversion begins.",
              "Cobertura finita, banda y ruido sembrado eliminan información antes de invertir.",
            ),
          ],
          [
            t("04 / INFERENCE", "04 / INFERENCIA"),
            t("Compare hypotheses", "Comparar hipótesis"),
            t(
              "Data fit, model error and prior assumptions must be inspected together.",
              "Ajuste de datos, error de modelo e hipótesis previas deben inspeccionarse juntos.",
            ),
          ],
        ].map(([n, title, body]) => (
          <div key={n}>
            <b>{n}</b>
            <strong>{title}</strong>
            <p>{body}</p>
          </div>
        ))}
      </div>
      <Equation
        tex={String.raw`d_{obs}=F(m_{true})+\epsilon,\qquad \hat m=\arg\min_m\{\|W_d(F(m)-d_{obs})\|_2^2+\beta R(m)\}`}
        caption={t(
          "The forward model predicts observations. The inverse objective balances agreement with observations against a declared prior.",
          "El modelo directo predice observaciones. El objetivo inverso equilibra acuerdo con datos y un prior declarado.",
        )}
      />
      <div className="doc-grid">
        <section>
          <h2>
            {t(
              "A small residual can hide a wrong earth",
              "Un residuo pequeño puede ocultar una Tierra incorrecta",
            )}
          </h2>
          <p>
            {t(
              "Potential fields are non-unique: many distributions of density or magnetization can generate similar surface observations. Sensitivity weighting and sparse penalties select a solution; they do not create information that was never measured. In the opposing-density case, cancellation can produce a weak field over substantial geological structure.",
              "Los campos potenciales no son únicos: muchas distribuciones de densidad o magnetización generan observaciones superficiales similares. Ponderaciones y penalizaciones seleccionan una solución; no crean información nunca medida. En el caso de densidades opuestas, la cancelación genera un campo débil sobre estructura importante.",
            )}
          </p>
          <Refs ids={["cockett2015", "choclo"]} />
        </section>
        <section>
          <h2>
            {t(
              "Frequency is a depth filter, not a ruler",
              "La frecuencia filtra profundidad, no la mide directamente",
            )}
          </h2>
          <p>
            {t(
              "In a uniform conductor, electromagnetic skin depth scales approximately with the square root of resistivity divided by frequency. Layered responses mix a range of depths. The MT cases show why apparent resistivity is not a direct depth section. The layer thicknesses are held known here so the resistivity inverse problem can be isolated.",
              "En un conductor uniforme, la profundidad de penetración escala aproximadamente con la raíz de resistividad sobre frecuencia. Las respuestas estratificadas mezclan profundidades. MT muestra por qué resistividad aparente no es una sección directa. Aquí los espesores son conocidos para aislar la inversión de resistividad.",
            )}
          </p>
          <Refs ids={["heagy2017", "mtpy"]} />
        </section>
        <section>
          <h2>
            {t(
              "Waveforms carry timing and amplitude",
              "Las ondas transportan tiempo y amplitud",
            )}
          </h2>
          <p>
            {t(
              "A shot gather places receiver position horizontally and time vertically. Reflections, refractions and diffractions create different moveout patterns. The animation is a saved acoustic pressure field from the same finite-difference simulation that produces the gathers. It is not a drawn expanding circle. Inversion uses the waveform gradient through Deepwave automatic differentiation.",
              "Un registro coloca receptores horizontalmente y tiempo verticalmente. Reflexiones, refracciones y difracciones generan patrones distintos. La animación es presión acústica guardada de la misma simulación que produce registros, no un círculo dibujado. La inversión usa el gradiente de onda por diferenciación automática de Deepwave.",
            )}
          </p>
          <Refs ids={["virieux2009", "deepwave"]} />
        </section>
        <section>
          <h2>
            {t(
              "A learned prior has a domain",
              "Un prior aprendido tiene un dominio",
            )}
          </h2>
          <p>
            {t(
              "The CNN learns column density, a depth-integrated property, from gravity observations. The autoencoder learns a compressed representation of observations. Neither is a universal geological interpreter. Realization-disjoint training, validation and test sets separate fitting from evaluation; two withheld geometries deliberately stress transfer.",
              "La CNN aprende densidad integrada en profundidad desde gravedad. El autoencoder aprende una representación comprimida de observaciones. Ninguno interpreta geología universalmente. Particiones por realizaciones separan ajuste y evaluación; dos geometrías excluidas ponen a prueba la transferencia.",
            )}
          </p>
          <Refs ids={["inversionnet", "openfwi"]} />
        </section>
      </div>
      <section className="method-article">
        <h2>
          {t(
            "Start with a falsifiable question",
            "Comience con una pregunta contrastable",
          )}
        </h2>
        <p>
          {t(
            "Open the normal-fault seismic case, play the central shot and pause at an interface. Then inspect a different receiver gather and compare direct with multiscale inversion. For a contrasting failure, use decoupled joint structures and increase regularization: a visually cleaner model may be scientifically worse. Every case includes a guided comparison and an explicit limitation.",
            "Abra la falla normal sísmica, reproduzca el disparo central y pause en una interfaz. Inspeccione otro registro y compare inversión directa y multiescala. Para un fallo distinto, use estructuras conjuntas desacopladas y aumente regularización: un modelo visualmente limpio puede ser peor científicamente. Cada caso incluye una comparación guiada y una limitación.",
          )}
        </p>
        <a href={appBase}>
          {t("Open the observatory →", "Abrir el observatorio →")}
        </a>
      </section>
    </div>
  );
}

const theory: Record<
  Family,
  {
    equation: string;
    refs: string[];
    algorithm: [string, string];
    assumptions: [string, string];
    validation: [string, string];
  }
> = {
  gravity: {
    equation: String.raw`d=G_\rho m,\quad \min_q\|Aq-b\|_2^2+\beta\sum_i w_iq_i^2,\quad m=Wq`,
    refs: ["cockett2015", "choclo"],
    algorithm: [
      "SimPEG computes exact rectangular-prism gz sensitivities for a 14 × 12 × 8 mesh and 256 stations. Columns are scaled by sensitivity with a 6% floor. L2 solves a data-space positive-definite linear system. IRLS repeats eight solves with weights proportional to (q² + ε²)^−1/2; ε is 12% of the current maximum |q|. This is sparse model-norm regularization, not a smoothness penalty.",
      "SimPEG calcula sensibilidades gz de prismas en malla 14 × 12 × 8 y 256 estaciones. Se escalan columnas por sensibilidad con piso 6%. L2 resuelve un sistema definido positivo en espacio de datos. IRLS repite ocho soluciones con pesos proporcionales a (q² + ε²)^−1/2; ε es 12% del máximo |q|. Es norma dispersa de modelo, no suavizado.",
    ],
    assumptions: [
      "Cartesian ENU coordinates; density contrast in g/cm³ and gz in mGal. Upward z gives negative gz over a positive mass. Finite mesh, independent Gaussian noise, uniform station uncertainty; no regional trend or terrain outside the mesh.",
      "Coordenadas ENU; contraste en g/cm³ y gz en mGal. z positivo arriba produce gz negativo sobre masa positiva. Malla finita, ruido gaussiano independiente e incertidumbre uniforme; sin tendencia regional ni terreno exterior.",
    ],
    validation: [
      "Independent prism comparison, linearity and sign checks; artifact residual closure; model error against known truth. Small residuals do not certify depth resolution.",
      "Comparación independiente de prismas, linealidad y signo; cierre de residuos; error de modelo contra verdad conocida. Residuos pequeños no certifican resolución en profundidad.",
    ],
  },
  magnetics: {
    equation: String.raw`d_{TMI}\simeq\hat b_0^T B_a,\qquad d=G_xm_x+G_ym_y+G_zm_z`,
    refs: ["cockett2015", "choclo"],
    algorithm: [
      "The inducing field is 50,000 nT at inclination 60° and declination 12°. Scalar inversion assumes induced magnetization. Vector inversion solves three susceptibility-equivalent components per cell and displays their norm. In the remanent case, the true direction is normalized (0.80, −0.55, 0.23), intentionally inconsistent with the scalar assumption.",
      "Campo inductor de 50.000 nT, inclinación 60° y declinación 12°. Inversión escalar supone magnetización inducida. La vectorial resuelve tres componentes equivalentes de susceptibilidad por celda y muestra su norma. En remanencia, la dirección real es (0,80; −0,55; 0,23) normalizada, incompatible con la hipótesis escalar.",
    ],
    assumptions: [
      "Weak-anomaly linearized total-field response; no self-demagnetization or nonlinear susceptibility. Vector amplitude is not directly interchangeable with a signed scalar susceptibility estimate.",
      "Respuesta total linealizada de anomalía débil; sin autodesmagnetización ni susceptibilidad no lineal. La amplitud vectorial no equivale directamente a susceptibilidad escalar con signo.",
    ],
    validation: [
      "Check vector/scalar forward consistency for induced direction, physical nT scale, and remanent residuals. Additional vector freedom can overfit.",
      "Verifique consistencia vectorial/escalar en dirección inducida, escala nT y residuos remanentes. Mayor libertad vectorial puede sobreajustar.",
    ],
  },
  mt: {
    equation: String.raw`Z_j=w_j\frac{Z_{j+1}+w_j\tanh(k_jh_j)}{w_j+Z_{j+1}\tanh(k_jh_j)},\quad k_j=\sqrt{i\omega\mu/\rho_j},\quad w_j=\sqrt{i\omega\mu\rho_j}`,
    refs: ["heagy2017", "goyes2024", "mtpy"],
    algorithm: [
      "Complex impedance recurses upward from a homogeneous half-space. Bounded SciPy least squares estimates log resistivity between 1 and 6,000 Ω m. A second solver optimizes log resistivity with Adam. A third uses a 1–24–24–1 tanh network as a per-sounding parameterization, differentiating through the same physical recursion. Neural bounds are exp(1) to exp(8) Ω m.",
      "La impedancia compleja recurre hacia arriba desde un semiespacio. SciPy estima log resistividad entre 1 y 6.000 Ω m. Un segundo solver optimiza con Adam. Un tercero usa red tanh 1–24–24–1 por sondeo, diferenciando la misma recursión física. Límites neuronales exp(1) a exp(8) Ω m.",
    ],
    assumptions: [
      "Known layer thicknesses; isotropic 1D earth; 36 frequencies. Loss fits real and imaginary impedance with known noise standard deviation, plus differences of log resistivity. Apparent resistivity and phase are response diagnostics.",
      "Espesores conocidos, Tierra 1D isotrópica y 36 frecuencias. La pérdida ajusta impedancia real e imaginaria con desviación conocida y diferencias de log resistividad. Resistividad aparente y fase son diagnósticos de respuesta.",
    ],
    validation: [
      "Homogeneous half-space: apparent resistivity equals true resistivity and phase is 45°. NumPy/PyTorch parity and directional derivative tests check implementation. Saved least-squares states are objective evaluations, not accepted iterations.",
      "Semiespacio homogéneo: resistividad aparente igual a real y fase 45°. Paridad NumPy/PyTorch y derivadas direccionales verifican implementación. Estados de mínimos cuadrados son evaluaciones, no iteraciones aceptadas.",
    ],
  },
  seismic: {
    equation: String.raw`\partial_{tt}u-v^2\nabla^2u=s,\qquad \Phi(v)=\|P u(v)-d\|_2^2/\|d\|_2^2+\beta R(v)`,
    refs: ["deepwave", "virieux2009", "devito"],
    algorithm: [
      "Deepwave propagates three Ricker shots on a 64 × 48 grid, 25 m spacing, 1 ms time step and 1.1 s duration. Fourth-order spatial differences and 12-cell absorbing boundaries are used. Automatic differentiation computes gradients. Adam performs 28 updates inside velocity bounds 1,400–4,400 m/s. Multiscale optimization uses moving-average windows 21, 9 and 1 samples; the retained solution minimizes full-band data loss among evaluated states.",
      "Deepwave propaga tres disparos Ricker en malla 64 × 48, paso 25 m, tiempo 1 ms y duración 1,1 s. Diferencias espaciales de orden cuatro y bordes absorbentes de 12 celdas. Diferenciación automática calcula gradientes. Adam realiza 28 actualizaciones entre 1.400–4.400 m/s. Multiescala usa ventanas de 21, 9 y 1 muestras; se retiene el menor error de datos de banda completa.",
    ],
    assumptions: [
      "Constant-density acoustic 2D medium, known source, 40 or 20 receivers. Starting velocity is an a priori depth trend (1,800 + 22 × depth-index), not a smoothed copy of truth. Displayed wavefields are central-shot snapshots every 24 ms; gathers are sampled every 4 ms.",
      "Medio acústico 2D de densidad constante, fuente conocida y 40 o 20 receptores. Velocidad inicial es tendencia previa (1.800 + 22 × índice de profundidad), no verdad suavizada. Campos del disparo central cada 24 ms; registros cada 4 ms.",
    ],
    validation: [
      "Adjoint directional derivative, finite nonzero propagated energy, residual closure, and final-versus-initial loss across all cases. Data improvement is not a claim that 28 updates fully recover the earth.",
      "Derivada direccional adjunta, energía finita no nula, cierre de residuos y comparación de pérdida final/inicial en todos los casos. Mejorar datos no implica que 28 actualizaciones recuperen toda la Tierra.",
    ],
  },
  joint: {
    equation: String.raw`\Phi=\Phi_g(\rho)+\Phi_m(\chi)+\lambda\|\nabla\tilde\rho\times\nabla\tilde\chi\|_2^2+\alpha(\|\tilde\rho\|_2^2+\|\tilde\chi\|_2^2)`,
    refs: ["cockett2015"],
    algorithm: [
      "The gravity and magnetic operators share a mesh. Dimensionless density and susceptibility are optimized together for 180 Adam steps from independent L2 solutions. Cross-gradients use cell-index derivatives on normalized properties; their magnitude is dimensionless. Coupling increases from 4 to 25 in the regularization experiment.",
      "Los operadores gravimétrico y magnético comparten malla. Propiedades adimensionales se optimizan 180 pasos Adam desde soluciones L2 independientes. Gradientes cruzados usan derivadas por índice de celda en propiedades normalizadas; magnitud adimensional. Acoplamiento aumenta de 4 a 25.",
    ],
    assumptions: [
      "Structural compatibility is a prior, not an observed fact. One case shares boundaries; the other deliberately violates that prior. Zero gradients also make a cross-product small.",
      "Compatibilidad estructural es un prior, no un hecho observado. Un caso comparte límites; otro lo viola deliberadamente. Gradientes nulos también reducen el producto cruzado.",
    ],
    validation: [
      "Compare both data fits, property errors and structural penalty; test zero/parallel/orthogonal gradients. Coverage masks must apply to both objectives.",
      "Compare ambos ajustes, errores de propiedades y penalización estructural; pruebe gradientes nulos, paralelos y ortogonales. Máscaras de cobertura aplican a ambos objetivos.",
    ],
  },
  learned: {
    equation: String.raw`\hat c=f_\theta(d/s_d)\,s_c,\quad c(x,y)=\sum_z\rho(x,y,z)\Delta z;\qquad a(d)=\|g_\theta(d/s_d)-d/s_d\|_2^2/N`,
    refs: ["inversionnet", "openfwi"],
    algorithm: [
      "The CNN uses two 3 × 3 convolutions (16 and 24 channels), GELU, adaptive 4 × 4 pooling, and 384–96–168 dense layers. It predicts 12 × 14 column density. The autoencoder uses 256–64–12–64–256 dense layers. Both train for 180 epochs on 800 realizations; best validation weights on 160 realizations are frozen before evaluating another 160.",
      "La CNN usa convoluciones 3 × 3 (16 y 24 canales), GELU, pooling 4 × 4 y capas 384–96–168. Predice densidad integrada 12 × 14. Autoencoder 256–64–12–64–256. Ambos entrenan 180 épocas con 800 realizaciones; mejores pesos en 160 de validación se congelan antes de evaluar otras 160.",
    ],
    assumptions: [
      "Four procedural geometry families, fixed reference survey, training-only normalization. Oblique and ring geometries are withheld. Missing stations are linearly interpolated with nearest edge fill. Changing survey height deliberately tests acquisition shift, not recalibration.",
      "Cuatro familias procedurales, geometría de referencia fija y normalización sólo de entrenamiento. Geometrías oblicua y anular excluidas. Estaciones faltantes se interpolan linealmente con borde cercano. Cambiar altura prueba cambio de adquisición, no recalibración.",
    ],
    validation: [
      "Serialized weight round-trip, disjoint seeds, held-out per-realization errors, and classical column-density baseline. The 99th-percentile validation autoencoder threshold is an empirical novelty flag, not uncertainty or probability.",
      "Recarga de pesos, semillas disjuntas, errores por realización independiente y referencia clásica de densidad integrada. Umbral percentil 99 de validación es alerta empírica, no incertidumbre ni probabilidad.",
    ],
  },
};
export function Methodology() {
  const t = useText();
  const es = useShellLang() === "es";
  return (
    <div className="page-body prose">
      <Head
        kicker={t("METHODS / 02", "MÉTODOS / 02")}
        title={t(
          "Follow the physics. Inspect the assumptions.",
          "Siga la física. Inspeccione los supuestos.",
        )}
      >
        {t(
          "Every named method below maps to an executable implementation and a computed artifact. The inverse objective, not the visual style, defines what a result means.",
          "Cada método corresponde a una implementación ejecutable y un artefacto calculado. El objetivo inverso, no el estilo visual, define el significado del resultado.",
        )}
      </Head>
      <Tabs
        ariaLabel={t("Method families", "Familias de métodos")}
        tabs={Object.entries(theory).map(([family, item]) => ({
          id: family,
          label: familyLabels[family as Family][es ? 1 : 0],
          content: (
            <article className="method-article">
              <Equation
                tex={item.equation}
                caption={familyLabels[family as Family][es ? 1 : 0]}
              />
              <div className="doc-grid">
                <section>
                  <h2>
                    {t("Algorithm & parameters", "Algoritmo y parámetros")}
                  </h2>
                  <p>{item.algorithm[es ? 1 : 0]}</p>
                </section>
                <section>
                  <h2>{t("Assumptions & units", "Supuestos y unidades")}</h2>
                  <p>{item.assumptions[es ? 1 : 0]}</p>
                </section>
                <section>
                  <h2>
                    {t(
                      "Validation & interpretation",
                      "Validación e interpretación",
                    )}
                  </h2>
                  <p>{item.validation[es ? 1 : 0]}</p>
                </section>
                <section>
                  <h2>
                    {t(
                      "Inspect the implementation",
                      "Inspeccione la implementación",
                    )}
                  </h2>
                  <p>
                    <a
                      href={`${source}data-pipeline/${{ gravity: "potential", magnetics: "potential", mt: "electromagnetics", seismic: "seismic", joint: "joint", learned: "learning" }[family]}.py`}
                    >
                      {t("Open the numerical source", "Abrir código numérico")}
                    </a>
                  </p>
                  <p>
                    <a href={`${source}tests/test_rebuild.py`}>
                      {t("Numerical tests", "Pruebas numéricas")}
                    </a>
                  </p>
                  <Refs ids={item.refs} />
                </section>
              </div>
            </article>
          ),
        }))}
      />
    </div>
  );
}

export function Implementation() {
  const t = useText();
  return (
    <div className="page-body prose">
      <Head
        kicker={t("ENGINEERING / 03", "INGENIERÍA / 03")}
        title={t(
          "One calculation. Traceable all the way to the screen.",
          "Un cálculo. Trazable hasta la pantalla.",
        )}
      >
        {t(
          "Python computes canonical experiments locally. The browser loads the exact exported arrays, rather than drawing a second approximate simulation. The VPS and GitHub Pages serve the same static release; neither is advertised as a GPU server.",
          "Python calcula experimentos canónicos localmente. El navegador carga exactamente los arreglos exportados, no una segunda simulación aproximada. VPS y GitHub Pages sirven el mismo release estático; ninguno se anuncia como servidor GPU.",
        )}
      </Head>
      <div className="process-diagram">
        {[
          [
            "01",
            "geology.py",
            t(
              "Explicit 3D geometry and layered/section constructors; units and seeded cases.",
              "Geometría 3D explícita y constructores estratificados; unidades y casos sembrados.",
            ),
          ],
          [
            "02",
            "rebuild.py",
            t(
              "Forward model, noise, coverage mask, inverse solve, evaluation. GPU where supported.",
              "Modelo directo, ruido, máscara, inversión y evaluación. GPU cuando corresponde.",
            ),
          ],
          [
            "03",
            "catalog.json",
            t(
              "120 artifacts, method summaries, SHA-256 and byte sizes; trained checkpoints.",
              "120 artefactos, métodos, SHA-256 y tamaños; checkpoints entrenados.",
            ),
          ],
          [
            "04",
            "React / Three.js",
            t(
              "Case-specific rendering, orbit, cuts, frame replay, units, export and comparison.",
              "Vistas por caso, órbita, cortes, reproducción, unidades, exportación y comparación.",
            ),
          ],
        ].map(([n, title, body]) => (
          <div key={n}>
            <b>{n}</b>
            <strong>{title}</strong>
            <p>{body}</p>
          </div>
        ))}
      </div>
      <div className="doc-grid">
        <section>
          <h2>{t("Reproduce locally", "Reproducir localmente")}</h2>
          <pre>
            <code>
              {
                "./scripts/setup.ps1 -Gpu\n./scripts/precompute.ps1\n.venv-pipeline/Scripts/python tests/run_validation.py\ncd frontend\nnpm ci\nnpm test\nnpm run build"
              }
            </code>
          </pre>
          <p>
            {t(
              "Virtual environments stay inside the repository and are ignored by Git. No internal Python package or editable install is needed. The build copies committed artifacts; CI never trains or regenerates them.",
              "Los entornos virtuales permanecen en el repositorio y fuera de Git. No requiere paquete Python interno ni instalación editable. El build copia artefactos; CI nunca entrena ni los regenera.",
            )}
          </p>
        </section>
        <section>
          <h2>
            {t(
              "Array orientation is part of the contract",
              "La orientación es parte del contrato",
            )}
          </h2>
          <p>
            {t(
              "Potential-field vectors use x-fast mesh order: [z, northing, easting]. Surface maps are [northing, easting]. Seismic images are [depth, distance], while shot data are [shot, receiver, time]. The renderer transposes shot gathers, not velocity grids. All axes carry physical units.",
              "Los vectores potenciales usan x rápido: [z, norte, este]. Mapas [norte, este]. Imágenes sísmicas [profundidad, distancia], registros [disparo, receptor, tiempo]. El render transpone registros, no velocidades. Los ejes indican unidades físicas.",
            )}
          </p>
        </section>
        <section>
          <h2>{t("Evidence and checkpoints", "Evidencia y checkpoints")}</h2>
          <p>
            {t(
              "Each artifact includes truth, observations, predictions, residuals, inverse model, recorded states, parameters, seed and engine. CNN/autoencoder weights are small JSON arrays with shape metadata and SHA-256. The training ledger records split counts, normalization, per-test errors and the selected validation loss.",
              "Cada artefacto incluye verdad, observaciones, predicciones, residuos, modelo, estados, parámetros, semilla y motor. Pesos CNN/autoencoder son arreglos JSON con formas y SHA-256. El registro documenta particiones, normalización, errores y pérdida de validación.",
            )}
          </p>
          <a href={`${appBase}data/v2/models/training.json`}>
            {t(
              "Download the training ledger",
              "Descargar registro de entrenamiento",
            )}
          </a>
        </section>
        <section>
          <h2>{t("What runs online", "Qué se ejecuta online")}</h2>
          <p>
            {t(
              "3D rendering, slicing, orbit, time/iteration scrubbing, method and experiment comparisons, and run export execute in the browser. The live layered-earth calculator on Experiments recomputes complex impedance for your chosen resistivity and thickness values. FWI and neural training are deliberately offline.",
              "Render 3D, cortes, órbita, reproducción, comparación y exportación se ejecutan en navegador. La calculadora estratificada en Experimentos recalcula impedancia para resistividades y espesores elegidos. FWI y entrenamiento neuronal son offline deliberadamente.",
            )}
          </p>
        </section>
      </div>
      <Refs ids={["cockett2015", "deepwave", "choclo"]} />
    </div>
  );
}

export function Experiments() {
  const t = useText();
  const es = useShellLang() === "es";
  const { catalog, error } = useCatalog();
  const [selected, setSelected] = useState("GRAVITY_INTRUSION");
  const lesson = lessons[selected];
  return (
    <div className="page-body prose">
      <Head
        kicker={t("EXPERIMENTS / 04", "EXPERIMENTOS / 04")}
        title={t(
          "Change one cause. Examine the consequence.",
          "Cambie una causa. Examine la consecuencia.",
        )}
      >
        {t(
          "Six controlled conditions separate property contrast, observation noise, acquisition, missing coverage and regularization. They are individual forward/inverse computations, not colour variants.",
          "Seis condiciones controladas separan contraste, ruido, adquisición, cobertura faltante y regularización. Son cálculos directos/inversos individuales, no variantes de color.",
        )}
      </Head>
      {error && <p role="alert">{error}</p>}
      <div className="case-guide">
        <label className="inline-control">
          {t("Choose an investigation", "Elija una investigación")}
          <select
            value={selected}
            onChange={(e) => setSelected(e.target.value)}
          >
            {catalog?.cases.map((c) => (
              <option key={c.id} value={c.id}>
                {es ? c.name_es : c.name}
              </option>
            ))}
          </select>
        </label>
        <h2>{lesson.question[es ? 1 : 0]}</h2>
        <p>{lesson.read[es ? 1 : 0]}</p>
        <p>{lesson.try[es ? 1 : 0]}</p>
        <p className="plot-note">{lesson.limit[es ? 1 : 0]}</p>
      </div>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              <th>{t("Condition", "Condición")}</th>
              <th>{t("Potential fields", "Campos potenciales")}</th>
              <th>MT</th>
              <th>{t("Seismic", "Sísmica")}</th>
            </tr>
          </thead>
          <tbody>
            {[
              [
                "Reference / referencia",
                "256 stations · 60 m",
                "36 frequencies · 0.01–100 Hz",
                "3 shots · 40 receivers · 8 or 9 Hz",
              ],
              [
                "Contrast / contraste",
                "×1.5 property",
                "×1.5 resistivity",
                "×1.15 velocity contrast",
              ],
              [
                "Noise / ruido",
                "14% field SD",
                "10% |Z| per component",
                "8% amplitude SD",
              ],
              [
                "Acquisition / adquisición",
                "180 m survey height",
                "0.001–100 Hz",
                "5 Hz source",
              ],
              [
                "Coverage / cobertura",
                "128 active stations",
                "18 active frequencies",
                "20 receivers",
              ],
              [
                "Regularization / regularización",
                "β .018 → .25; joint λ 4 → 25",
                "β .001 → .3",
                "β .002 → .06",
              ],
            ].map((row) => (
              <tr key={row[0]}>
                {row.map((cell, i) => (
                  <td key={i}>{cell}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <LiveMT />
    </div>
  );
}

import { LiveMT } from "../components/LiveMT";
export function Benchmark() {
  const t = useText();
  const es = useShellLang() === "es";
  const { catalog, error } = useCatalog();
  const [family, setFamily] = useState<Family>("gravity");
  const [method, setMethod] = useState("l2");
  const [metric, setMetric] = useState("model_rmse");
  const cases = catalog?.cases.filter((c) => c.family === family) ?? [];
  const methods = cases[0]?.variants[0]?.methods ?? {};
  const selectedMethod = methods[method] ? method : Object.keys(methods)[0];
  const metrics = Object.keys(methods[selectedMethod]?.metrics ?? {}).filter(
    (k) => typeof methods[selectedMethod]?.metrics[k] === "number",
  );
  const selectedMetric = metrics.includes(metric) ? metric : metrics[0];
  return (
    <div className="page-body prose">
      <Head
        kicker={t("EVIDENCE / 05", "EVIDENCIA / 05")}
        title={t(
          "Compare errors, not appearances.",
          "Compare errores, no apariencias.",
        )}
      >
        {t(
          "Results below are read directly from the committed artifact catalogue. Compare like units within a method. There is no combined score that mixes gravity, resistivity and velocity.",
          "Resultados leídos directamente del catálogo de artefactos. Compare unidades iguales dentro de un método. No existe un puntaje combinado de gravedad, resistividad y velocidad.",
        )}
      </Head>
      {error && <p role="alert">{error}</p>}
      <div className="benchmark-summary">
        {[
          [
            catalog?.cases.length ?? 0,
            t("geological cases", "casos geológicos"),
          ],
          [
            catalog?.cases.reduce((n, c) => n + c.variants.length, 0) ?? 0,
            t("computed experiments", "experimentos calculados"),
          ],
          [
            catalog?.cases.reduce(
              (n, c) =>
                n +
                c.variants.reduce(
                  (m, v) => m + Object.keys(v.methods).length,
                  0,
                ),
              0,
            ) ?? 0,
            t("method results", "resultados de métodos"),
          ],
          [1120, t("learning realizations", "realizaciones de aprendizaje")],
        ].map(([v, l]) => (
          <div key={l}>
            <strong>{v}</strong>
            <span>{l}</span>
          </div>
        ))}
      </div>
      <div className="benchmark-controls">
        <select
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
        <select
          aria-label={t("Method", "Método")}
          value={selectedMethod ?? ""}
          onChange={(e) => setMethod(e.target.value)}
        >
          {Object.entries(methods).map(([k, v]) => (
            <option key={k} value={k}>
              {es ? v.name_es : v.name}
            </option>
          ))}
        </select>
        <select
          aria-label={t("Metric", "Métrica")}
          value={selectedMetric ?? ""}
          onChange={(e) => setMetric(e.target.value)}
        >
          {metrics.map((k) => (
            <option key={k} value={k}>
              {k.replaceAll("_", " ")}
            </option>
          ))}
        </select>
      </div>
      {cases.length > 0 && selectedMetric && (
        <>
          <Plot
            title={t(
              "Effect of controlled conditions",
              "Efecto de condiciones controladas",
            )}
            x={[1, 2, 3, 4, 5, 6]}
            series={cases.map((c, i) => ({
              name: es ? c.name_es : c.name,
              values: c.variants.map((v) =>
                Number(v.methods[selectedMethod]?.metrics[selectedMetric]),
              ),
              color: [
                "var(--plot-observed)",
                "var(--plot-predicted)",
                "var(--plot-third)",
                "#779487",
              ][i % 4],
            }))}
            xLabel={t(
              "1 Reference · 2 Contrast · 3 Noise · 4 Acquisition · 5 Coverage · 6 Regularization",
              "1 Referencia · 2 Contraste · 3 Ruido · 4 Adquisición · 5 Cobertura · 6 Regularización",
            )}
            yLabel={selectedMetric.replaceAll("_", " ")}
          />
          <div className="table-scroll">
            <table>
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
                          title={`SHA-256 ${v.sha256}`}
                          href={`${appBase}data/v2/${v.path}`}
                        >
                          {format(
                            Number(
                              v.methods[selectedMethod]?.metrics[
                                selectedMetric
                              ],
                            ),
                          )}
                        </a>
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
      <p className="plot-note">
        {t(
          "WRMS is dimensionless data residual normalized by the specified noise. Model RMSE uses the property units of the selected family; MT log-model RMSE is dimensionless; velocity RMSE is m/s; column RMSE is g/cm³ m. Cross-gradient values use normalized cell-index derivatives. Click a result to inspect its complete artifact.",
          "WRMS es residuo adimensional normalizado por ruido. RMSE usa unidades de la propiedad; log-RMSE MT es adimensional; RMSE de velocidad m/s; RMSE de columna g/cm³ m. Gradiente cruzado usa derivadas por celda normalizadas. Pulse un resultado para inspeccionar su artefacto.",
        )}
      </p>
      <p>
        <a href={`${appBase}data/v2/models/training.json`}>
          {t(
            "Training / validation / held-out test evidence",
            "Evidencia de entrenamiento / validación / prueba independiente",
          )}
        </a>{" "}
        ·{" "}
        <a href={`${source}docs/validation/rebuild.md`}>
          {t(
            "Validation report and limitations",
            "Informe de validación y limitaciones",
          )}
        </a>
      </p>
    </div>
  );
}
