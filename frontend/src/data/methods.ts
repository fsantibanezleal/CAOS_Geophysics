export type Text = [string, string];
export type Formula = { tex: string; caption: Text };
export type Algorithm = {
  id: string;
  title: Text;
  explanation: Text;
  equation: Formula;
  steps: Text[];
  settings: Text;
  history: Text;
  limitation: Text;
};
export type Chapter = {
  id: string;
  title: Text;
  paragraphs: Text[];
  equations: Formula[];
  assumptions: Text;
  refs: string[];
  algorithms: Algorithm[];
};
const T = (en: string, es: string): Text => [en, es];
const E = (tex: string, en: string, es: string): Formula => ({
  tex,
  caption: T(en, es),
});

export const chapters: Chapter[] = [
  {
    id: "potential",
    title: T("Gravity and magnetics", "Gravedad y magnetismo"),
    refs: ["cockett2015", "simpeggravity", "simpegmagnetic"],
    paragraphs: [
      T(
        "Gravity inversion estimates density contrast from the perturbation of the gravitational field. A receiver integrates contributions from the entire subsurface: its value is not a measurement of the material directly beneath it. The model here divides a 2,240 × 1,920 × 1,120 m domain into 28 × 24 × 16 rectangular prisms. Each prism has constant density contrast or susceptibility. SimPEG integrates its response at each receiver; summing the prism contributions gives a linear forward operator. Coordinates are easting, northing and elevation, with elevation positive upward.",
        "La inversión gravimétrica estima contraste de densidad a partir de la perturbación del campo gravitacional. Cada receptor integra contribuciones de todo el subsuelo: no mide sólo el material situado debajo. Aquí el dominio de 2.240 × 1.920 × 1.120 m se divide en 28 × 24 × 16 prismas rectangulares, cada uno con contraste de densidad o susceptibilidad constante. SimPEG integra su respuesta en los receptores; la suma define un operador directo lineal. Las coordenadas son este, norte y elevación positiva hacia arriba.",
      ),
      T(
        "For magnetics, the scalar model assumes magnetization aligned with a uniform inducing field of 50,000 nT, inclination 60° and declination 12°. Total-magnetic-intensity anomalies are linearized as the projection of the anomalous field onto that direction. Consequently, a magnetic extremum need not lie above the causative body. The remanent tabular case deliberately violates the alignment assumption. Its three-component alternative allows an effective magnetization vector in every cell, increasing the number of unknowns without adding observations.",
        "En magnetometría, el modelo escalar supone magnetización alineada con un campo inductor uniforme de 50.000 nT, inclinación de 60° y declinación de 12°. La anomalía de intensidad total se linealiza proyectando el campo anómalo sobre esa dirección. Por ello, un extremo magnético no necesariamente coincide con la posición del cuerpo. El caso tabular remanente viola deliberadamente la alineación. La alternativa vectorial permite tres componentes por celda, aumentando las incógnitas sin agregar observaciones.",
      ),
      T(
        "The reference survey contains 256 stations. There are 10,752 scalar cell values, or 32,256 vector components, so data fit cannot identify a unique model. In matrix terms, directions in or near the null space change the earth model while changing the survey response little. Deep and small bodies are especially weakly constrained. The refined mesh reduces geometric stair-stepping; it does not increase the resolving power of the survey. No topography correction, regional-field estimation or geological boundary parameterization is fitted in these cases.",
        "El levantamiento de referencia contiene 256 estaciones frente a 10.752 valores escalares o 32.256 componentes vectoriales. Por tanto, el ajuste no identifica un modelo único. Las direcciones del espacio nulo o casi nulo modifican el subsuelo con poco cambio en los datos. Cuerpos profundos y pequeños quedan especialmente mal restringidos. Refinar la malla reduce escalones geométricos, pero no aumenta la resolución del levantamiento. Estos casos no ajustan topografía, campo regional ni superficies geológicas parametrizadas.",
      ),
      ["The inverse now whitens observations by noise sigma and penalizes both depth-weighted cell size and derivatives in metres. Horizontal correlation lengths are 240 m; the vertical length is 140 m. An independent calibration fixed the weak depth exponent at 0.375. Discrepancy selects beta without access to display truth. IRLS reweights the smallness term four times while preserving spatial L2 derivatives. Neither method imposes positivity or known body masks, so negative or misplaced estimates remain visible and receive explicit recovery verdicts.","La inversión ahora blanquea observaciones por sigma y penaliza tamaño ponderado por profundidad y derivadas por metro. Las longitudes horizontales son 240 m y la vertical 140 m. Calibración independiente fijó exponente débil 0,375. La discrepancia elige beta sin verdad del caso. IRLS repesa tamaño cuatro veces conservando derivadas L2. No hay positividad ni máscaras de cuerpos conocidas; estimados negativos o desplazados permanecen visibles con veredictos explícitos."],
    ],
    equations: [
      E(
        String.raw`g_z(\mathbf r)=\mathcal G\int_V\Delta\rho(\mathbf r')\frac{z'-z}{\|\mathbf r'-\mathbf r\|^3}\,dV',\qquad \mathbf d=G\mathbf m`,
        "𝒢 is the gravitational constant; Δρ is density contrast; r is a receiver and r′ a source point. G is the prism-response matrix and m the cell-property vector. The integral uses SI units; exported gravity is mGal (10⁻⁵ m/s²).",
        "𝒢 es la constante gravitacional; Δρ es contraste de densidad; r es un receptor y r′ un punto fuente. G es la matriz de respuesta prismática y m las propiedades por celda. La integral usa SI; la gravedad exportada está en mGal (10⁻⁵ m/s²).",
      ),
      E(
        String.raw`\Delta T\simeq\widehat{\mathbf B}_0\cdot\mathbf B_{a},\qquad G(\mathbf m+\mathbf n)=G\mathbf m\quad(G\mathbf n=0)`,
        "ΔT is linearized TMI; Bₐ is the anomalous field and B̂₀ the inducing-field unit vector. A null-space vector n produces no additional measured response, illustrating non-uniqueness.",
        "ΔT es TMI linealizada; Bₐ es el campo anómalo y B̂₀ la dirección unitaria del campo inductor. Un vector n del espacio nulo no cambia la respuesta medida y expresa la no unicidad.",
      ),
    ],
    assumptions: T(
      "Constant properties inside flat rectangular cells; linear superposition; no demagnetization or induced–remanent decomposition. Scalar susceptibility may become negative because the solve is unconstrained. Model-error values require the synthetic truth and are unavailable for an unknown field model.",
      "Propiedades constantes en prismas rectangulares; superposición lineal; sin desmagnetización ni separación inducida–remanente. La susceptibilidad escalar puede ser negativa porque no hay restricciones. El error de modelo requiere la verdad sintética y no está disponible para un subsuelo de campo desconocido.",
    ),
    algorithms: [
  {
    "id": "l2",
    "title": [
      "Spatially regularized L2",
      "L2 con regularización espacial"
    ],
    "explanation": [
      "The solve whitens each observation and operator row by its supplied standard deviation. A sparse positive spatial precision combines cell smallness and first derivatives in physical metres. SimPEG supplies the exact prism operator; the data-space quadratic optimizer and discrepancy selection are implemented locally, not by SimPEG inversion directives.",
      "Se blanquean datos y filas del operador por su desviación estándar. Una precisión espacial dispersa positiva combina tamaño de celda y primeras derivadas en metros. SimPEG aporta el operador prismático; la optimización cuadrática y selección por discrepancia son locales, no directivas de inversión de SimPEG."
    ],
    "equation": {
      "tex": "A=W_dG,\\ b=W_dd,\\quad \\widehat m=Q^{-1}A^T(AQ^{-1}A^T+\\beta I)^{-1}b,\\quad Q=\\mathrm{diag}(w^2)+\\sum_{\\alpha} \\ell_\\alpha^2D_\\alpha^T\\mathrm{diag}(w_{\\mathrm{face}}^2)D_\\alpha",
      "caption": [
        "Wd = diag(1/σ); Dα differentiates cell values per metre; ℓα is correlation length; w is the unit-RMS depth weight proportional to (depth+dz)^−0.375; face weights average adjacent squared weights. Beta balances whitened data and spatial precision.",
        "Wd = diag(1/σ); Dα deriva valores por metro; ℓα es longitud de correlación; w es peso de profundidad de RMS unitario proporcional a (profundidad+dz)^−0,375; se promedian pesos cuadrados en caras. Beta equilibra datos blanqueados y precisión espacial."
      ]
    },
    "steps": [
      [
        "Whiten active survey rows with the recorded noise standard deviations; reserve omitted rows for evaluation.",
        "Blanquear filas activas con desviaciones registradas; reservar filas omitidas para evaluación."
      ],
      [
        "Factor the sparse physical precision and form the symmetric data-space eigensystem.",
        "Factorizar la precisión física dispersa y formar el sistema propio simétrico de datos."
      ],
      [
        "Search beta by discrepancy, multiply by the declared experimental strength, and solve the quadratic inverse.",
        "Buscar beta por discrepancia, multiplicar por fuerza experimental declarada y resolver la inversión cuadrática."
      ],
      [
        "Predict all stations and separately evaluate active, held-out, model-support, background and baseline errors.",
        "Predecir todas las estaciones y evaluar por separado errores activos, omitidos, soporte, fondo y referencia."
      ]
    ],
    "settings": [
      "Physical correlation lengths: 240 m east, 240 m north, 140 m vertical. Depth exponent 0.375 was frozen using independent calibration seeds 67081/67082. Beta is selected from mean squared whitened residual = 1; the regularization variant multiplies it by 0.25/0.018.",
      "Longitudes físicas: 240 m este, 240 m norte y 140 m vertical. Exponente de profundidad 0,375 fijado con semillas independientes 67081/67082. Beta se elige por residuo blanqueado cuadrático medio = 1; la variante lo multiplica por 0,25/0,018."
    ],
    "history": [
      "The trace is mean squared whitened residual on active stations; model penalties are excluded. Saved states and final predictions share explicit state identities.",
      "La trayectoria es residuo blanqueado cuadrático medio en estaciones activas; excluye penalizaciones. Estados guardados y predicciones finales tienen identidad explícita."
    ],
    "limitation": [
      "This is an unconstrained spatial L2 prior, not a uniqueness proof. No positivity, depth-boundary fit or true-mask constraint is imposed. Conditional noise ensembles keep beta and prior fixed and exclude geological ambiguity and bias.",
      "Es un prior L2 espacial sin restricciones, no prueba de unicidad. No se impone positividad, ajuste de interfaces ni máscara verdadera. Los conjuntos de ruido fijan beta y prior y excluyen ambigüedad geológica y sesgo."
    ]
  },
  {
    "id": "irls",
    "title": [
      "Spatial L1/L2 IRLS",
      "IRLS espacial L1/L2"
    ],
    "explanation": [
      "IRLS adds a smoothed L1 smallness preference while retaining the same physical L2 derivative penalty. The first solve uses unit smallness weights. Later solves derive weights from the preceding estimate only; synthetic truth is never used by the inverse. This is not a total-variation method.",
      "IRLS añade preferencia L1 suavizada en tamaño conservando la misma penalización L2 de derivadas físicas. La primera solución usa pesos unitarios; después se calculan sólo del estimado anterior. La verdad sintética nunca entra en la inversión. No es variación total."
    ],
    "equation": {
      "tex": "\\epsilon_k=\\max(0.15\\,P_{95}(|m_k|),10^{-12}),\\quad c_j=(m_{k,j}^2+\\epsilon_k^2)^{-1/2}/\\operatorname{median}(c),\\quad Q_k=\\mathrm{diag}(w^2c)+Q_{\\mathrm{spatial}}",
      "caption": [
        "P95 is the 95th percentile of estimated absolute property; epsilon stabilizes weights. Median normalization applies to unnormalized c. Only the smallness block is reweighted; Qspatial contains fixed physical derivatives.",
        "P95 es percentil 95 de propiedad absoluta estimada; epsilon estabiliza pesos. La normalización por mediana se aplica a c sin normalizar. Sólo cambia el bloque de tamaño; Qespacial conserva derivadas físicas."
      ]
    },
    "steps": [
      [
        "Start with the same uncertainty-weighted spatial L2 system.",
        "Comenzar con el mismo sistema L2 espacial ponderado por incertidumbre."
      ],
      [
        "Derive stabilized smallness weights from the current estimate; keep spatial derivative weights fixed.",
        "Derivar pesos estabilizados de tamaño del estimado; mantener pesos de derivadas espaciales."
      ],
      [
        "Reselect discrepancy beta for each quadratic subproblem and record its objective and residual.",
        "Reelegir beta por discrepancia en cada subproblema y registrar objetivo y residuo."
      ],
      [
        "After four solves, export the last evaluated model and its complete station predictions.",
        "Tras cuatro soluciones, exportar el último modelo evaluado y predicciones completas."
      ]
    ],
    "settings": [
      "Four solves. Epsilon = max(0.15 × estimate absolute-property percentile 95, 10⁻¹²); inverse-root weights divided by their median. Physical lengths and frozen depth prior match L2; beta is recalibrated in each subproblem.",
      "Cuatro soluciones. Epsilon = max(0,15 × percentil 95 de propiedad absoluta estimada, 10⁻¹²); pesos inversos normalizados por mediana. Longitudes y prior de profundidad coinciden con L2; beta se recalibra por subproblema."
    ],
    "history": [
      "The trace is mean squared whitened residual on active stations; model penalties are excluded. Saved states and final predictions share explicit state identities.",
      "La trayectoria es residuo blanqueado cuadrático medio en estaciones activas; excluye penalizaciones. Estados guardados y predicciones finales tienen identidad explícita."
    ],
    "limitation": [
      "Changing weights, epsilon and discrepancy beta means the trace is not convergence of one fixed objective. Sparse-looking support does not establish correct depth or interfaces; evaluate the held-out and support errors.",
      "Al cambiar pesos, epsilon y beta, la trayectoria no demuestra convergencia de un objetivo fijo. El soporte compacto no establece profundidad ni interfaces correctas; evalúe datos omitidos y error del soporte."
    ]
  },
  {
    "id": "vector",
    "title": [
      "Vector magnetization",
      "Magnetización vectorial"
    ],
    "explanation": [
      "Three effective magnetization components replace scalar susceptibility. The operator concatenates component sensitivities and the prior repeats the physical precision for each block. The displayed volume is vector amplitude, not induced scalar susceptibility; direction errors require all three exported components.",
      "Tres componentes efectivas sustituyen la susceptibilidad escalar. El operador concatena sensibilidades y el prior repite la precisión física por bloque. El volumen muestra amplitud vectorial, no susceptibilidad inducida; los errores de dirección requieren las tres componentes."
    ],
    "equation": {
      "tex": "G_v=[G_x\\ G_y\\ G_z],\\quad Q_v=\\mathrm{blockdiag}(Q,Q,Q),\\quad |m_j|=\\sqrt{m_{x,j}^2+m_{y,j}^2+m_{z,j}^2}",
      "caption": [
        "Gv maps three component blocks to TMI; Qv uses the same physical prior per component. The scene displays amplitude in effective SI units, while mean direction error is evaluated on known target support.",
        "Gv transforma tres bloques en TMI; Qv aplica el mismo prior físico por componente. La escena muestra amplitud efectiva SI; el error angular medio se evalúa en el soporte del objetivo conocido."
      ]
    },
    "steps": [
      [
        "Build the three-component magnetic operator for the same station geometry and inducing field.",
        "Construir operador magnético de tres componentes con las mismas estaciones y campo inductor."
      ],
      [
        "Whiten active survey rows with the recorded noise standard deviations; reserve omitted rows for evaluation.",
        "Blanquear filas activas con desviaciones registradas; reservar filas omitidas para evaluación."
      ],
      [
        "Factor the sparse physical precision and form the symmetric data-space eigensystem.",
        "Factorizar la precisión física dispersa y formar el sistema propio simétrico de datos."
      ],
      [
        "Export the final vector field, scalar amplitudes and target-support angular error; no scalar replay is substituted for vector states.",
        "Exportar vectores finales, amplitudes y error angular en soporte; no sustituir estados vectoriales por reproducción escalar."
      ]
    ],
    "settings": [
      "Physical correlation lengths: 240 m east, 240 m north, 140 m vertical. Depth exponent 0.375 was frozen using independent calibration seeds 67081/67082. Beta is selected from mean squared whitened residual = 1; the regularization variant multiplies it by 0.25/0.018.",
      "Longitudes físicas: 240 m este, 240 m norte y 140 m vertical. Exponente de profundidad 0,375 fijado con semillas independientes 67081/67082. Beta se elige por residuo blanqueado cuadrático medio = 1; la variante lo multiplica por 0,25/0,018."
    ],
    "history": [
      "The trace is mean squared whitened residual on active stations; model penalties are excluded. Saved states and final predictions share explicit state identities.",
      "La trayectoria es residuo blanqueado cuadrático medio en estaciones activas; excluye penalizaciones. Estados guardados y predicciones finales tienen identidad explícita."
    ],
    "limitation": [
      "32,256 vector unknowns remain constrained by at most 256 observations. Scalar amplitudes do not show direction. Remanence recovery must be assessed using component and angular errors, not data fit alone.",
      "32.256 incógnitas vectoriales quedan restringidas por hasta 256 observaciones. Amplitudes escalares no muestran dirección. La remanencia debe evaluarse con errores de componentes y ángulo, no sólo ajuste."
    ]
  }
],
  },
  {
    id: "mt",
    title: T("Magnetotellurics", "Magnetotelúrica"),
    refs: ["heagy2017", "goyes2024", "scipytrf"],
    paragraphs: [
      T(
        "Magnetotelluric sounding measures the complex relation between horizontal electric and magnetic fields over frequency. In a horizontally layered, isotropic earth the impedance depends on the resistivities and thicknesses of all layers. It is not a direct measurement of resistivity at one depth. The four cases use different resistive covers, conductors and basement sequences. Layer thicknesses are known during inversion here, so the unknown vector contains only one resistivity per layer, including the infinite basement.",
        "El sondeo magnetotelúrico mide la relación compleja entre campos eléctricos y magnéticos horizontales según frecuencia. En una Tierra horizontalmente estratificada e isotrópica, la impedancia depende de resistividades y espesores de todas las capas. No mide resistividad a una profundidad única. Los cuatro casos contienen coberturas, conductores y basamentos diferentes. Aquí los espesores son conocidos al invertir; las incógnitas son las resistividades de cada capa, incluido el semiespacio basal.",
      ),
      T(
        "The forward calculation starts at the basement and propagates impedance upward through each finite layer. The complex propagation constant couples attenuation and phase delay. At the surface, apparent resistivity is calculated from impedance magnitude, while phase measures the electric–magnetic phase relation. In a homogeneous halfspace apparent resistivity equals the true resistivity and phase is 45° for the sign convention used here. Those identities are tested independently of the inverse solver.",
        "El cálculo directo parte del basamento y propaga impedancia hacia arriba por cada capa finita. La constante compleja de propagación combina atenuación y desfase. En superficie, la resistividad aparente deriva de la magnitud de impedancia y la fase mide la relación eléctrica–magnética. En un semiespacio homogéneo, la resistividad aparente coincide con la real y la fase es 45° con esta convención. Estas identidades se prueban independientemente del inversor.",
      ),
      T(
        "Frequency controls a broad sensitivity distribution. In a homogeneous conductor the skin depth grows with the square root of resistivity divided by frequency; layered media do not preserve a one-to-one frequency–depth map. A thin conductor can be constrained mainly through its conductance, thickness divided by resistivity. Because thickness is fixed in this experiment, the inversion does not explore that full trade-off. Reducing the frequency set or extending its low-frequency end changes the available information, not just the curve display.",
        "La frecuencia controla una distribución amplia de sensibilidad. En un conductor homogéneo, la penetración crece con la raíz de resistividad dividida por frecuencia; las capas no mantienen una correspondencia única frecuencia–profundidad. Un conductor delgado puede quedar restringido principalmente por su conductancia, espesor dividido por resistividad. Como el espesor es fijo aquí, no se explora toda esa compensación. Reducir frecuencias o extender la banda baja cambia la información disponible, no sólo la curva.",
      ),
      T(
        "All three inversions fit real and imaginary impedance with the same mean-of-real-components objective, bounds 1–6000 Ω m, initial 100 Ω m and beta. Data and regularization scaling are now matched. TRF, projected Adam and the per-sounding neural parameterization differ in optimizer and feasible parameterization, not loss normalization. Every saved model is independently evaluated after its update; the final selected model is appended and generates all final curves.",
        "Las tres inversiones ajustan partes real e imaginaria con el mismo objetivo medio por componentes reales, cotas 1–6000 Ω m, inicio 100 Ω m y beta. Se igualan escalas de datos y regularización. TRF, Adam proyectado y red por sondeo difieren en optimizador y parametrización, no normalización. Cada modelo guardado se evalúa después de actualizar; el final se añade y genera todas las curvas.",
      ),
    ],
    equations: [
      E(
        String.raw`\begin{aligned}\omega&=2\pi f,\quad k_j=\sqrt{i\omega\mu_0/\rho_j},\quad w_j=\sqrt{i\omega\mu_0\rho_j}\\Z_n&=w_n,\qquad Z_j=w_j\frac{Z_{j+1}+w_j\tanh(k_jh_j)}{w_j+Z_{j+1}\tanh(k_jh_j)}\end{aligned}`,
        "f is frequency (Hz), i² = −1, μ₀ = 4π×10⁻⁷ H/m, ρⱼ is layer resistivity (Ω m), hⱼ its thickness (m), kⱼ its propagation constant and wⱼ its intrinsic impedance. Zₙ is the infinite-basement impedance; Z₁ is the surface response.",
        "f es frecuencia (Hz), i² = −1, μ₀ = 4π×10⁻⁷ H/m, ρⱼ resistividad (Ω m), hⱼ espesor (m), kⱼ constante de propagación y wⱼ impedancia intrínseca. Zₙ corresponde al basamento infinito; Z₁ a superficie.",
      ),
      E(
        String.raw`\rho_a=\frac{|Z_1|^2}{\mu_0\omega},\qquad \phi=\arg Z_1,\qquad \delta=\sqrt{\frac{2\rho}{\mu_0\omega}}`,
        "ρₐ is apparent resistivity (Ω m), φ is phase (shown in degrees), and δ is homogeneous-medium skin depth (m). δ is not the depth assigned to a plotted apparent-resistivity value.",
        "ρₐ es resistividad aparente (Ω m), φ es fase (mostrada en grados) y δ penetración en medio homogéneo (m). δ no asigna una profundidad única al valor de resistividad aparente.",
      ),
    ],
    assumptions: T(
      "Plane-wave source, isotropic nonmagnetic layers, known thicknesses, no lateral structure, static shift or galvanic distortion. Independent Gaussian noise is added to each impedance component. A complex WRMS near √2, rather than 1, is expected at the true response under this two-component noise convention.",
      "Fuente de onda plana, capas isotrópicas no magnéticas, espesores conocidos, sin estructura lateral, desplazamiento estático ni distorsión galvánica. Se agrega ruido gaussiano independiente a cada componente de impedancia. Con esta convención, el WRMS complejo esperado en la respuesta verdadera es cercano a √2, no a 1.",
    ),
    algorithms: [
  {
    "id": "mt-lm",
    "title": [
      "Bounded trust-region least squares (TRF)",
      "Mínimos cuadrados acotados (TRF)"
    ],
    "explanation": [
      "SciPy’s trust-region reflective algorithm fits the complex layered impedance via stacked real residuals. Data residuals are divided by √(2NA), and adjacent log-layer differences by √(L−1). Thus twice SciPy’s reported cost is the common complete objective J. This is TRF, not Levenberg–Marquardt.",
      "TRF de SciPy ajusta impedancia estratificada con residuos reales apilados. Los residuos se dividen por √(2NA) y las diferencias logarítmicas por √(L−1). Dos veces el costo de SciPy equivale al objetivo completo J. Es TRF, no Levenberg–Marquardt."
    ],
    "equation": {
      "tex": "J(x)=\\frac1{2N_A}\\sum_{i\\in A}\\left[\\left(\\frac{\\Re\\Delta Z_i}{\\sigma_i}\\right)^2+\\left(\\frac{\\Im\\Delta Z_i}{\\sigma_i}\\right)^2\\right]+\\frac{\\beta}{L-1}\\sum_{j=1}^{L-1}(x_{j+1}-x_j)^2,\\quad 0\\le x_j\\le\\ln6000",
      "caption": [
        "x = ln resistivity; ΔZi is predicted minus observed impedance; sigma is uncertainty of each independent real component; NA is active-frequency count; L is layer count. The spatial term is zero for one layer. All three solvers minimize this same J.",
        "x = ln resistividad; ΔZi es impedancia predicha menos observada; sigma es incertidumbre por componente real; NA es cantidad de frecuencias activas; L cuenta capas. El prior es cero para una capa. Los tres métodos minimizan el mismo J."
      ]
    },
    "steps": [
      [
        "Validate positive frequencies, thicknesses, uncertainties and common resistivity bounds; initialize every layer at 100 Ω m.",
        "Validar frecuencias, espesores, incertidumbres y cotas positivas; iniciar cada capa en 100 Ω m."
      ],
      [
        "Apply exactly the same active-frequency real-component normalization and mean adjacent-log-layer penalty.",
        "Aplicar idéntica normalización real en frecuencias activas y penalización media de diferencias logarítmicas."
      ],
      [
        "Evaluate every saved physical model independently with its own complete objective, avoiding mutable parameter aliases.",
        "Evaluar cada modelo físico guardado con su propio objetivo completo, evitando alias de parámetros mutables."
      ],
      [
        "Append the selected final model and freshly computed objective; calculate final curves from that identical state.",
        "Añadir modelo final seleccionado y objetivo recalculado; obtener curvas finales del mismo estado."
      ]
    ],
    "settings": [
      "CPU float64; bounds 1–6000 Ω m; common initial 100 Ω m; max_nfev 400; ftol = xtol = gtol = 10⁻¹⁰; β = 0.001, or 0.3 for stronger regularization. Canonical soundings use 36 frequencies, or 18 active in coverage tests.",
      "CPU float64; cotas 1–6000 Ω m; inicio común 100 Ω m; max_nfev 400; ftol = xtol = gtol = 10⁻¹⁰; β = 0,001 o 0,3 con regularización mayor. Sondeos canónicos de 36 frecuencias, 18 activas en cobertura."
    ],
    "history": [
      "Recorded complete J includes residual evaluations that may be rejected optimizer trials, not just accepted iterations. The final entry is the selected returned model evaluated again; it matches the final curves.",
      "J completo registrado incluye evaluaciones residuales que pueden ser ensayos rechazados, no sólo iteraciones aceptadas. La última entrada reevalúa el modelo devuelto y coincide con las curvas finales."
    ],
    "limitation": [
      "Layer thicknesses remain prescribed, and low impedance residual does not establish unique resistivities. Local identifiability and bounds are evaluated separately. Conditional bootstrap intervals exclude thickness, dimensionality and correlated-noise uncertainty.",
      "Los espesores son prescritos y un residuo bajo no establece resistividades únicas. Se evalúan identificabilidad local y cotas por separado. Intervalos bootstrap excluyen incertidumbre de espesores, dimensionalidad y ruido correlacionado."
    ]
  },
  {
    "id": "mt-adam",
    "title": [
      "Projected Adam impedance inversion",
      "Inversión de impedancia por Adam proyectado"
    ],
    "explanation": [
      "CPU PyTorch differentiates the same complex recursion and objective. Adam updates log resistivities, then projects them onto the same log bounds as TRF. Every candidate is copied after the update and evaluated afresh; minimum complete objective selects the returned model without reading geological truth.",
      "PyTorch CPU diferencia la misma recursión y objetivo. Adam actualiza log resistividades y las proyecta a las mismas cotas que TRF. Cada candidato se copia después de actualizar y se reevalúa; el mínimo objetivo completo selecciona el retorno sin leer verdad geológica."
    ],
    "equation": {
      "tex": "J(x)=\\frac1{2N_A}\\sum_{i\\in A}\\left[\\left(\\frac{\\Re\\Delta Z_i}{\\sigma_i}\\right)^2+\\left(\\frac{\\Im\\Delta Z_i}{\\sigma_i}\\right)^2\\right]+\\frac{\\beta}{L-1}\\sum_{j=1}^{L-1}(x_{j+1}-x_j)^2,\\quad 0\\le x_j\\le\\ln6000",
      "caption": [
        "x = ln resistivity; ΔZi is predicted minus observed impedance; sigma is uncertainty of each independent real component; NA is active-frequency count; L is layer count. The spatial term is zero for one layer. All three solvers minimize this same J.",
        "x = ln resistividad; ΔZi es impedancia predicha menos observada; sigma es incertidumbre por componente real; NA es cantidad de frecuencias activas; L cuenta capas. El prior es cero para una capa. Los tres métodos minimizan el mismo J."
      ]
    },
    "steps": [
      [
        "Validate positive frequencies, thicknesses, uncertainties and common resistivity bounds; initialize every layer at 100 Ω m.",
        "Validar frecuencias, espesores, incertidumbres y cotas positivas; iniciar cada capa en 100 Ω m."
      ],
      [
        "Apply exactly the same active-frequency real-component normalization and mean adjacent-log-layer penalty.",
        "Aplicar idéntica normalización real en frecuencias activas y penalización media de diferencias logarítmicas."
      ],
      [
        "Evaluate every saved physical model independently with its own complete objective, avoiding mutable parameter aliases.",
        "Evaluar cada modelo físico guardado con su propio objetivo completo, evitando alias de parámetros mutables."
      ],
      [
        "Append the selected final model and freshly computed objective; calculate final curves from that identical state.",
        "Añadir modelo final seleccionado y objetivo recalculado; obtener curvas finales del mismo estado."
      ]
    ],
    "settings": [
      "1,200 updates; initial learning rate 0.06, multiplied by 1/2 after half the fixed budget and 1/4 after three quarters. Common 1–6000 Ω m bounds and β. Save every 20 updates and append the selected final state.",
      "1.200 actualizaciones; tasa inicial 0,06, multiplicada por 1/2 tras mitad de presupuesto y 1/4 tras tres cuartos. Cotas comunes 1–6000 Ω m y β. Guardar cada 20 pasos y añadir estado final seleccionado."
    ],
    "history": [
      "Complete matched J at the initial model and recorded post-update states, then at the minimum-objective selected model. A finite budget is not a convergence certificate; model and loss always refer to the same copied array.",
      "J completo equivalente en modelo inicial y estados posteriores guardados, luego en el modelo de menor objetivo. Presupuesto finito no certifica convergencia; modelo y pérdida usan la misma matriz copiada."
    ],
    "limitation": [
      "Layer thicknesses remain prescribed, and low impedance residual does not establish unique resistivities. Local identifiability and bounds are evaluated separately. Conditional bootstrap intervals exclude thickness, dimensionality and correlated-noise uncertainty.",
      "Los espesores son prescritos y un residuo bajo no establece resistividades únicas. Se evalúan identificabilidad local y cotas por separado. Intervalos bootstrap excluyen incertidumbre de espesores, dimensionalidad y ruido correlacionado."
    ]
  },
  {
    "id": "mt-neural",
    "title": [
      "Per-sounding physics-guided neural inversion",
      "Inversión neuronal física por sondeo"
    ],
    "explanation": [
      "A 1–24–24–1 tanh network takes normalized layer index and predicts a bounded log-resistivity residual about the same 100 Ω m initial model. The last layer starts at zero so all solvers share exactly the initial profile. The network is optimized separately for each sounding using the analytical impedance recursion; it is neither a pretrained inverse nor a PDE-residual PINN.",
      "Una red tanh 1–24–24–1 usa índice normalizado de capa y predice un residuo logarítmico acotado respecto al mismo inicio 100 Ω m. La última capa inicia en cero para compartir perfil inicial exacto. Se optimiza por sondeo con recursión analítica; no es inversor preentrenado ni PINN con residuo diferencial."
    ],
    "equation": {
      "tex": "x_j=x_{\\min}+(x_{\\max}-x_{\\min})\\,\\sigma\\!\\left[\\operatorname{logit}\\frac{x_j^0-x_{\\min}}{x_{\\max}-x_{\\min}}+N_\\theta(j/(L-1))\\right]",
      "caption": [
        "x is log resistivity; xmin = 0 and xmax = ln6000; x0 = ln100; sigma is logistic sigmoid. The objective is the same J as TRF and direct Adam. Normalized input for one layer is zero.",
        "x es log resistividad; xmin = 0, xmax = ln6000 y x0 = ln100; sigma es sigmoide logística. El objetivo es el mismo J de TRF y Adam directo. Para una capa, entrada normalizada cero."
      ]
    },
    "steps": [
      [
        "Validate positive frequencies, thicknesses, uncertainties and common resistivity bounds; initialize every layer at 100 Ω m.",
        "Validar frecuencias, espesores, incertidumbres y cotas positivas; iniciar cada capa en 100 Ω m."
      ],
      [
        "Apply exactly the same active-frequency real-component normalization and mean adjacent-log-layer penalty.",
        "Aplicar idéntica normalización real en frecuencias activas y penalización media de diferencias logarítmicas."
      ],
      [
        "Evaluate every saved physical model independently with its own complete objective, avoiding mutable parameter aliases.",
        "Evaluar cada modelo físico guardado con su propio objetivo completo, evitando alias de parámetros mutables."
      ],
      [
        "Append the selected final model and freshly computed objective; calculate final curves from that identical state.",
        "Añadir modelo final seleccionado y objetivo recalculado; obtener curvas finales del mismo estado."
      ]
    ],
    "settings": [
      "CPU float64; seeded 1–24–24–1 network; 1,800 Adam updates; initial rate 0.015 with the same half/quarter schedule; tanh hidden activations. The common bounded objective uses no target layer resistivities.",
      "CPU float64; red 1–24–24–1 con semilla; 1.800 pasos Adam; tasa 0,015 con el mismo esquema mitad/cuarto; activaciones tanh. El objetivo acotado común no utiliza resistividades objetivo."
    ],
    "history": [
      "Complete matched objective recorded every 20 post-update states and for the selected minimum-objective model. These are per-sounding optimization states, not a training dataset learning curve.",
      "Objetivo completo común cada 20 estados posteriores y en el modelo de menor objetivo seleccionado. Son estados de optimización por sondeo, no curva de entrenamiento de un conjunto."
    ],
    "limitation": [
      "Layer thicknesses remain prescribed, and low impedance residual does not establish unique resistivities. Local identifiability and bounds are evaluated separately. Conditional bootstrap intervals exclude thickness, dimensionality and correlated-noise uncertainty.",
      "Los espesores son prescritos y un residuo bajo no establece resistividades únicas. Se evalúan identificabilidad local y cotas por separado. Intervalos bootstrap excluyen incertidumbre de espesores, dimensionalidad y ruido correlacionado."
    ]
  }
],
  },
  {
    id: "seismic",
    title: T("Acoustic FWI", "FWI acústica"),
    refs: ["virieux2009", "deepwave", "adam"],
    paragraphs: [
      T(
        "Full-waveform inversion estimates a velocity field by matching the pressure histories recorded at receivers for known seismic sources. The forward problem propagates waves through a candidate velocity field. Interfaces change propagation speed and create reflected and transmitted energy; lateral discontinuities also diffract the wavefield. Unlike potential-field inversion, the map from velocity to a receiver time series is nonlinear. The acoustic approximation used here treats density as constant and omits shear waves, attenuation and a free surface.",
        "La inversión de onda completa estima velocidad ajustando historias de presión en receptores para fuentes conocidas. El problema directo propaga ondas por una velocidad candidata. Las interfaces cambian la velocidad y generan reflexión y transmisión; discontinuidades laterales difractan. A diferencia de campos potenciales, la relación entre velocidad y serie temporal es no lineal. Aquí la aproximación acústica supone densidad constante y excluye ondas de corte, atenuación y superficie libre.",
      ),
      T(
        "Deepwave evaluates a finite-difference acoustic propagator on 128 × 96 nodes at 12.5 m spacing. Three sources at 75 m depth illuminate the layered, faulted, salt and gas-channel models. Forty receivers, or twenty under reduced coverage, lie at the same depth. The record lasts 1.6 s at a computational time step of 0.5 ms. Exported receiver traces are sampled every 4 ms; wavefield images every 24 ms. Those display samples are not the internal time integration step.",
        "Deepwave evalúa un propagador acústico de diferencias finitas en 128 × 96 nodos separados 12,5 m. Tres fuentes a 75 m iluminan modelos estratificado, fallado, salino y de canal de gas. Cuarenta receptores, o veinte con cobertura reducida, están a igual profundidad. El registro dura 1,6 s con paso de cálculo de 0,5 ms. Las trazas se exportan cada 4 ms y campos cada 24 ms. El muestreo visual no es el paso de integración.",
      ),
      T(
        "Automatic differentiation computes the derivative of the discrete receiver loss with respect to velocity parameters. Its adjoint interpretation is to propagate data residual information backward and combine it with the forward wavefield. A directional finite-difference test checks that this gradient agrees with perturbations of the implemented simulator. This test verifies a derivative, not a correct recovered geology. Limited illumination and the oscillatory waveform objective can leave the model far from truth despite substantial loss reduction.",
        "La diferenciación automática calcula la derivada de la pérdida discreta respecto a parámetros de velocidad. Su interpretación adjunta propaga información del residuo hacia atrás y la combina con el campo directo. Una prueba direccional por diferencias finitas verifica acuerdo con perturbaciones del simulador. Verifica la derivada, no la geología recuperada. La iluminación limitada y el objetivo oscilatorio pueden dejar un modelo lejos de la verdad pese a reducir mucho la pérdida.",
      ),
      T(
        "Cycle skipping arises when a local update matches the wrong oscillation. Both methods first fit a data-only 1D background from an independent depth trend, then refine spatial controls under an identical physical-gradient prior. One branch uses full-band traces; the other uses a fixed 3, 5, 8, 14 Hz schedule selected on separate calibration geometry. Each stage receives 28 L-BFGS calls; stages and accepted states are recorded. A finite budget does not certify a global solution, and withheld receiver data never select the model.",
        "El salto de ciclo aparece al ajustar una oscilación equivocada. Ambos métodos ajustan primero un fondo 1D desde tendencia independiente y refinan controles espaciales con el mismo prior físico. Una rama usa banda completa y otra secuencia 3, 5, 8, 14 Hz fijada con geometría separada. Cada etapa recibe 28 llamadas L-BFGS; se registran etapas y estados aceptados. Presupuesto finito no certifica solución global, y receptores omitidos nunca seleccionan modelo.",
      ),
    ],
    equations: [
      E(
        String.raw`\frac1{v(\mathbf x)^2}\frac{\partial^2p}{\partial t^2}-\nabla^2p=s(\mathbf x,t),\qquad d_s=R_sp_s`,
        "v is velocity (m/s), p pressure, s the source term and Rₛ the sampling operator at receivers for shot s. Deepwave solves the discrete constant-density acoustic equation with absorbing boundaries.",
        "v es velocidad (m/s), p presión, s la fuente y Rₛ el muestreo en receptores del disparo s. Deepwave resuelve la ecuación acústica discreta de densidad constante con fronteras absorbentes.",
      ),
      E(
        String.raw`v=1400+3000\,\sigma(p),\qquad \frac{\partial J}{\partial p}=\frac{\partial J}{\partial v}\,3000\sigma(p)(1-\sigma(p))`,
        "Here p denotes the unconstrained optimization parameter, not acoustic pressure; σ is the logistic sigmoid. This map bounds velocity to 1,400–4,400 m/s and rescales its gradient by the chain rule.",
        "Aquí p representa el parámetro de optimización, no presión acústica; σ es la sigmoide logística. La transformación acota velocidad a 1.400–4.400 m/s y escala su gradiente por la regla de la cadena.",
      ),
    ],
    assumptions: T(
      "Known source wavelet, fixed source/receiver geometry, constant density and two-dimensional propagation. PML boundaries absorb outgoing waves; there is no free-surface reflection. A pressure animation visualizes the known-model forward solve, not uncertainty or the current inverse iterate.",
      "Ondícula conocida, geometría fija, densidad constante y propagación bidimensional. Las fronteras PML absorben ondas; no hay reflexión de superficie libre. La animación muestra el cálculo directo del modelo conocido, no incertidumbre ni la iteración inversa actual.",
    ),
    algorithms: [
  {
    "id": "fwi-l2",
    "title": [
      "Full-band acoustic FWI",
      "FWI acústica de banda completa"
    ],
    "explanation": [
      "After the shared data-only 1D background, this comparator uses full-band waveforms on every 2D control grid. It shares priors, initialization, receivers and optimizer-call budget with frequency continuation. Both branches use bounded multiresolution logits, not the old full-grid Adam parameterization.",
      "Después del fondo 1D compartido ajustado sólo a datos, este comparador usa banda completa en cada malla 2D. Comparte prior, inicio, receptores y llamadas con continuación. Ambas ramas usan logits multirresolución acotados, no la antigua parametrización Adam de malla completa."
    ],
    "equation": {
      "tex": "\\Phi(q)=\\frac{\\operatorname{mean}_{A,s,t}|L_{f_c}(F(v(q))-d)|^2}{\\operatorname{mean}_{A,s,t}|L_{f_c}d|^2}+\\beta\\sum_{\\alpha=x,z}\\operatorname{mean}\\left(\\frac{\\Delta_\\alpha v}{10\\,\\Delta\\alpha}\\right)^2,\\quad v(q)=1400+3000\\,\\sigma(Bq)",
      "caption": [
        "A denotes active receivers; F is constant-density propagation; d is measured synthetic pressure; Lfc is the cutoff filter; B bilinearly interpolates control logits. Gradient scales are 100 m and 1000 m/s. This energy-normalized objective is not a colored-noise likelihood.",
        "A son receptores activos; F es propagación de densidad constante; d es presión sintética medida; Lfc es filtro de corte; B interpola bilinealmente logits. Escalas de gradiente: 100 m y 1000 m/s. El objetivo normalizado por energía no es verosimilitud de ruido coloreado."
      ]
    },
    "steps": [
      [
        "Start from the independent 1800 + 0.88 z m/s trend and fit a laterally constant 1 × 12 logit control grid at 3 Hz.",
        "Partir de tendencia independiente 1800 + 0,88 z m/s y ajustar controles logit 1 × 12 lateralmente constantes a 3 Hz."
      ],
      [
        "Refine to 9 × 12, 17 × 24 and 33 × 48 controls with aligned endpoints; never initialize from smoothed truth.",
        "Refinar controles 9 × 12, 17 × 24 y 33 × 48 con extremos alineados; nunca iniciar desde verdad suavizada."
      ],
      [
        "Optimize active receiver data only with L-BFGS strong-Wolfe; evaluate each accepted update including the terminal update.",
        "Optimizar sólo receptores activos con L-BFGS strong-Wolfe; evaluar cada actualización aceptada incluida la terminal."
      ],
      [
        "Export terminal model, identical final frame and recomputed predictions; score whole-model and withheld errors separately.",
        "Exportar modelo terminal, cuadro final idéntico y predicciones recalculadas; evaluar modelo total y datos omitidos por separado."
      ]
    ],
    "settings": [
      "28 L-BFGS calls per stage, four stages; history size 15. CPU/GPU propagator: fourth-order spatial differences, dt 0.5 ms, 3,200 samples (1.6 s), 300 m PML, fixed maximum propagation velocity 4600 m/s. Inverse bounds 1400–4400 m/s; β 0.001 or 0.03. Every fifth receiver (index mod 5 = 2) is withheld.",
      "28 llamadas L-BFGS por etapa, cuatro etapas; memoria 15. Propagador CPU/GPU de cuarto orden, dt 0,5 ms, 3.200 muestras (1,6 s), PML 300 m, velocidad máxima de propagación fija 4600 m/s. Cotas inversas 1400–4400 m/s; β 0,001 o 0,03. Se omite cada quinto receptor (índice mod 5 = 2)."
    ],
    "history": [
      "Raw full-band relative waveform MSE at evaluated stage-entry and accepted-call states. Filtered objective and regularization are separate exported history terms. Frames map explicitly to history records; final model and predictions use the same terminal state.",
      "MSE relativo sin filtrar en entradas de etapa y estados de llamadas aceptadas. Objetivo filtrado y regularización se exportan aparte. Los cuadros se enlazan a registros; modelo final y predicciones usan el mismo estado terminal."
    ],
    "limitation": [
      "Finite-budget baseline improvement is not exact geology, uniqueness or field performance. The known source and same-operator synthetic observations simplify the inverse. Salt remains a declared cycle-skipping challenge with failures visible; source estimation and elastic physics are excluded.",
      "Mejorar referencia con presupuesto finito no es geología exacta, unicidad ni rendimiento de campo. Fuente conocida y mismo operador sintético simplifican la inversión. La sal mantiene desafío de salto de ciclos y fallos visibles; no se estima fuente ni física elástica."
    ]
  },
  {
    "id": "fwi-multiscale",
    "title": [
      "Frequency-continuation acoustic FWI",
      "FWI acústica con continuación en frecuencia"
    ],
    "explanation": [
      "Zero-phase sixth-order Butterworth amplitude filtering selects physical cutoff frequencies, replacing the ineffective moving-average windows. Both observed and predicted traces use the same zero-padded FFT filter. The 3 Hz background is followed by 5, 8 and 14 Hz 2D stages, at the same spatial grids and compute budget as the full-band comparator.",
      "El filtrado de amplitud Butterworth de orden seis y fase cero selecciona cortes físicos, sustituyendo ventanas móviles ineficaces. Trazas observadas y predichas usan el mismo filtro FFT con ceros. Al fondo 3 Hz siguen etapas 2D de 5, 8 y 14 Hz con iguales mallas y presupuesto que banda completa."
    ],
    "equation": {
      "tex": "H(f;f_c)=\\left[1+(|f|/f_c)^{12}\\right]^{-1/2},\\quad L_{f_c}d=\\mathrm{crop}\\,\\mathcal F^{-1}\\!\\left(H\\,\\mathcal F(\\mathrm{pad}(d))\\right)",
      "caption": [
        "fc is cutoff in Hz; FFT padding reaches a power of two at least twice the trace length; output is cropped to the original record. The filter is zero-phase, not a causal IIR or moving average, and cannot create absent low-frequency information.",
        "fc es corte en Hz; se rellena a potencia de dos al menos doble del largo y se recorta al registro original. Es fase cero, no IIR causal ni promedio móvil; no crea información baja ausente."
      ]
    },
    "steps": [
      [
        "Start from the independent 1800 + 0.88 z m/s trend and fit a laterally constant 1 × 12 logit control grid at 3 Hz.",
        "Partir de tendencia independiente 1800 + 0,88 z m/s y ajustar controles logit 1 × 12 lateralmente constantes a 3 Hz."
      ],
      [
        "Refine to 9 × 12, 17 × 24 and 33 × 48 controls with aligned endpoints; never initialize from smoothed truth.",
        "Refinar controles 9 × 12, 17 × 24 y 33 × 48 con extremos alineados; nunca iniciar desde verdad suavizada."
      ],
      [
        "Optimize active receiver data only with L-BFGS strong-Wolfe; evaluate each accepted update including the terminal update.",
        "Optimizar sólo receptores activos con L-BFGS strong-Wolfe; evaluar cada actualización aceptada incluida la terminal."
      ],
      [
        "Export terminal model, identical final frame and recomputed predictions; score whole-model and withheld errors separately.",
        "Exportar modelo terminal, cuadro final idéntico y predicciones recalculadas; evaluar modelo total y datos omitidos por separado."
      ]
    ],
    "settings": [
      "Cutoffs 3 → 5 → 8 → 14 Hz at control grids 1 × 12 → 9 × 12 → 17 × 24 → 33 × 48. The independent calibration froze this schedule before nominal evaluation. All propagation, regularization and call-budget settings match the comparator.",
      "Cortes 3 → 5 → 8 → 14 Hz en controles 1 × 12 → 9 × 12 → 17 × 24 → 33 × 48. Calibración independiente fijó la secuencia antes de evaluar casos nominales. Propagación, regularización y presupuesto coinciden con comparador."
    ],
    "history": [
      "Raw full-band relative waveform MSE at evaluated stage-entry and accepted-call states. Filtered objective and regularization are separate exported history terms. Frames map explicitly to history records; final model and predictions use the same terminal state.",
      "MSE relativo sin filtrar en entradas de etapa y estados de llamadas aceptadas. Objetivo filtrado y regularización se exportan aparte. Los cuadros se enlazan a registros; modelo final y predicciones usan el mismo estado terminal."
    ],
    "limitation": [
      "Finite-budget baseline improvement is not exact geology, uniqueness or field performance. The known source and same-operator synthetic observations simplify the inverse. Salt remains a declared cycle-skipping challenge with failures visible; source estimation and elastic physics are excluded.",
      "Mejorar referencia con presupuesto finito no es geología exacta, unicidad ni rendimiento de campo. Fuente conocida y mismo operador sintético simplifican la inversión. La sal mantiene desafío de salto de ciclos y fallos visibles; no se estima fuente ni física elástica."
    ]
  }
],
  },
  {
  "id": "joint",
  "title": [
    "Structural and petrophysical inversion",
    "Inversión estructural y petrofísica"
  ],
  "refs": [
    "crossgradient",
    "astic2020",
    "cockett2015"
  ],
  "paragraphs": [
    [
      "Gravity and magnetic observations constrain different physical properties. Their shared boundaries are a hypothesis, not a universal law. The application now compares an uncoupled multi-property baseline, physical cross-gradient coupling and a distinct Gaussian-mixture petrophysical prior. All three use the same active data, uncertainty, starting estimates, spatial precisions and optimizer budget. This matched comparison isolates the added prior instead of confounding coupling with different initialization or penalties.",
      "Gravedad y magnetismo restringen propiedades distintas. Compartir límites es una hipótesis, no ley universal. Se comparan una referencia multipropiedad desacoplada, gradiente cruzado físico y un prior petrofísico diferente de mezcla gaussiana. Los tres usan datos, incertidumbre, estimados iniciales, precisiones espaciales y presupuesto iguales. Así se aísla el prior añadido sin confundirlo con inicialización o penalizaciones."
    ],
    [
      "For structural coupling, density is normalized by 0.5 g/cm³ and susceptibility by 0.03 SI. Derivatives divide differences by physical cell spacing in metres. The mean squared cross-gradient is multiplied by 240⁴ and divided by its value at the matched independent initialization (floor 10⁻¹²). A diagonal quadratic-Hessian preconditioner scales optimizer variables. This normalization uses no target truth. Parallel, antiparallel or vanishing gradients all make the penalty small; this is not proof of matching interfaces. Inspect density and susceptibility recovery, active and omitted station errors, and change relative to the independent model.",
      "En acoplamiento estructural se normaliza densidad por 0,5 g/cm³ y susceptibilidad por 0,03 SI. Derivadas dividen diferencias por espaciamiento en metros. La media del gradiente cruzado cuadrado se multiplica por 240⁴ y divide por su valor en la inicialización independiente común (piso 10⁻¹²). Un precondicionador Hessiano diagonal escala variables. Esta normalización no usa verdad objetivo. Gradientes paralelos, antiparalelos o nulos reducen la penalización sin probar interfaces correctas. Inspeccione ambas propiedades, estaciones activas/omitidas y cambio respecto al modelo independiente."
    ],
    [
      "The petrophysical branch minimizes the actual negative log density of a fitted two-class full-covariance Gaussian mixture. Its 640 density/susceptibility pairs are original synthetic laboratory-like samples generated independently with seed 68121. EM fits weights, means and covariances before inversion; it does not see display-case voxel labels. This explicit likelihood formulation is inspired by petrophysically guided inversion, but it does not invoke SimPEG’s PGI optimizer or dynamically update the mixture during the geological inversion.",
      "La rama petrofísica minimiza la densidad logarítmica negativa real de una mezcla gaussiana de dos clases con covarianza completa. Sus 640 pares densidad/susceptibilidad son muestras sintéticas originales tipo laboratorio con semilla independiente 68121. EM ajusta pesos, medias y covarianzas antes de invertir y no ve etiquetas de celdas del caso. Esta formulación se inspira en inversión guiada petrofísicamente; no invoca el optimizador PGI de SimPEG ni actualiza dinámicamente la mezcla."
    ],
    [
      "The shared-contact and conflicting-boundary cases test the prior in different regimes. In the latter, an independently dense body and magnetic dyke deliberately violate the coupled petrophysical relation. That output remains visible as a negative control. Mixture responsibilities express relative compatibility of the recovered property pair with each prior component; they are not observed rock types or probabilities that the inferred geology is true. A lower complete objective is not sufficient to establish improved recovery.",
      "Los casos de contacto compartido y límites conflictivos prueban regímenes distintos. En el segundo, un cuerpo denso y dique magnético separados violan deliberadamente la relación petrofísica; la salida se conserva como control negativo. Las responsabilidades expresan compatibilidad relativa del par recuperado con cada componente; no son litologías observadas ni probabilidades de geología verdadera. Reducir el objetivo no establece por sí solo mejor recuperación."
    ]
  ],
  "equations": [
    {
      "tex": "J_0=\\frac{\\|W_g(G_g\\rho-d_g)\\|^2}{N_g}+\\frac{\\|W_m(G_m\\chi-d_m)\\|^2}{N_m}+\\frac{\\beta_g}{N_g}\\rho^TQ\\rho+\\frac{\\beta_m}{N_m}\\chi^TQ\\chi",
      "caption": [
        "ρ is density contrast and χ susceptibility; Wg/Wm whiten observations; Ng/Nm count active stations; Q is physical spatial precision. Each beta is selected independently before joint optimization.",
        "ρ es contraste de densidad y χ susceptibilidad; Wg/Wm blanquean datos; Ng/Nm cuentan estaciones activas; Q es precisión espacial física. Cada beta se selecciona antes de optimización conjunta."
      ]
    },
    {
      "tex": "\\mathbf c=\\nabla(\\rho/0.5)\\times\\nabla(\\chi/0.03),\\quad J_{\\rm cross}=J_0+\\lambda\\,C/C_0,\\quad C=240^4\\operatorname{mean}(\\mathbf c^2)",
      "caption": [
        "Gradients are per metre. The mean runs over the three cross-product components and all cells. C₀ is max(C at the independent initialization, 10⁻¹²); lambda controls structural coupling, not property equality.",
        "Gradientes por metro. La media recorre tres componentes del producto cruz y todas las celdas. C₀ es max(C inicial independiente, 10⁻¹²); lambda controla estructura, no igualdad de propiedades."
      ]
    }
  ],
  "assumptions": [
    "Common flat mesh, independently noisy surveys and fixed priors. Conflicting lithologies can invalidate the structural or petrophysical hypothesis. Neither the optimized model nor its mixture membership is a geological posterior sample.",
    "Malla plana común, ruido independiente y priors fijos. Litologías conflictivas pueden invalidar hipótesis estructurales o petrofísicas. Ni el modelo optimizado ni su pertenencia son muestras posteriores geológicas."
  ],
  "algorithms": [
    {
      "id": "joint-uncoupled",
      "title": [
        "Matched uncoupled inversion",
        "Inversión desacoplada comparable"
      ],
      "explanation": [
        "Both properties are optimized under their own noise-weighted data and spatial terms, with no structural or mixture coupling. This is the baseline for interpreting whether an added multi-property prior improves recovery under the same numerical budget.",
        "Se optimizan ambas propiedades con sus términos de datos y espacio ponderados, sin acoplamiento estructural ni mezcla. Es la referencia para determinar si añadir un prior multipropiedad mejora recuperación con igual presupuesto."
      ],
      "equation": {
        "tex": "J_0=\\frac{\\|W_g(G_g\\rho-d_g)\\|^2}{N_g}+\\frac{\\|W_m(G_m\\chi-d_m)\\|^2}{N_m}+\\frac{\\beta_g}{N_g}\\rho^TQ\\rho+\\frac{\\beta_m}{N_m}\\chi^TQ\\chi",
        "caption": [
          "ρ is density contrast and χ susceptibility; Wg/Wm whiten observations; Ng/Nm count active stations; Q is physical spatial precision. Each beta is selected independently before joint optimization.",
          "ρ es contraste de densidad y χ susceptibilidad; Wg/Wm blanquean datos; Ng/Nm cuentan estaciones activas; Q es precisión espacial física. Cada beta se selecciona antes de optimización conjunta."
        ]
      },
      "steps": [
        [
          "Initialize density and susceptibility from matched independent spatial L2 solves, with the same active observations.",
          "Inicializar densidad y susceptibilidad desde L2 espaciales independientes con las mismas observaciones activas."
        ],
        [
          "Evaluate the separate whitened data means and physical spatial precisions; add only the selected coupling term.",
          "Evaluar medias de datos blanqueados y precisiones espaciales separadas; añadir sólo el acoplamiento seleccionado."
        ],
        [
          "Apply a strong-Wolfe L-BFGS update and save an independently evaluated objective/model pair.",
          "Aplicar actualización L-BFGS strong-Wolfe y guardar un par objetivo/modelo evaluado independientemente."
        ],
        [
          "Export both property models, predictions and recovery metrics; compare with the matched uncoupled output.",
          "Exportar ambas propiedades, predicciones y métricas; comparar con la salida desacoplada equivalente."
        ]
      ],
      "settings": [
        "Diagonal quadratic-Hessian preconditioning; CPU float64 L-BFGS, strong-Wolfe line search, 80 steps, history size 15, gradient tolerance 10⁻¹⁰ and change tolerance 10⁻¹². Both properties start from separate spatial L2 solves. Gravity and magnetic beta are separately selected by discrepancy. Coupling weight is 1, or 4 in the regularization condition.",
        "Precondicionamiento Hessiano cuadrático diagonal; L-BFGS CPU float64 con búsqueda strong-Wolfe, 80 pasos, memoria 15, tolerancia de gradiente 10⁻¹⁰ y cambio 10⁻¹². Ambas propiedades parten de L2 espacial independiente. Beta gravimétrica y magnética se eligen por discrepancia. Acoplamiento 1 o 4 con regularización mayor."
      ],
      "history": [
        "Complete objective after accepted optimizer updates, saved every eight steps and at the final state. Data, spatial, cross-gradient and mixture terms are exported separately; a mixture negative-log density can be negative and is not a normalized error.",
        "Objetivo completo después de actualizaciones aceptadas, guardado cada ocho pasos y al final. Se exportan términos de datos, espacial, gradiente cruzado y mezcla; la densidad logarítmica negativa puede ser negativa y no es error normalizado."
      ],
      "limitation": [
        "Independent priors cannot determine unobserved shared geology. Compare full-model, support and omitted-data errors rather than accepting a small fitted residual.",
        "Los priors independientes no determinan geología compartida no observada. Compare errores de modelo, soporte y datos omitidos en vez de aceptar un residuo ajustado pequeño."
      ]
    },
    {
      "id": "joint",
      "title": [
        "Physical cross-gradient inversion",
        "Inversión por gradiente cruzado físico"
      ],
      "explanation": [
        "A dimensionless physical cross-gradient penalty is added to the matched baseline. Density and susceptibility stay separate variables; no pointwise proportionality is imposed. The reported structural diagnostic uses physical properties, whereas the optimizer couples normalized properties.",
        "Se añade gradiente cruzado físico adimensional a la referencia equivalente. Densidad y susceptibilidad siguen separadas; no se impone proporcionalidad puntual. El diagnóstico usa propiedades físicas, mientras el objetivo acopla propiedades normalizadas."
      ],
      "equation": {
        "tex": "J_{\\rm cross}=J_0+\\lambda\\frac{240^4\\operatorname{mean}[(\\nabla(\\rho/0.5)\\times\\nabla(\\chi/0.03))^2]}{C_0}",
        "caption": [
          "J0 is the uncoupled objective; lambda is 1 or 4; physical spacings are 80, 80 and 70 m. C₀ is the scaled cross penalty at the matched independent initial model, floored at 10⁻¹². It is fixed during inversion, not tuned to the target.",
          "J0 es objetivo desacoplado; lambda vale 1 o 4; espaciamientos físicos 80, 80 y 70 m. C₀ es la penalización escalada en el inicio independiente común, con piso 10⁻¹². Se fija durante la inversión, no se ajusta al objetivo."
        ]
      },
      "steps": [
        [
          "Initialize density and susceptibility from matched independent spatial L2 solves, with the same active observations.",
          "Inicializar densidad y susceptibilidad desde L2 espaciales independientes con las mismas observaciones activas."
        ],
        [
          "Evaluate the separate whitened data means and physical spatial precisions; add only the selected coupling term.",
          "Evaluar medias de datos blanqueados y precisiones espaciales separadas; añadir sólo el acoplamiento seleccionado."
        ],
        [
          "Apply a strong-Wolfe L-BFGS update and save an independently evaluated objective/model pair.",
          "Aplicar actualización L-BFGS strong-Wolfe y guardar un par objetivo/modelo evaluado independientemente."
        ],
        [
          "Export both property models, predictions and recovery metrics; compare with the matched uncoupled output.",
          "Exportar ambas propiedades, predicciones y métricas; comparar con la salida desacoplada equivalente."
        ]
      ],
      "settings": [
        "Diagonal quadratic-Hessian preconditioning; CPU float64 L-BFGS, strong-Wolfe line search, 80 steps, history size 15, gradient tolerance 10⁻¹⁰ and change tolerance 10⁻¹². Both properties start from separate spatial L2 solves. Gravity and magnetic beta are separately selected by discrepancy. Coupling weight is 1, or 4 in the regularization condition.",
        "Precondicionamiento Hessiano cuadrático diagonal; L-BFGS CPU float64 con búsqueda strong-Wolfe, 80 pasos, memoria 15, tolerancia de gradiente 10⁻¹⁰ y cambio 10⁻¹². Ambas propiedades parten de L2 espacial independiente. Beta gravimétrica y magnética se eligen por discrepancia. Acoplamiento 1 o 4 con regularización mayor."
      ],
      "history": [
        "Complete objective after accepted optimizer updates, saved every eight steps and at the final state. Data, spatial, cross-gradient and mixture terms are exported separately; a mixture negative-log density can be negative and is not a normalized error.",
        "Objetivo completo después de actualizaciones aceptadas, guardado cada ocho pasos y al final. Se exportan términos de datos, espacial, gradiente cruzado y mezcla; la densidad logarítmica negativa puede ser negativa y no es error normalizado."
      ],
      "limitation": [
        "Parallel gradients and flat fields can both satisfy the structural term. Failure to improve independent density recovery is reported as unresolved even when the coupling term decreases.",
        "Gradientes paralelos y campos constantes satisfacen el término estructural. No mejorar la densidad independiente se informa como no resuelto aunque disminuya acoplamiento."
      ]
    },
    {
      "id": "pgi",
      "title": [
        "Gaussian-mixture petrophysical inversion",
        "Inversión petrofísica de mezcla gaussiana"
      ],
      "explanation": [
        "The prior evaluates recovered density and susceptibility in their original physical units against an independently fitted Gaussian mixture. Strong-Wolfe L-BFGS differentiates the complete mixture log likelihood together with data and spatial terms; class responsibilities are exported, not invented by the renderer.",
        "El prior evalúa densidad y susceptibilidad recuperadas en unidades físicas frente a una mezcla ajustada independientemente. L-BFGS diferencia la verosimilitud completa junto con datos y espacio; se exportan responsabilidades, no se inventan en la vista."
      ],
      "equation": {
        "tex": "J_{\\rm PGI}=J_0-\\frac{\\eta}{M}\\sum_{j=1}^M\\log\\left[\\sum_{k=1}^{2}\\pi_k\\,\\mathcal N\\!\\left((\\rho_j,\\chi_j);\\mu_k,\\Sigma_k\\right)\\right]",
        "caption": [
          "M is cell count; πk, μk and Σk are independently fitted weights, physical-property means and full covariances. Eta is mixture strength, 1 or 4. The mixture is fixed throughout inversion.",
          "M es cantidad de celdas; πk, μk y Σk son pesos, medias físicas y covarianzas completas ajustados independientemente. Eta es fuerza 1 o 4. La mezcla se fija durante la inversión."
        ]
      },
      "steps": [
        [
          "Fit the two-component full-covariance GMM to 640 independent petrophysical samples using EM.",
          "Ajustar mezcla de dos componentes y covarianza completa a 640 muestras independientes mediante EM."
        ],
        [
          "Initialize density and susceptibility from matched independent spatial L2 solves, with the same active observations.",
          "Inicializar densidad y susceptibilidad desde L2 espaciales independientes con las mismas observaciones activas."
        ],
        [
          "Evaluate the separate whitened data means and physical spatial precisions; add only the selected coupling term.",
          "Evaluar medias de datos blanqueados y precisiones espaciales separadas; añadir sólo el acoplamiento seleccionado."
        ],
        [
          "Minimize the complete objective and export physical-property estimates, prior parameters and normalized responsibilities.",
          "Minimizar objetivo completo y exportar propiedades, parámetros del prior y responsabilidades normalizadas."
        ]
      ],
      "settings": [
        "Diagonal quadratic-Hessian preconditioning; CPU float64 L-BFGS, strong-Wolfe line search, 80 steps, history size 15, gradient tolerance 10⁻¹⁰ and change tolerance 10⁻¹². Both properties start from separate spatial L2 solves. Gravity and magnetic beta are separately selected by discrepancy. Coupling weight is 1, or 4 in the regularization condition.",
        "Precondicionamiento Hessiano cuadrático diagonal; L-BFGS CPU float64 con búsqueda strong-Wolfe, 80 pasos, memoria 15, tolerancia de gradiente 10⁻¹⁰ y cambio 10⁻¹². Ambas propiedades parten de L2 espacial independiente. Beta gravimétrica y magnética se eligen por discrepancia. Acoplamiento 1 o 4 con regularización mayor."
      ],
      "history": [
        "Complete objective after accepted optimizer updates, saved every eight steps and at the final state. Data, spatial, cross-gradient and mixture terms are exported separately; a mixture negative-log density can be negative and is not a normalized error.",
        "Objetivo completo después de actualizaciones aceptadas, guardado cada ocho pasos y al final. Se exportan términos de datos, espacial, gradiente cruzado y mezcla; la densidad logarítmica negativa puede ser negativa y no es error normalizado."
      ],
      "limitation": [
        "Original synthetic sample pairs are not field rock measurements. A misspecified mixture can bias both properties; the conflicting case is a deliberate negative control. This is not SimPEG’s PGI optimization implementation.",
        "Los pares sintéticos originales no son mediciones de rocas de campo. Una mezcla incorrecta sesga ambas propiedades; el caso conflictivo es control negativo. No es la implementación del optimizador PGI de SimPEG."
      ]
    }
  ]
},
  {
    id: "cnn",
    title: T("Inverse CNN", "CNN inversa"),
    refs: ["cockett2015", "adam"],
    paragraphs: [
      T(
        "The convolutional inverse predicts depth-integrated density from a 16 × 16 gravity map. Its target is a 24 × 28 horizontal array, not a volume. Summing density contrast times cell thickness removes the explicit depth axis, although the forward gravity response still depends on depth. The learned mapping therefore estimates one projection of the subsurface within a training distribution. It cannot establish where in depth a predicted column anomaly is located.",
        "La red convolucional predice densidad integrada en profundidad desde un mapa gravimétrico de 16 × 16. Su objetivo es un arreglo horizontal de 24 × 28, no un volumen. Sumar contraste de densidad por espesor elimina el eje de profundidad del objetivo, aunque la gravedad todavía depende de él. La red estima una proyección dentro de su distribución de entrenamiento; no establece a qué profundidad se sitúa la anomalía de una columna.",
      ),
      T(
        "Training realizations contain ellipsoids, inclined bodies, basins and faulted layers with randomized position, size and contrast. Complete geological realizations are assigned to training, validation or test before network fitting. The split sizes are 800, 160 and 160, generated from independent seeds. The oblique intrusion and ring dyke displayed in the workbench are outside those generator families. They test geometric transfer, while a survey-height change tests acquisition shift without retraining the network.",
        "Las realizaciones contienen elipsoides, cuerpos inclinados, cuencas y capas falladas con posición, tamaño y contraste aleatorios. Se asignan realizaciones completas a entrenamiento, validación o prueba antes del ajuste. Las particiones tienen 800, 160 y 160 modelos con semillas independientes. La intrusión oblicua y el dique anular del visor quedan fuera de esas familias. Prueban transferencia geométrica; cambiar altura prueba cambio de adquisición sin reentrenar.",
      ),
      T(
        "The input scale is the standard deviation of clean training observations only. Gaussian noise of 2% of that scale is added before normalization to all three splits. The target is divided by a fixed 400 g/cm³ m scale. Using test statistics for normalization would leak information; this implementation does not do so. The output is restored to physical units before calculating column RMSE. Missing stations are linearly interpolated, with nearest-neighbor edge fill, because the trained network requires a complete input raster.",
        "La escala de entrada es la desviación estándar de observaciones limpias de entrenamiento. Se agrega ruido gaussiano del 2% de esa escala a las tres particiones antes de normalizar. El objetivo se divide por 400 g/cm³ m. Usar estadísticas de prueba filtraría información; aquí no ocurre. La salida vuelve a unidades físicas antes de calcular RMSE de columna. Las estaciones ausentes se interpolan linealmente con relleno de borde por vecino cercano, porque la red requiere una imagen completa.",
      ),
      T(
        "The validation set selects the lowest-MSE checkpoint. The held-out test evaluates that checkpoint and a noise-aware spatial L2 comparator on exactly identical noisy observations, then projects the classical estimate onto the same 24 × 28 column target. Input hashes and per-realization errors make that comparison inspectable. Neither a lower average nor a sharper map establishes field transfer; withheld oblique and ring cases retain their individual failures.",
        "Validación selecciona el checkpoint de menor MSE. Prueba evalúa ese checkpoint y un comparador espacial L2 con idénticas observaciones ruidosas, proyectando el modelo clásico al mismo objetivo de columnas 24 × 28. Se exportan hashes de entradas y errores por realización. Un promedio menor o imagen más definida no demuestra transferencia de campo; los casos oblicuo y anular omitidos conservan sus fallos individuales.",
      ),
    ],
    equations: [
      E(
        String.raw`c_{yx}=\sum_{z=1}^{16}\Delta\rho_{zyx}\,70\ \mathrm m,\qquad x=d/s_d,\qquad y=c/400`,
        "c is column density contrast in g/cm³ m; 70 m is cell thickness; sd is training-observation standard deviation; x and y are normalized input and target. The 400 scale has the same units as c.",
        "c es contraste de densidad integrada en g/cm³ m; 70 m es espesor de celda; sd es desviación de datos de entrenamiento; x e y son entrada y objetivo normalizados. La escala 400 tiene las unidades de c.",
      ),
      E(
        String.raw`\theta_* = \arg\min_{\theta\ \mathrm{among\ saved\ epochs}}\operatorname{MSE}_{val}(f_\theta(x),y),\qquad \widehat c=400f_{\theta_*}(x)`,
        "θ denotes network weights. Validation MSE selects an epoch; it is not optimized on test cases. The final prediction ĉ is rescaled to physical column-density units.",
        "θ representa pesos. MSE de validación selecciona época, sin optimizar casos de prueba. La predicción ĉ se reescala a unidades físicas de densidad integrada.",
      ),
    ],
    assumptions: T(
      "Fixed 16 × 16 survey geometry and a restricted synthetic generator. No terrain, regional trend or heterogeneous measurement errors are learned. The network is not a full 3D inverse, and its output is not a calibrated uncertainty estimate.",
      "Geometría fija de 16 × 16 y generador sintético restringido. No se aprenden terreno, tendencia regional ni errores heterogéneos. La red no es un inversor 3D completo y no estima incertidumbre calibrada.",
    ),
    algorithms: [
      {
        id: "cnn",
        title: T(
          "CNN training and inference",
          "Entrenamiento e inferencia CNN",
        ),
        explanation: T(
          "Two spatial convolutions extract features; adaptive pooling reduces them to a fixed representation; dense layers predict the column target. This is a locally trained gravity network, not a reproduction of a published seismic InversionNet checkpoint.",
          "Dos convoluciones extraen rasgos espaciales; pooling adaptativo los reduce a una representación fija; capas densas predicen columnas. Es una red gravimétrica local, no una reproducción de un checkpoint sísmico InversionNet.",
        ),
        equation: E(
          String.raw`1\!\times\!16\!\times\!16\xrightarrow{3\times3}16\!\times\!16\!\times\!16\xrightarrow{3\times3}24\!\times\!16\!\times\!16\xrightarrow{pool}384\xrightarrow{dense}96\xrightarrow{dense}672`,
          "Convolutions have padding one and GELU activation. Adaptive average pooling produces 24 × 4 × 4 = 384 features; the 96-unit dense layer uses GELU; the linear output reshapes to 24 × 28.",
          "Convoluciones con padding uno y GELU. Pooling promedio adaptativo produce 24 × 4 × 4 = 384 rasgos; la capa de 96 usa GELU; la salida lineal se organiza en 24 × 28.",
        ),
        steps: [
          T(
            "Generate disjoint geological realizations and compute their SimPEG gravity responses.",
            "Generar realizaciones disjuntas y respuestas gravimétricas SimPEG.",
          ),
          T(
            "Fit the input scale on training observations only; normalize inputs and column targets.",
            "Calcular escala sólo en entrenamiento; normalizar entradas y columnas.",
          ),
          T(
            "Train by minibatch MSE; evaluate validation MSE each epoch and retain the best weights.",
            "Entrenar con MSE por minibatch; evaluar validación cada época y guardar mejores pesos.",
          ),
          T(
            "Reload exported weights and compare predictions against held-out columns and the physical baseline.",
            "Recargar pesos exportados y comparar columnas independientes con referencia física.",
          ),
        ],
        settings: T(
          "Adam learning rate 0.001, batch size 64, 180 epochs. Model seed 7721; realization seeds 18001 / 29001 / 39001; noise seed 5001. Outputs are linear, with no positivity constraint.",
          "Tasa Adam 0,001, lotes de 64, 180 épocas. Semilla de red 7721; realizaciones 18001 / 29001 / 39001; ruido 5001. Salidas lineales sin positividad.",
        ),
        history: T(
          "Validation MSE sampled at epochs 0, 5, …, 175. The training ledger’s train field is the last minibatch loss of that epoch, not the epoch mean.",
          "MSE de validación en épocas 0, 5, …, 175. El campo train del registro corresponde al último minibatch, no a la media de la época.",
        ),
        limitation: T(
          "No browser retraining or live CNN inference is performed; the workbench displays computed predictions. Higher output pixel count does not supply missing depth information.",
          "No se reentrena ni ejecuta CNN en vivo en el navegador; se muestran predicciones calculadas. Más píxeles de salida no aportan información de profundidad ausente.",
        ),
      },
    ],
  },
  {
    id: "ae",
    title: T("Observation autoencoder", "Autoencoder de observaciones"),
    refs: ["adam"],
    paragraphs: [
      T(
        "The autoencoder reconstructs the normalized gravity observation map after compression through a twelve-dimensional latent vector. Its task differs from the inverse CNN: the target is the observation itself, not density or geology. A large reconstruction error can indicate that an input is poorly represented by the learned observation manifold. It can also result from noise, changed acquisition or interpolation. A small error does not imply that a geological model is familiar or that an inverse prediction is accurate.",
        "El autoencoder reconstruye el mapa gravimétrico normalizado tras comprimirlo a doce variables latentes. A diferencia de la CNN inversa, el objetivo es la propia observación, no densidad ni geología. Un error alto puede indicar una entrada mal representada por la variedad aprendida, pero también ruido, adquisición distinta o interpolación. Un error bajo no implica geología conocida ni una inversión precisa.",
      ),
      T(
        "Training uses the same realization-disjoint observation splits as the CNN, but no property target. A fully connected encoder maps 256 station values to 64 hidden features and then 12 latent features; a decoder maps back through 64 to 256 values. The network is deterministic at inference. There is no probabilistic latent distribution, variational objective, geological class label or ensemble. The exported squared-error map localizes observation mismatch, not the probability of a subsurface anomaly.",
        "Se usan las mismas particiones disjuntas de observaciones, pero sin objetivo de propiedades. El codificador conecta 256 estaciones con 64 rasgos y después 12 latentes; el decodificador retorna por 64 a 256. La inferencia es determinista. No hay distribución latente probabilística, objetivo variacional, clases geológicas ni ensamble. El mapa de error cuadrado localiza desajuste de observaciones, no probabilidad de anomalía subterránea.",
      ),
      T(
        "The novelty threshold is the 99th percentile of errors on a separate 160-realization calibration set, seed 49001, not the checkpoint-selection validation set. The frozen threshold is tested against 160 independent generator-distribution examples and 80 withheld-family realizations, seed 59001. Sensitivity, specificity, misses, false alarms and pairwise ROC AUC are recorded. These measurements are specific to the generator and noise law, not calibrated probabilities of geological correctness.",
        "El umbral es el percentil 99 de errores en 160 realizaciones de calibración separadas, semilla 49001, no de validación de pesos. Se prueba con 160 ejemplos independientes del generador y 80 realizaciones de familias omitidas, semilla 59001. Se registran sensibilidad, especificidad, fallos, falsas alarmas y ROC AUC. Son medidas específicas del generador y ruido, no probabilidades calibradas de corrección geológica.",
      ),
      T(
        "The workbench reports both the case score and threshold. The comparison is a testable detector decision, not an assurance of reliability. Under missing coverage the network input is interpolated, whereas the displayed error compares the reconstructed map against all recorded stations, including omitted ones. This distinction matters when attributing a high score to novelty rather than preprocessing. Results should be read alongside input coverage, observation noise and the inverse CNN’s separate column error.",
        "El visor informa puntaje y umbral. La comparación es una decisión verificable del detector, no una garantía. Con cobertura incompleta, la entrada se interpola, mientras el error mostrado compara reconstrucción con todas las estaciones registradas, incluidas las omitidas. Esto importa para distinguir novedad de efectos del preprocesamiento. Los resultados deben leerse junto a cobertura, ruido y error independiente de columna de la CNN.",
      ),
    ],
    equations: [
      E(
        String.raw`\widehat x=D_\theta(E_\theta(x)),\qquad J_{AE}=\frac1{256}\sum_{i=1}^{256}(\widehat x_i-x_i)^2`,
        "x is the normalized station map; E and D are encoder and decoder; θ denotes weights. The loss averages normalized squared observation error over stations.",
        "x es el mapa normalizado; E y D son codificador y decodificador; θ son pesos. La pérdida promedia error cuadrático normalizado entre estaciones.",
      ),
      E(
        String.raw`\tau=Q_{0.99}\{J_{AE}(x):x\in calibration\},\qquad flag(x)=\mathbf1[J_{AE}(x)>\tau]`,
        "τ is the empirical independent-calibration threshold; Q is a sample quantile; flag is a binary threshold decision. It is not a posterior probability or a geological classification.",
        "τ es el umbral empírico de calibración independiente; Q un cuantil muestral; flag una decisión binaria. No es probabilidad posterior ni clasificación geológica.",
      ),
    ],
    assumptions: T(
      "Observation reconstruction is only a candidate novelty signal. Unfamiliar geometries may produce familiar gravity maps and remain below threshold. The independent 80-realization withheld-family test measures detection under its generator only; misses must be retained.",
      "Reconstruir observaciones es sólo una señal candidata de novedad. Geometrías desconocidas pueden generar mapas familiares y quedar bajo el umbral. La prueba de 80 realizaciones omitidas mide detección sólo bajo su generador; se conservan todos los fallos.",
    ),
    algorithms: [
      {
        id: "autoencoder",
        title: T("Autoencoder and threshold", "Autoencoder y umbral"),
        explanation: T(
          "Training minimizes reconstruction MSE on normalized noisy observations. The best validation checkpoint is frozen before computing test errors or the two geometric-transfer examples.",
          "El entrenamiento minimiza MSE de reconstrucción en observaciones ruidosas normalizadas. Se fija el mejor checkpoint de validación antes de calcular prueba o ejemplos de transferencia.",
        ),
        equation: E(
          String.raw`256\xrightarrow{GELU}64\xrightarrow{GELU}12\xrightarrow{GELU}64\xrightarrow{linear}256`,
          "Fully connected layers compress and reconstruct the flattened 16 × 16 input. GELU follows each hidden layer; the output is linear. No inverse physical model is evaluated by this network.",
          "Capas densas comprimen y reconstruyen la entrada 16 × 16 aplanada. GELU sigue cada capa oculta y la salida es lineal. Esta red no evalúa un modelo físico inverso.",
        ),
        steps: [
          T(
            "Use the training-only input normalization and the same disjoint realization splits.",
            "Usar normalización de entrenamiento y las mismas particiones disjuntas.",
          ),
          T(
            "Train the 256→64→12→64→256 network to reconstruct its input.",
            "Entrenar la red 256→64→12→64→256 para reconstruir su entrada.",
          ),
          T(
            "Select the minimum-validation-MSE checkpoint; compute the 0.99 error quantile on a separate 160-realization calibration set.",
            "Seleccionar mínimo MSE de validación; calcular cuantil de error 0,99 en 160 realizaciones separadas de calibración.",
          ),
          T(
            "Compute test and case reconstruction errors; compare scores with the frozen threshold.",
            "Calcular errores de prueba y casos; compararlos con el umbral fijo.",
          ),
        ],
        settings: T(
          "Adam 0.001, batch size 64, 180 epochs. Same 800 / 160 / 160 split and input scale as CNN. Each exported checkpoint is reloaded and its numerical predictions checked.",
          "Adam 0,001, lotes 64, 180 épocas. Mismas particiones 800 / 160 / 160 y escala de entrada que CNN. Se recarga cada checkpoint y se verifican sus predicciones.",
        ),
        history: T(
          "Validation reconstruction MSE every five epochs. It is a training record, not an inverse iteration trajectory for the currently selected case.",
          "MSE de reconstrucción de validación cada cinco épocas. Es historial de entrenamiento, no trayectoria inversa del caso seleccionado.",
        ),
        limitation: T(
          "A threshold miss must be reported as a miss. Reconstructed observations and a low error score do not validate a geological interpretation.",
          "No superar el umbral en un caso desconocido debe informarse como fallo de detección. Reconstruir observaciones con error bajo no valida interpretación geológica.",
        ),
      },
    ],
  },
];

export function algorithmFor(id: string) {
  return chapters.flatMap((c) => c.algorithms).find((a) => a.id === id);
}
