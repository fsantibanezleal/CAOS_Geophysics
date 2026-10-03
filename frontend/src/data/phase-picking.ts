/** Source-backed explanatory content only. These are not executable method records. */
export type Pair = readonly [en: string, es: string];
export type PickerId = "m08" | "m13";
export interface CitedText { text: Pair; cite: string }
export interface PickerEquation { tex: string; caption: Pair }
export interface PickerSection {
  title: Pair;
  paragraphs: CitedText[];
  equations: PickerEquation[];
  symbols: Pair[];
  steps?: Pair[];
  calloutTitle: Pair;
  callout: Pair;
  refs: string[];
}
export interface PickerContent {
  id: PickerId;
  title: Pair;
  theory: PickerSection;
  implementation: PickerSection;
}
const T = (en: string, es: string): Pair => [en, es];
const P = (en: string, es: string, cite: string): CitedText => ({ text: T(en, es), cite });
const E = (tex: string, en: string, es: string): PickerEquation => ({ tex, caption: T(en, es) });

export const phasePickers: readonly PickerContent[] = [
  {
    id: "m08",
    title: T("M08 · Classical P/S arrivals", "M08 · Llegadas P/S clásicas"),
    theory: {
      title: T("Classical waveform arrival picking", "Detección clásica de llegadas sísmicas"),
      paragraphs: [
        P(
          "An earthquake station records three channel histories, not a controlled acoustic FWI shot. MiniSEED samples begin as digital counts with a UTC start time and sampling frequency in Hz. Their channel orientation, sensor response and validity epoch live in StationXML. Response removal can produce ground velocity in m/s only when that response matches the channel and recording time; a trace left in counts must retain its counts label. Neither a converted amplitude nor a phase arrival is a subsurface velocity image.",
          "Una estación sísmica registra tres canales, no un disparo controlado de FWI acústica. MiniSEED comienza como conteos digitales con inicio UTC y frecuencia de muestreo en Hz. La orientación, respuesta del instrumento y época válida están en StationXML. La deconvolución produce velocidad del suelo en m/s sólo si la respuesta corresponde al canal y tiempo; una traza sin corrección conserva la unidad de conteos. Ni amplitud convertida ni llegada de fase son una imagen de velocidad del subsuelo.",
          "obspyresponse",
        ),
        P(
          "A classical short-term/long-term average compares energy in a short recent window with a longer background window. If both windows use the same homogeneous quantity, counts squared or (m/s) squared cancel and the ratio is dimensionless. Window durations in seconds become integer sample lengths through the measured sampling rate. A high ratio is evidence of a change in signal energy, not evidence that a particular wave type has arrived. Filter corners, taper, gap masks and triggering thresholds must be recorded because they can move or create apparent onsets.",
          "El promedio de corto plazo frente al de largo plazo compara energía reciente con un fondo más largo. Si ambas ventanas usan la misma magnitud, los conteos al cuadrado o (m/s) al cuadrado se cancelan y la razón no tiene dimensión. Las duraciones en segundos se convierten a muestras enteras usando la frecuencia medida. Una razón alta indica cambio de energía, no identifica por sí sola el tipo de onda. Cortes de filtro, taper, máscaras de huecos y umbrales se registran porque pueden desplazar o crear aparentes inicios.",
          "obspytrigger",
        ),
        P(
          "P and S are phase hypotheses attached to an onset after a separate association step. P is often the first clear compressional arrival, whereas S can be later and mixed with P coda. A published S-wave workflow combines horizontal-component STA/LTA, polarization evidence, AR-AIC refinement and quality assessment. These are literature components, not selected M08 settings; no fixed STA/LTA threshold automatically labels an onset S. The window source, channel evidence and any analyst review must accompany the pick. Ambiguous coda, noise or converted phases remain unresolved rather than forced into P/S.",
          "P y S son hipótesis de fase asignadas a un inicio tras una etapa de asociación separada. P suele ser la primera llegada compresional clara; S puede ser posterior y mezclarse con la coda de P. Un flujo publicado para S combina STA/LTA horizontal, polarización, refinamiento AR-AIC y control de calidad. Son componentes de literatura, no parámetros M08 elegidos; ningún umbral STA/LTA fijo identifica automáticamente S. Se conserva origen de ventana, evidencia por canal y revisión humana. Coda, ruido o conversión ambiguos quedan no resueltos, sin forzar P/S.",
          "diehl2009",
        ),
        P(
          "A catalogue pick is an analyst timing reference with finite reading uncertainty, not the true wavefield. Evaluation matches a candidate and an analyst P or S one-to-one within a predeclared phase-specific tolerance, then reports signed time residual in seconds, misses, false triggers and P/S confusions separately. Low signal-to-noise ratio, clipping, gaps, wrong response epoch, overlapping events and a late S buried in P coda are necessary failure strata. Only real held-out event and station groups can support a claim about field picking; no such result is reported by this content page.",
          "Una marca de catálogo es referencia temporal de un analista con incertidumbre de lectura, no el campo de ondas verdadero. La evaluación empareja candidata y referencia P o S uno a uno dentro de tolerancia declarada por fase; informa residuo temporal con signo en segundos, omisiones, falsas activaciones y confusión P/S por separado. Baja señal/ruido, saturación, huecos, época de respuesta errónea, eventos superpuestos y S oculta en coda P son estratos de falla necesarios. Sólo grupos reales de eventos y estaciones reservados permiten afirmar desempeño de campo; esta página no presenta tal resultado.",
          "allen1978",
        ),
      ],
      equations: [
        E(String.raw`t_n=t_0+\frac{n}{f_s},\qquad N_S=\operatorname{round}(f_sT_S),\quad N_L=\operatorname{round}(f_sT_L)`,
          "t₀ is UTC trace start; n is sample index; fₛ is samples/s (Hz); Tₛ and Tₗ are short and long durations in s; Nₛ and Nₗ are their sample counts.",
          "t₀ es inicio UTC; n es índice; fₛ son muestras/s (Hz); Tₛ y Tₗ duran segundos; Nₛ y Nₗ son sus cantidades de muestras."),
        E(String.raw`C_c[n]=\frac{N_S^{-1}\sum_{j=n-N_S+1}^{n}x_c[j]^2}{N_L^{-1}\sum_{j=n-N_L+1}^{n}x_c[j]^2},\qquad N_L>N_S`,
          "C is the dimensionless STA/LTA characteristic on channel c; x is a single consistently labelled input quantity. A zero/invalid long-window denominator and samples crossing gaps are ineligible, not valid triggers.",
          "C es la característica STA/LTA sin dimensión del canal c; x mantiene una sola unidad. Denominador largo nulo/inválido y muestras sobre huecos son inadmisibles, no activaciones válidas."),
        E(String.raw`\Delta t_{\phi}=\widehat t_{\phi}-t^{\rm analyst}_{\phi},\qquad \phi\in\{P,S\}`,
          "The signed residual Δt is in s; a positive value is a late pick. It is defined only for a one-to-one matched phase and does not turn the analyst time into exact physical truth.",
          "El residuo con signo Δt está en s; positivo significa marca tardía. Sólo se define para fase emparejada uno a uno y no vuelve exacto el tiempo del analista."),
      ],
      symbols: [
        T("x: trace amplitude, digital counts or corrected velocity in m/s, never mixed.", "x: amplitud en conteos digitales o velocidad corregida en m/s, nunca mezcladas."),
        T("fₛ: sample rate in Hz; t₀ and tₙ: UTC times; n: sample index.", "fₛ: frecuencia en Hz; t₀ y tₙ: tiempos UTC; n: índice de muestra."),
        T("Tₛ/Tₗ: short/long windows in s; Nₛ/Nₗ: corresponding counts of samples.", "Tₛ/Tₗ: ventanas en s; Nₛ/Nₗ: cantidades de muestras."),
        T("C: dimensionless energy ratio; Δt: pick minus analyst time in s.", "C: razón energética sin dimensión; Δt: marca menos tiempo del analista en s."),
      ],
      calloutTitle: T("Assumptions and failure boundary", "Supuestos y límite de falla"),
      callout: T(
        "STA/LTA is an onset detector, not a P/S classifier or a measure of calibrated pick uncertainty. Response correction needs a valid epoch and documented stabilization; gaps and clipped channels must not be silently filled. M08 numerical execution and field scores remain unverified here.",
        "STA/LTA detecta inicios; no clasifica P/S ni mide incertidumbre calibrada. Corregir respuesta exige época válida y estabilización documentada; huecos y saturación no se rellenan en silencio. Ejecución M08 y métricas de campo siguen sin verificarse aquí.",
      ),
      refs: ["allen1978", "diehl2009", "obspytrigger", "obspyresponse", "zhu2019"],
    },
    implementation: {
      title: T("M08 processing and classical comparator", "M08: proceso y comparador clásico"),
      paragraphs: [
        P(
          "This is the approved processing specification, not an assertion that M08 has run. An input record needs immutable MiniSEED bytes and hash, event and station/channel identities, UTC interval, sample rate, original counts unit, StationXML hash and response epoch, analyst phase-file identity and rights verdict. Response lookup uses channel plus time, not just station name. A missing or conflicting response prevents a claim of physical velocity, although a consistently counts-labelled trigger analysis may remain inspectable.",
          "Esta es la especificación aprobada, no prueba de ejecución M08. Una entrada requiere bytes MiniSEED inmutables y hash, identidades de evento y estación/canal, intervalo UTC, frecuencia, unidad original de conteos, hash StationXML y época de respuesta, archivo de fases y veredicto de derechos. La respuesta se busca por canal y tiempo, no sólo por nombre de estación. Sin respuesta válida no puede afirmarse velocidad física; un análisis de activación en conteos bien rotulados puede seguir siendo inspeccionable.",
          "obspyresponse",
        ),
        P(
          "The processing receipt must preserve raw traces before detrending, tapering, response correction, band-limiting, anti-aliased resampling or rotation. It records each operation and parameter, output unit, channel order and any gap/clipping mask. Phase windows must be defined without peeking at held-out analyst labels during tuning. The classical characteristic is evaluated only where the full long window is valid; threshold-on and threshold-off semantics and refractory/duplicate handling must be frozen on training/validation groups.",
          "El recibo conserva trazas crudas antes de quitar tendencia, taper, corregir respuesta, filtrar, remuestrear con antialias o rotar. Registra cada operación y parámetro, unidad final, orden de canales y máscara de huecos/saturación. Las ventanas se definen sin mirar etiquetas reservadas al ajustar. La característica clásica se evalúa sólo donde toda ventana larga es válida; umbrales de encendido/apagado y manejo refractario/duplicados se congelan con entrenamiento/validación.",
          "obspytrigger",
        ),
        P(
          "For an eligible window, candidate onset indices are converted to UTC using retained t₀ and fₛ. P/S association needs a separately declared phase window and component evidence, then records phase, time, channel support, ratio/threshold, quality verdict and unresolved reason. If a Diehl-style polarization and AR-AIC S refinement is chosen later, its rotations, search window, model order and quality rule must be frozen before test. S is not the second trigger by default, and catalogue labels must not quietly choose test predictions.",
          "En ventana admisible, índices de inicio se convierten a UTC con t₀ y fₛ conservados. La asociación P/S requiere ventana de fase y evidencia por componentes declaradas aparte; registra fase, tiempo, canales, razón/umbral, calidad y motivo de no resolución. Si más adelante se elige refinamiento S tipo Diehl con polarización y AR-AIC, se fijan rotaciones, ventana, orden de modelo y regla de calidad antes de prueba. S no es la segunda activación por defecto y etiquetas de catálogo no eligen predicciones de prueba.",
          "diehl2009",
        ),
        P(
          "The M08 and M13 comparator receives the same held-out event-station trace IDs, UTC windows, acquisition QC and analyst annotations. Each method may apply its declared transform, but their admissible population and exclusion counts are aligned. One-to-one matching and phase-specific tolerances are frozen before test. Report P/S precision, recall and confusion, signed/absolute residual distributions in s, abstentions and SNR/response/channel-failure strata. A small residual on matched picks alone can conceal many missed phases.",
          "Los comparadores M08 y M13 reciben las mismas trazas evento-estación reservadas, ventanas UTC, QC de adquisición y anotaciones. Cada método aplica su transformación declarada, pero población admisible y exclusiones se alinean. Emparejamiento uno a uno y tolerancias por fase se congelan antes de prueba. Se informan precisión, recall y confusión P/S, residuos con signo y absolutos en s, abstenciones y estratos de señal/ruido, respuesta y canales. Residuo pequeño entre marcas emparejadas puede ocultar muchas fases perdidas.",
          "zhu2019",
        ),
      ],
      equations: [
        E(String.raw`\widehat t_{\phi}=t_0+\frac{n_{\phi}}{f_s},\qquad R_{\phi}=\frac{TP_{\phi}}{TP_{\phi}+FN_{\phi}}`,
          "nφ is a declared phase-associated onset index; Rφ is recall for phase φ on the complete eligible population, including misses FN, not only matched picks TP.",
          "nφ es índice de inicio asociado a fase; Rφ es recall de fase φ en población admisible completa, con omisiones FN, no sólo aciertos TP."),
        E(String.raw`\operatorname{MedAE}_{\phi}=\operatorname{median}_{i\in\mathcal M_{\phi}}|\widehat t_i-t_i^{\rm analyst}|`,
          "Median absolute timing error is in s and is conditional on the matched set Mφ; it must be shown beside recall and unmatched counts.",
          "Error absoluto mediano está en s y condicionado al conjunto emparejado Mφ; se muestra junto a recall y casos sin emparejar."),
      ],
      symbols: [
        T("nφ: selected sample; t₀: UTC start; fₛ: Hz; t̂φ: picked UTC time.", "nφ: muestra elegida; t₀: inicio UTC; fₛ: Hz; t̂φ: tiempo UTC marcado."),
        T("TP/FN: matched true picks and missed analyst phases; Rφ: recall.", "TP/FN: marcas emparejadas y fases omitidas; Rφ: recall."),
        T("Mφ: one-to-one matched set; MedAEφ: conditional median timing error in s.", "Mφ: conjunto emparejado uno a uno; MedAEφ: error temporal mediano condicional en s."),
      ],
      steps: [
        T("Verify source rights, raw hash, event/station IDs, response epoch and analyst-phase provenance.", "Verificar derechos, hash crudo, IDs evento/estación, época de respuesta y origen de fases."),
        T("QC three channels, clocks, orientation, gaps and clipping; preserve counts and any corrected m/s derivative separately.", "Controlar canales, reloj, orientación, huecos y saturación; conservar conteos y derivada corregida en m/s por separado."),
        T("Record detrend/taper/filter/resampling and convert short/long durations from s to samples using the retained fₛ.", "Registrar tendencia, taper, filtro y remuestreo; convertir duraciones de s a muestras con fₛ."),
        T("Freeze STA/LTA windows, thresholds, phase-association rule and abstention on train/validation groups only.", "Congelar ventanas, umbrales, asociación de fase y abstención sólo con entrenamiento/validación."),
        T("Emit onset candidates and eligible P/S picks with UTC time, evidence, reason and processing hash.", "Emitir inicios y marcas P/S admisibles con UTC, evidencia, motivo y hash de proceso."),
        T("Score the same held-out traces and analyst picks used by M13, including unmatched phases and exclusions.", "Evaluar las mismas trazas y marcas reservadas que M13, incluso omisiones y exclusiones."),
      ],
      calloutTitle: T("Not yet an executable result", "Aún no es resultado ejecutable"),
      callout: T(
        "No local M08 short/long window lengths, filter corners, thresholds, field pick table or accuracy are established by this frontend change. They become release settings only after the source/rights and independent numerical gates pass; this page offers no run control.",
        "Este cambio web no fija ventanas M08, cortes de filtro, umbrales, tabla de marcas de campo ni precisión. Sólo serán parámetros de release tras aprobar fuente/derechos y pruebas numéricas independientes; esta página no ofrece control de ejecución.",
      ),
      refs: ["allen1978", "diehl2009", "obspytrigger", "obspyresponse", "zhu2019"],
    },
  },
  {
    id: "m13",
    title: T("M13 · Learned P/S picking", "M13 · Detección P/S aprendida"),
    theory: {
      title: T("PhaseNet-family arrival probabilities", "Probabilidades de llegada tipo PhaseNet"),
      paragraphs: [
        P(
          "The PhaseNet reference problem maps a three-component earthquake record to three sample-wise classes: background, P arrival and S arrival. Its published example uses 3001 samples at 100 Hz, covering 30.0 s between the first and last sample. The input is a recording of an earthquake with analyst arrival annotations, not an acoustic source-receiver shot gather or a direct measurement of subsurface velocity. A network output marks likely arrival time on that window; it cannot by itself locate an event or invert geology.",
          "El problema de referencia PhaseNet transforma tres componentes de un sismo en tres clases por muestra: fondo, llegada P y llegada S. El ejemplo publicado usa 3001 muestras a 100 Hz, con 30,0 s entre primera y última muestra. La entrada es un registro sísmico con marcas de analista, no un conjunto de disparos y receptores ni una medición directa de velocidad del subsuelo. La salida indica tiempos probables de llegada en esa ventana; por sí sola no localiza evento ni invierte geología.",
          "zhu2019",
        ),
        P(
          "The paper subtracts the mean and divides by standard deviation separately for each component. The local M13 contract instead subtracts the float64 trace mean, casts to float32 and divides by each component's peak centred count; the 6000-sample E/N/Z tensor is dimensionless. Raw unrestituted counts and response-corrected velocity in m/s are different data products and cannot be mixed. A zero-variance, absent, clipped or gap-filled channel is a quality failure, not a silently valid three-component example.",
          "El artículo resta la media y divide por desviación estándar en cada componente. El contrato M13 local resta la media float64, convierte a float32 y divide por el máximo absoluto de conteos centrados de cada componente; el tensor E/N/Z de 6000 muestras no tiene dimensión. Conteos sin corregir y velocidad corregida en m/s son productos distintos y no se mezclan. Canal de varianza nula, ausente, saturado o rellenado es una falla de calidad, no un ejemplo triple válido.",
          "zhu2019",
        ),
        P(
          "The reference architecture adapts U-Net to one-dimensional time series. Four downsampling stages build a broader temporal receptive field; four upsampling stages and skip connections recover sample-level timing detail. The published description uses seven-sample convolutions and stride four in the down path. A three-class softmax converts logits to per-sample class scores that sum to one. Those scores are conditional model outputs, not calibrated probabilities of geological truth or a direct confidence interval around a pick.",
          "La arquitectura de referencia adapta U-Net a series temporales unidimensionales. Cuatro etapas descendentes amplían el contexto temporal; cuatro ascendentes y conexiones de salto recuperan detalle por muestra. La descripción publicada usa convoluciones de siete muestras y paso cuatro al reducir. Softmax de tres clases convierte logits en puntajes por muestra que suman uno. Son salidas condicionales del modelo, no probabilidades calibradas de verdad geológica ni un intervalo de confianza directo para una marca.",
          "zhu2019",
        ),
        P(
          "For training, analyst P and S times become narrow Gaussian target curves; the reference paper uses a 0.1 s target standard deviation. Background takes the remaining class mass and categorical cross-entropy compares target and predicted distributions over samples. The Gaussian width represents target-label smoothing, not measured analyst uncertainty. Disagreement between analysts, timing-clock error and waveform ambiguity need separate evidence. A P or S pick is extracted from an accepted score peak under thresholds fixed before test; multiple peaks or low scores may require abstention.",
          "Para entrenar, tiempos P y S de analistas se vuelven curvas objetivo gaussianas; el artículo usa desviación objetivo de 0,1 s. El fondo recibe la masa de clase restante y entropía cruzada compara objetivo y predicción por muestra. El ancho gaussiano suaviza etiquetas, no mide incertidumbre del analista. Desacuerdo humano, error de reloj y ambigüedad de onda requieren evidencia separada. Una marca P o S proviene de un máximo aceptado con umbrales fijados antes de prueba; varios máximos o puntajes bajos pueden exigir abstención.",
          "zhu2019",
        ),
        P(
          "The published PhaseNet split was stratified by station recordings; it does not demonstrate the event-and-station-disjoint generalization required here. The local STEAD selection assigns event IDs and station identities to separate train, development and test sets before fitting. Bridge recordings are withheld rather than copied between sets. The frozen M13 checkpoint and M08 comparator were scored on the same 6,000 selected held-out traces, retaining QC failures and phase misses; the 24 browser-display selections are a separate metadata-selected subset. Their browser parity and calibration cannot be inferred from offline scores.",
          "La división publicada de PhaseNet estratificó registros por estación; no demuestra la generalización con eventos y estaciones disjuntos exigida aquí. La selección STEAD local asigna eventos y estaciones a entrenamiento, desarrollo y prueba antes de ajustar. Los registros puente se excluyen. El checkpoint M13 congelado y M08 se evaluaron en las mismas 6.000 trazas reservadas, con fallas de calidad y omisiones; las 24 de visualización web son una submuestra elegida por metadatos. La paridad web y calibración no se infieren de las cifras offline.",
          "zhu2019",
        ),
      ],
      equations: [
        E(String.raw`\widetilde x_{c,n}=\frac{x_{c,n}-\mu_c}{\sigma_c},\qquad c\in\{Z,N,E\}`,
          "x is a consistently labelled trace quantity (counts or m/s); μ and σ use the same unit, so normalized x̃ is dimensionless. A zero or invalid σ must follow a declared QC policy.",
          "x conserva unidad de traza (conteos o m/s); μ y σ usan esa unidad, de modo que x̃ no tiene dimensión. σ nula o inválida requiere política QC declarada."),
        E(String.raw`q_{k,n}=\frac{\exp z_{k,n}}{\sum_{j\in\{N,P,S\}}\exp z_{j,n}},\qquad k\in\{N,P,S\}`,
          "z is the network logit at sample n; q is the softmax class score for background N, P or S. The three scores sum to one at each sample; calibration is not implied.",
          "z es logit de red en muestra n; q es puntaje softmax de fondo N, P o S. Los tres suman uno por muestra; esto no implica calibración."),
        E(String.raw`p_{\phi,n}\propto\exp\!\left[-\frac{(t_n-t^{\rm analyst}_{\phi})^2}{2\sigma_t^2}\right],\qquad \mathcal L=-\sum_n\sum_{k\in\{N,P,S\}}p_{k,n}\log q_{k,n}`,
          "p is an analyst-centred soft target, σₜ is its chosen smoothing width in s (0.1 s in the reference paper), and L is categorical cross-entropy. Neither is a product uncertainty estimate.",
          "p es objetivo suave centrado en marca humana; σₜ es ancho de suavizado en s (0,1 s en el artículo), y L es entropía cruzada categórica. Ninguno estima incertidumbre del producto."),
      ],
      symbols: [
        T("c: Z/N/E component; n: sample index; x: counts or m/s before normalization.", "c: componente Z/N/E; n: índice; x: conteos o m/s antes de normalizar."),
        T("μc/σc: per-component mean/spread in the input unit; x̃: dimensionless input.", "μc/σc: media/dispersión por componente en unidad de entrada; x̃: entrada sin dimensión."),
        T("k: background N, P or S class; z: logit; q: model class score.", "k: clase fondo N, P o S; z: logit; q: puntaje del modelo."),
        T("p: analyst-centred target distribution; σₜ: smoothing width in s; L: cross-entropy.", "p: distribución objetivo centrada en analista; σₜ: ancho de suavizado en s; L: entropía cruzada."),
      ],
      calloutTitle: T("Reference architecture, not a trained product", "Arquitectura de referencia, no modelo entrenado"),
      callout: T(
        "The 3001-sample input, four-stage U-Net and 0.1 s label width are reference-paper settings, not the selected 6000-sample local model. Softmax height is not calibrated pick uncertainty. The separate browser parity gate must compare the exact frozen ONNX export with real held-out traces before a browser accuracy claim.",
        "La entrada de 3001 muestras, U-Net de cuatro etapas y ancho de etiqueta de 0,1 s son parámetros del artículo, no del modelo local de 6000 muestras. Softmax no es incertidumbre calibrada. La paridad web debe comparar el ONNX congelado con trazas reales reservadas antes de afirmar precisión web.",
      ),
      refs: ["zhu2019", "phasenetofficial", "obspyresponse"],
    },
    implementation: {
      title: T("M13 training, inference and comparison contract", "M13: contrato de entrenamiento, inferencia y comparación"),
      paragraphs: [
        P(
          "A frozen M13 checkpoint and ONNX export are produced by the separate STEAD pipeline; this frontend branch carries no model or field waveform bytes. The browser can execute a supplied ONNX file or a separately reviewed asset manifest. Its trace and model hashes, E/N/Z order, 100 Hz rate, 6000-sample window, unrestituted-count normalization, 0.8 thresholds and 0.4 s P–S separation must agree with the frozen receipt. Loading a model alone does not establish field accuracy or browser parity.",
          "El procesamiento STEAD separado produce checkpoint M13 y ONNX congelados; esta rama web no contiene modelo ni trazas de campo. El navegador puede ejecutar un ONNX aportado o un manifiesto revisado por separado. Hashes, orden E/N/Z, 100 Hz, ventana de 6000 muestras, normalización de conteos sin corregir, umbrales 0,8 y separación P–S de 0,4 s deben coincidir con el registro congelado. Cargar un modelo no demuestra precisión de campo ni paridad web.",
          "phasenetofficial",
        ),
        P(
          "Partition before any fitted normalization, augmentation, threshold search or checkpoint choice. Enforce empty intersections of event IDs and station identities between train, validation and test; discard and count bridge traces. If those constraints leave too few observations, the evaluation remains not-run rather than weakening the split silently. Record the count and scientific distribution of P, S and noise windows per partition. A normalization learned globally on the test set would leak information even when trace IDs are disjoint.",
          "Particionar antes de normalización ajustada, aumentos, búsqueda de umbrales o elección de checkpoint. Exigir intersecciones vacías de IDs de eventos y estaciones entre entrenamiento, validación y prueba; excluir y contar trazas puente. Si quedan muy pocos datos, la evaluación sigue no ejecutada, sin debilitar la partición en silencio. Registrar cantidad y distribución de ventanas P, S y ruido por grupo. Normalizar globalmente con prueba filtra información aunque las trazas no se repitan.",
          "zhu2019",
        ),
        P(
          "The local PhaseNet-family encoder-decoder accepts 100 Hz, 6000-sample E/N/Z unrestituted-count windows. It subtracts each float64 component mean after casting to float32, divides by the float32 peak absolute centred count, rejects flat or exactly duplicated components, and outputs N/P/S softmax scores. This differs from the published 3001-sample reference architecture and standard-deviation normalization. There is no browser resampling or missing-channel fill.",
          "La red local tipo PhaseNet recibe ventanas E/N/Z de 6000 muestras a 100 Hz en conteos sin corregir. Resta la media float64 de cada componente tras convertir a float32, divide por su máximo absoluto float32 de conteos centrados y rechaza componentes planas o duplicadas exactamente. Entrega puntajes softmax N/P/S. Esto difiere del artículo de 3001 muestras y normalización por desviación estándar. El navegador no remuestrea ni rellena canales.",
          "zhu2019",
        ),
        P(
          "Inference stores each sample-wise P/S/background score array with UTC time axis, source/window ID and checkpoint/preprocessing hashes. Peak distance, phase thresholds and an abstention rule are fixed on validation. Candidate picks are not made solely from the largest score if the window is clipped, gapped or out of the declared domain. Score calibration must be assessed empirically against independent analyst labels and separated from timing residual or between-analyst variation; a high softmax peak alone is not a credible uncertainty interval.",
          "La inferencia conserva arreglos de puntaje P/S/fondo por muestra, eje UTC, ID de fuente/ventana y hashes de checkpoint/proceso. Distancia entre máximos, umbrales y regla de abstención se fijan en validación. No se aceptan marcas sólo por máximo puntaje si la ventana está saturada, con huecos o fuera de dominio. Calibración se mide empíricamente contra marcas independientes y se separa de residuo temporal o desacuerdo entre analistas; un máximo softmax alto no es intervalo creíble.",
          "phasenetofficial",
        ),
        P(
          "The sealed M13 versus M08 test uses identical real held-out trace IDs, windows, QC flags and analyst picks and reports all exclusions across 6,000 selected records. The separate 24-record browser subset contains 23 QC-valid normalized waveforms and one flat-component QC rejection; the rejection stays visible and is never replaced after scoring. Browser inference is an additional gate: probabilities on those 23 arrays must differ from frozen PyTorch by at most 0.001 and picked peaks by at most one 0.01 s sample. Offline metrics cannot substitute for this check.",
          "La prueba sellada M13 frente a M08 usa las mismas trazas reales reservadas, ventanas, banderas QC y marcas humanas, y conserva exclusiones en 6.000 registros. La submuestra web de 24 contiene 23 ondas normalizadas válidas y una rechazada por componente plana; la rechazada sigue visible y no se sustituye tras conocer resultados. La inferencia web exige diferencias de probabilidad ≤0,001 frente a PyTorch y máximos a una muestra de 0,01 s o menos. Las métricas offline no sustituyen esta prueba.",
          "zhu2019",
        ),
      ],
      equations: [
        E(String.raw`\widehat t_{\phi}=t_0+\frac{\arg\max_{0\le n<6000}q_{\phi,n}}{100},\qquad \phi\in\{P,S\}`,
          "q is the uncalibrated phase score at sample n; t₀ is window start in seconds. The global peak becomes a candidate only at score ≥0.8; S abstains when its peak is less than 40 samples after an accepted P.",
          "q es puntaje de fase sin calibrar en muestra n; t₀ es inicio de ventana en segundos. El máximo global sólo es candidato con puntaje ≥0,8; S se abstiene si está a menos de 40 muestras de P aceptada."),
        E(String.raw`\mathcal E_{\rm event}^{a}\cap\mathcal E_{\rm event}^{b}=\varnothing,\quad\mathcal S_{\rm station}^{a}\cap\mathcal S_{\rm station}^{b}=\varnothing\quad(a\ne b)`,
          "E and S are event and station identity sets for any two train, validation or test partitions a,b. Bridge recordings are excluded and counted; the published PhaseNet split is not this stricter gate.",
          "E y S son conjuntos de eventos y estaciones para dos particiones a,b cualesquiera. Se excluyen y cuentan registros puente; la división publicada de PhaseNet no equivale a esta prueba estricta."),
        E(String.raw`\operatorname{precision}_{\phi}=\frac{TP_{\phi}}{TP_{\phi}+FP_{\phi}},\quad\operatorname{recall}_{\phi}=\frac{TP_{\phi}}{TP_{\phi}+FN_{\phi}}`,
          "TP, FP and FN are one-to-one matched, false and missed phase picks on the full eligible held-out population. Undefined denominators remain not-applicable, never an invented zero or perfect score.",
          "TP, FP y FN son marcas emparejadas, falsas y omitidas en toda la población reservada admisible. Denominadores indefinidos quedan no aplicables, nunca cero o puntaje perfecto inventado."),
      ],
      symbols: [
        T("qφ,n: dimensionless P/S score at sample n; n: 0 to 5999 at 100 Hz.", "qφ,n: puntaje P/S sin dimensión en muestra n; n: 0 a 5999 a 100 Hz."),
        T("t̂φ: candidate arrival relative to window start t₀, in seconds.", "t̂φ: llegada candidata relativa al inicio t₀ de la ventana, en segundos."),
        T("E/S: event/station ID sets, not wave-energy or S-phase symbols in the split equation.", "E/S: conjuntos de IDs de eventos/estaciones en ecuación de partición, no energía ni fase S."),
        T("TP/FP/FN: matched, false and missed picks under a fixed per-phase tolerance.", "TP/FP/FN: marcas acertadas, falsas y omitidas con tolerancia fija por fase."),
      ],
      steps: [
        T("Resolve waveform, phase-label, StationXML and checkpoint rights; hash all permitted originals.", "Resolver derechos de ondas, marcas, StationXML y checkpoint; hashear originales permitidos."),
        T("Partition by both event and station IDs, exclude bridges, and freeze the manifest before fitting transforms.", "Particionar por eventos y estaciones, excluir puentes y congelar manifiesto antes de ajustar."),
        T("Record unrestituted counts, E/N/Z order, 100 Hz, 6000-sample window and rejected channel QC.", "Registrar conteos sin corregir, orden E/N/Z, 100 Hz, ventana de 6000 muestras y canales rechazados por QC."),
        T("Construct analyst-centred P/S/background targets and train or fine-tune with validation-only model selection.", "Construir objetivos P/S/fondo centrados en analista y entrenar/ajustar con selección sólo de validación."),
        T("Freeze checkpoint hash, preprocessing, thresholds, peak distance and abstention; export full score arrays.", "Congelar hash, proceso, umbrales, distancia entre máximos y abstención; exportar puntajes completos."),
        T("Evaluate event/station-disjoint held-out traces against M08 on identical windows and labels, retaining failures.", "Evaluar trazas reservadas disjuntas frente a M08 en ventanas y marcas idénticas, conservando fallas."),
        T("Run browser ONNX parity against frozen PyTorch arrays on all 23 QC-valid display traces, preserving the 24th exclusion.", "Probar paridad ONNX web frente a arreglos PyTorch en las 23 trazas válidas y conservar la exclusión número 24."),
      ],
      calloutTitle: T("Unverified implementation and uncertainty", "Implementación e incertidumbre no verificadas"),
      callout: T(
        "This sidecar contains executable browser inference but no bundled model or waveform. The selected model's offline held-out metrics are separate from a browser parity verdict; local file uploads have unverified provenance. Softmax scores remain uncalibrated, and an analyst pick is a fallible reference rather than geological truth.",
        "Esta rama contiene inferencia web ejecutable, sin modelo ni onda incluidos. Las métricas offline del modelo son distintas del veredicto de paridad web; archivos locales tienen procedencia sin verificar. Softmax sigue sin calibrar y la marca de analista es referencia falible, no verdad geológica.",
      ),
      refs: ["zhu2019", "phasenetofficial", "obspyresponse"],
    },
  },
];
