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
      T(
        "Sensitivity scaling changes the model coordinates before inversion, reducing the strong preference for shallow cells. L2 then penalizes the size of those scaled coefficients. IRLS repeatedly changes the diagonal penalty so that small coefficients are penalized more strongly than large ones. Neither implementation contains a spatial-gradient smoothness term or positivity constraint. Their differences therefore reflect the chosen coefficient penalty, not a test of every smooth or sparse inversion method. Density errors use g/cm³; scalar magnetic errors use dimensionless SI susceptibility.",
        "La escala por sensibilidad cambia las coordenadas del modelo antes de invertir y reduce la preferencia por celdas someras. L2 penaliza el tamaño de esos coeficientes escalados. IRLS modifica repetidamente la penalización diagonal para penalizar más los coeficientes pequeños. Ninguna implementación incluye suavidad por gradiente espacial ni positividad. Las diferencias reflejan esa penalización particular, no una comparación de todos los métodos suaves o dispersos. Los errores de densidad usan g/cm³; los magnéticos escalares, susceptibilidad SI adimensional.",
      ),
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
        id: "l2",
        title: T("Sensitivity-scaled L2", "L2 escalada por sensibilidad"),
        explanation: T(
          "The inverse is solved in data space, where the matrix has one row per active receiver. This is an exact quadratic minimizer for the stated transformed objective, not a call to SimPEG’s inversion directives. Noise standard deviations normalize the reported WRMS but do not enter this linear solve.",
          "La inversión se resuelve en el espacio de datos, con una fila por receptor activo. Es el minimizador cuadrático del objetivo transformado indicado, no una llamada a las directivas de inversión de SimPEG. La desviación de ruido normaliza WRMS, pero no entra en esta solución lineal.",
        ),
        equation: E(
          String.raw`\begin{aligned}s_j&=\|G_{:j}\|_2,&W_{jj}&=\frac1{\max(s_j,0.06\max s)}\\a&=\|GW\|_F/\sqrt N,&A&=GW/a,\quad b=d/a\\q&=A^T(AA^T+\beta I)^{-1}b,&m&=Wq\end{aligned}`,
          "N is the active station count; s is column sensitivity; W rescales model coefficients; a normalizes the operator; β is the coefficient penalty. This minimizes ‖Aq−b‖² + β‖q‖². The matrix inverse denotes a linear solve, not explicit inversion.",
          "N es el número de estaciones activas; s es sensibilidad por columna; W escala coeficientes; a normaliza el operador; β penaliza su tamaño. Se minimiza ‖Aq−b‖² + β‖q‖². La inversa matricial representa una solución lineal, no inversión explícita.",
        ),
        steps: [
          T(
            "Select active rows of G and the observed vector; retain all rows for the final prediction map.",
            "Seleccionar filas activas de G y observaciones; conservar todas las filas para el mapa de predicción.",
          ),
          T(
            "Compute column norms, apply the 6% sensitivity floor and construct A and b.",
            "Calcular normas de columna, aplicar el piso del 6% y construir A y b.",
          ),
          T(
            "Solve the positive-definite data-space system with SciPy; recover m = Wq.",
            "Resolver el sistema definido positivo con SciPy; recuperar m = Wq.",
          ),
          T(
            "Predict Gm, export observed − predicted residuals and evaluate property error against the known model.",
            "Predecir Gm, exportar observación − predicción y evaluar error de propiedad contra el modelo conocido.",
          ),
        ],
        settings: T(
          "One linear solve. β = 0.018, or 0.25 in the stronger-regularization condition. Receiver height 60 m, or 180 m in the acquisition condition. No discrepancy-principle stopping or β search is performed.",
          "Una solución lineal. β = 0,018 o 0,25 con regularización mayor. Altura de receptores 60 m o 180 m en adquisición modificada. No hay parada por discrepancia ni búsqueda de β.",
        ),
        history: T(
          "One value: mean squared noise-normalized residual over active receivers. It omits the model penalty and is not an optimization trajectory.",
          "Un valor: media del residuo normalizado al cuadrado sobre receptores activos. Excluye la penalización del modelo y no es una trayectoria iterativa.",
        ),
        limitation: T(
          "A low WRMS can accompany a large density error. Canonical cases do not whiten residuals by sigma; the separate CSV-ingestion path explicitly weights rows before calling this solver.",
          "Un WRMS bajo puede acompañar un error de densidad alto. Los casos canónicos no blanquean residuos por sigma; la ruta separada de ingesta CSV pondera filas antes de llamar al solver.",
        ),
      },
      {
        id: "irls",
        title: T("Sparse IRLS", "IRLS dispersa"),
        explanation: T(
          "IRLS replaces one nonlinear sparsity penalty by a sequence of diagonal quadratic penalties. The initial weights are one, so the first solution equals L2. Subsequent weights are functions of the previous scaled coefficients q, not physical density or its spatial gradient.",
          "IRLS aproxima una penalización no lineal de dispersión mediante penalizaciones cuadráticas diagonales. Los pesos iniciales son uno, por lo que el primer resultado coincide con L2. Los siguientes pesos dependen de los coeficientes escalados q, no de la densidad física ni de su gradiente.",
        ),
        equation: E(
          String.raw`\begin{aligned}C_k&=\operatorname{diag}(1/w^{(k)}),\quad q_k=C_kA^T(AC_kA^T+\beta I)^{-1}b\\\epsilon_k&=\max(0.12\|q_k\|_\infty,10^{-10})\\\widetilde w_j&=(q_{k,j}^2+\epsilon_k^2)^{-1/2},\quad w_j^{(k+1)}=\widetilde w_j/\operatorname{median}(\widetilde w)\end{aligned}`,
          "A, b and β use the L2 scaling. C is inverse penalty weight; ε prevents singular weights near zero; k indexes the eight solves. The quadratic subproblem penalizes Σⱼwⱼqⱼ².",
          "A, b y β usan la escala L2. C es peso inverso; ε evita pesos singulares cerca de cero; k recorre ocho soluciones. El subproblema penaliza Σⱼwⱼqⱼ².",
        ),
        steps: [
          T(
            "Initialize all diagonal weights to one.",
            "Inicializar pesos diagonales en uno.",
          ),
          T(
            "Solve the data-space quadratic system for the current inverse weights.",
            "Resolver el sistema cuadrático con los pesos inversos actuales.",
          ),
          T(
            "Save the model and normalized data error; recompute ε and median-normalized weights.",
            "Guardar modelo y error de datos normalizado; recalcular ε y pesos normalizados por su mediana.",
          ),
          T(
            "Repeat for eight solves and return the last model, without selecting by known-truth error.",
            "Repetir ocho soluciones y devolver la última, sin seleccionar por error contra la verdad.",
          ),
        ],
        settings: T(
          "Eight solves, sensitivity floor 6%, ε factor 0.12, numerical floor 10⁻¹⁰. β stays fixed throughout. The changing ε and median normalization mean the trace is not monotone minimization of one fixed penalty.",
          "Ocho soluciones, piso de sensibilidad 6%, factor de ε 0,12 y piso numérico 10⁻¹⁰. β permanece fijo. Cambiar ε y normalizar por mediana significa que la trayectoria no minimiza monótonamente una penalización fija.",
        ),
        history: T(
          "Eight active-station mean squared normalized data residuals. These do not include the changing sparsity penalty.",
          "Ocho medias de residuos de datos normalizados al cuadrado en estaciones activas. No incluyen la penalización de dispersión variable.",
        ),
        limitation: T(
          "Compact support is a prior preference, not evidence that a recovered body has sharp geological boundaries. Eight updates are a fixed compute budget, not a convergence certificate.",
          "El soporte compacto es una preferencia del prior, no evidencia de límites geológicos abruptos. Ocho actualizaciones son un presupuesto fijo, no un certificado de convergencia.",
        ),
      },
      {
        id: "vector",
        title: T("Vector magnetization", "Magnetización vectorial"),
        explanation: T(
          "The vector solve replaces each scalar susceptibility with three effective susceptibility components. The same sensitivity-scaled L2 algebra is applied to the concatenated operator. The remanent case generates observations using a direction proportional to (0.80, −0.55, 0.23), rather than the inducing-field direction.",
          "La solución vectorial sustituye cada susceptibilidad escalar por tres componentes efectivas. Se aplica la misma solución L2 escalada a un operador concatenado. El caso remanente genera observaciones con dirección proporcional a (0,80; −0,55; 0,23), no con la dirección inductora.",
        ),
        equation: E(
          String.raw`d=\begin{bmatrix}G_x&G_y&G_z\end{bmatrix}\begin{bmatrix}m_x\\m_y\\m_z\end{bmatrix},\qquad m_{amp,j}=\sqrt{m_{x,j}^2+m_{y,j}^2+m_{z,j}^2}`,
          "Gₓ, Gᵧ, G𝓏 map the effective susceptibility components to TMI (nT). The displayed amplitude is dimensionless effective susceptibility, not magnetization in A/m. Component blocks are concatenated before solving.",
          "Gₓ, Gᵧ y G𝓏 transforman componentes de susceptibilidad efectiva a TMI (nT). La amplitud mostrada es susceptibilidad efectiva adimensional, no magnetización en A/m. Los bloques se concatenan antes de resolver.",
        ),
        steps: [
          T(
            "Build the three-component SimPEG prism operator at the same stations.",
            "Construir el operador prismático vectorial de SimPEG en las mismas estaciones.",
          ),
          T(
            "Apply the active-station mask and solve with the L2 sensitivity transformation.",
            "Aplicar la máscara de estaciones y resolver con la transformación L2.",
          ),
          T(
            "Separate component blocks and compute the magnitude per cell for display.",
            "Separar componentes y calcular la magnitud por celda para visualizar.",
          ),
          T(
            "Evaluate the full vector forward response; do not predict TMI from the magnitude alone.",
            "Evaluar la respuesta vectorial completa; no predecir TMI usando sólo la magnitud.",
          ),
        ],
        settings: T(
          "32,256 components; 256 observations, or 128 with reduced coverage. Same β and inducing field as scalar inversion. No direction or positivity bounds.",
          "32.256 componentes; 256 observaciones o 128 con cobertura reducida. Mismos β y campo inductor que la inversión escalar. Sin cotas de dirección ni positividad.",
        ),
        history: T(
          "One data-error value. No vector-model iteration frames are exported.",
          "Un valor de error de datos. No se exportan cuadros iterativos vectoriales.",
        ),
        limitation: T(
          "The larger parameter space can reduce residuals without identifying the correct direction. The benchmark exports no directional accuracy metric; scalar and vector model errors must not be treated as equivalent.",
          "El espacio de parámetros mayor puede reducir residuos sin identificar la dirección correcta. No se exporta una métrica de precisión direccional; los errores de modelo escalar y vectorial no son equivalentes.",
        ),
      },
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
        "All three inversions fit real and imaginary impedance, not apparent resistivity and phase independently. They differ in parameterization, optimization and relative regularization scaling. Bounded least squares uses sums of real residual components; the differentiable solvers use means of complex squared residuals and means of layer differences. The same numeric β therefore does not impose the same relative smoothing. The neural method optimizes a small network separately for each sounding; it is neither a pretrained inverse nor an independent PDE-residual PINN.",
        "Las tres inversiones ajustan partes real e imaginaria de impedancia, no resistividad aparente y fase independientemente. Difieren en parametrización, optimización y escala relativa de regularización. Mínimos cuadrados acotados usa sumas de componentes reales; los diferenciables usan medias del residuo complejo cuadrado y diferencias entre capas. Un mismo β numérico no impone igual suavizado relativo. La red pequeña se optimiza por sondeo: no es un inversor preentrenado ni una PINN con residuo diferencial independiente.",
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
        id: "mt-lm",
        title: T("Bounded TRF least squares", "Mínimos cuadrados TRF acotados"),
        explanation: T(
          "The optimization variable is x = ln ρ. A real residual vector concatenates real impedance error, imaginary impedance error and first differences of x. SciPy uses its trust-region reflective algorithm with a finite-difference Jacobian. The legacy data identifier contains “lm”, but the implemented optimizer is TRF, not Levenberg–Marquardt.",
          "La variable es x = ln ρ. Un vector real concatena errores real e imaginario de impedancia y primeras diferencias de x. SciPy usa región de confianza reflectiva con jacobiano por diferencias finitas. El identificador histórico contiene «lm», pero el optimizador es TRF, no Levenberg–Marquardt.",
        ),
        equation: E(
          String.raw`r(x)=\begin{bmatrix}\Re((Z(e^x)-Z_{obs})/\sigma)\\\Im((Z(e^x)-Z_{obs})/\sigma)\\\sqrt\beta Dx\end{bmatrix},\quad \min_{0\leq x\leq\ln6000}\tfrac12\|r(x)\|^2`,
          "Z uses active frequencies; σ is the component noise standard deviation; D takes adjacent layer differences. Resistivity is bounded to 1–6,000 Ω m. The regularizer acts on natural log resistivity.",
          "Z usa frecuencias activas; σ es desviación de ruido por componente; D diferencia capas adyacentes. Resistividad acotada a 1–6.000 Ω m. El regularizador actúa sobre logaritmo natural de resistividad.",
        ),
        steps: [
          T(
            "Initialize every layer at 100 Ω m and evaluate the upward impedance recursion.",
            "Inicializar cada capa en 100 Ω m y evaluar la recursión ascendente.",
          ),
          T(
            "Construct the real residual and estimate its Jacobian using two-point finite differences.",
            "Construir el residuo real y estimar su jacobiano por diferencias de dos puntos.",
          ),
          T(
            "Solve a bounded trust-region subproblem; accept or reject the candidate according to actual reduction.",
            "Resolver un subproblema acotado de región de confianza; aceptar o rechazar según reducción real.",
          ),
          T(
            "Return SciPy’s final parameter vector; predict all frequencies, including omitted ones.",
            "Devolver el vector final de SciPy; predecir todas las frecuencias, incluidas las omitidas.",
          ),
        ],
        settings: T(
          "max_nfev = 160; SciPy 1.15.2 defaults ftol = xtol = gtol = 10⁻⁸. β = 0.001 or 0.3. There are 36 log-spaced frequencies from 0.01 to 100 Hz; reduced coverage retains 18.",
          "max_nfev = 160; tolerancias predeterminadas de SciPy 1.15.2: ftol = xtol = gtol = 10⁻⁸. β = 0,001 o 0,3. Hay 36 frecuencias logarítmicas de 0,01 a 100 Hz; cobertura reducida retiene 18.",
        ),
        history: T(
          "Mean squared concatenated residual at saved function evaluations, including finite-difference probes. The index is not a count of accepted optimizer iterations.",
          "Media cuadrática del residuo concatenado en evaluaciones guardadas, incluidas perturbaciones del jacobiano. El índice no cuenta iteraciones aceptadas.",
        ),
        limitation: T(
          "Stopping at a tolerance or evaluation limit establishes neither a global minimum nor unique layer resistivities. Thickness uncertainty is excluded.",
          "Parar por tolerancia o límite de evaluaciones no establece mínimo global ni resistividades únicas. Se excluye incertidumbre de espesores.",
        ),
      },
      {
        id: "mt-adam",
        title: T("Differentiable impedance", "Impedancia diferenciable"),
        explanation: T(
          "Complex PyTorch operations differentiate the same recursion with respect to log resistivity. Adam updates the layer parameters directly. This avoids a finite-difference Jacobian but does not alter the electromagnetic assumptions or remove non-uniqueness.",
          "Las operaciones complejas de PyTorch diferencian la misma recursión respecto a log resistividad. Adam actualiza directamente los parámetros por capa. Esto evita el jacobiano por diferencias finitas, pero no cambia los supuestos electromagnéticos ni elimina la no unicidad.",
        ),
        equation: E(
          String.raw`J(x)=\frac1{N_f}\sum_{i\in\mathcal A}\left|\frac{Z_i(e^x)-Z_i^{obs}}{\sigma_i}\right|^2+\frac\beta{n-1}\sum_{j=1}^{n-1}(x_{j+1}-x_j)^2`,
          "𝒜 is the active frequency set with Nf entries; n is layer count; x is ln ρ. Means, rather than sums, define this objective. The gradient is taken through complex arithmetic to real x.",
          "𝒜 es el conjunto activo con Nf frecuencias; n es el número de capas; x es ln ρ. Este objetivo usa medias, no sumas. El gradiente atraviesa aritmética compleja hasta x real.",
        ),
        steps: [
          T(
            "Initialize x = ln 100 in float64 on the available compute device.",
            "Inicializar x = ln 100 en float64 sobre el dispositivo disponible.",
          ),
          T(
            "Evaluate complex impedance and the mean-normalized objective.",
            "Evaluar impedancia compleja y objetivo normalizado por medias.",
          ),
          T(
            "Backpropagate the objective and apply an Adam update to x.",
            "Retropropagar el objetivo y aplicar una actualización Adam a x.",
          ),
          T(
            "Run 250 updates; retain the model associated with the smallest recorded loss.",
            "Ejecutar 250 actualizaciones; conservar el modelo asociado a la menor pérdida registrada.",
          ),
        ],
        settings: T(
          "Adam learning rate 0.06; 250 updates; β = 0.001 or 0.3; initial 100 Ω m. Exponentiation enforces positivity but no upper resistivity bound is applied.",
          "Tasa Adam 0,06; 250 actualizaciones; β = 0,001 o 0,3; inicio 100 Ω m. Exponenciar asegura positividad, pero no impone cota superior.",
        ),
        history: T(
          "Objective sampled every 10 updates. In this direct-parameter implementation saved parameter snapshots are copied after the update; recorded loss was evaluated before it.",
          "Objetivo muestreado cada 10 actualizaciones. En esta parametrización directa, los parámetros se copian después de actualizar; la pérdida se evaluó antes.",
        ),
        limitation: T(
          "This comparison also changes constraints and relative penalty scaling versus TRF. It cannot isolate optimizer performance alone.",
          "La comparación cambia también restricciones y escala relativa de penalización respecto a TRF. No aísla únicamente el rendimiento del optimizador.",
        ),
      },
      {
        id: "mt-neural",
        title: T(
          "Per-sounding neural inversion",
          "Inversión neuronal por sondeo",
        ),
        explanation: T(
          "A small network maps normalized layer index to log resistivity. Its weights, rather than independent layer values, are optimized through the impedance recursion. This is a low-dimensional coupling of the layer values: the network is fitted anew for every sounding and never sees a target resistivity profile.",
          "Una red pequeña transforma el índice normalizado de capa en log resistividad. Sus pesos, no valores independientes por capa, se optimizan a través de la recursión. La red acopla las resistividades y se ajusta nuevamente para cada sondeo, sin usar un perfil objetivo de resistividad.",
        ),
        equation: E(
          String.raw`u_j=\frac{j-1}{n-1},\quad x_j=1+7\,\operatorname{sigmoid}(f_\theta(u_j)),\quad \min_\theta J(x(\theta))`,
          "uⱼ is normalized layer index, not physical depth; fθ is a 1→24→24→1 tanh network. xⱼ = ln ρⱼ is bounded between 1 and 8, so resistivity lies between e and e⁸ Ω m. J is the differentiable-impedance objective.",
          "uⱼ es índice normalizado, no profundidad física; fθ es una red tanh 1→24→24→1. xⱼ = ln ρⱼ queda entre 1 y 8, por lo que ρ queda entre e y e⁸ Ω m. J es el objetivo de impedancia diferenciable.",
        ),
        steps: [
          T(
            "Initialize network weights with the case seed and create normalized layer-index inputs.",
            "Inicializar pesos con la semilla del caso y entradas de índice normalizado.",
          ),
          T(
            "Map outputs through the bounded log-resistivity transform.",
            "Transformar salidas a log resistividad acotada.",
          ),
          T(
            "Evaluate impedance and differentiate the loss through both recursion and network.",
            "Evaluar impedancia y diferenciar la pérdida a través de recursión y red.",
          ),
          T(
            "Apply 420 Adam updates and select the lowest evaluated-loss resistivity profile.",
            "Aplicar 420 actualizaciones Adam y seleccionar el perfil con menor pérdida evaluada.",
          ),
        ],
        settings: T(
          "Float64; tanh hidden activations; Adam learning rate 0.025; 420 updates. β = 0.001 or 0.3. The forward operator is analytical layered impedance, not a learned emulator.",
          "Float64; activaciones ocultas tanh; tasa Adam 0,025; 420 actualizaciones. β = 0,001 o 0,3. El operador directo es impedancia estratificada analítica, no un emulador aprendido.",
        ),
        history: T(
          "Pre-update objective and network-produced resistivities sampled every 10 steps. The stored final profile is the best evaluated profile, not necessarily the last saved frame.",
          "Objetivo y resistividades producidas por la red antes de actualizar, cada 10 pasos. El perfil final es el mejor evaluado, no necesariamente el último cuadro.",
        ),
        limitation: T(
          "No pretrained transfer, learned uncertainty or layer-thickness estimation is provided. Index-based coupling is a parameterization choice, not a geological law.",
          "No hay transferencia preentrenada, incertidumbre aprendida ni estimación de espesores. Acoplar por índice es una elección de parametrización, no una ley geológica.",
        ),
      },
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
        "Deepwave evaluates a finite-difference acoustic propagator on 128 × 96 nodes at 12.5 m spacing. Three sources at 75 m depth illuminate the layered, faulted, salt and gas-channel models. Forty receivers, or twenty under reduced coverage, lie at the same depth. The record lasts 1.1 s at a computational time step of 0.5 ms. Exported receiver traces are sampled every 4 ms; wavefield images every 24 ms. Those display samples are not the internal time integration step.",
        "Deepwave evalúa un propagador acústico de diferencias finitas en 128 × 96 nodos separados 12,5 m. Tres fuentes a 75 m iluminan modelos estratificado, fallado, salino y de canal de gas. Cuarenta receptores, o veinte con cobertura reducida, están a igual profundidad. El registro dura 1,1 s con paso de cálculo de 0,5 ms. Las trazas se exportan cada 4 ms y campos cada 24 ms. El muestreo visual no es el paso de integración.",
      ),
      T(
        "Automatic differentiation computes the derivative of the discrete receiver loss with respect to velocity parameters. Its adjoint interpretation is to propagate data residual information backward and combine it with the forward wavefield. A directional finite-difference test checks that this gradient agrees with perturbations of the implemented simulator. This test verifies a derivative, not a correct recovered geology. Limited illumination and the oscillatory waveform objective can leave the model far from truth despite substantial loss reduction.",
        "La diferenciación automática calcula la derivada de la pérdida discreta respecto a parámetros de velocidad. Su interpretación adjunta propaga información del residuo hacia atrás y la combina con el campo directo. Una prueba direccional por diferencias finitas verifica acuerdo con perturbaciones del simulador. Verifica la derivada, no la geología recuperada. La iluminación limitada y el objetivo oscilatorio pueden dejar un modelo lejos de la verdad pese a reducir mucho la pérdida.",
      ),
      T(
        "Cycle skipping occurs when predicted and observed events are so misaligned that a local update matches the wrong oscillation. The continuation variant first compares moving-average-filtered traces, then reduces the averaging window. This is a specific time-domain continuation strategy, not a complete frequency-domain inversion. It uses the same initial depth trend as direct FWI, rather than a smoothed true model. Both methods receive 28 updates, so their final states are finite-budget reconstructions, not claimed converged global solutions.",
        "El salto de ciclo aparece cuando eventos predichos y observados están tan desalineados que una actualización local ajusta otra oscilación. La variante de continuación compara primero trazas promediadas y reduce luego la ventana. Es una estrategia temporal específica, no una inversión completa en frecuencia. Usa la misma tendencia inicial con profundidad que FWI directa, no la verdad suavizada. Ambas reciben 28 actualizaciones: son reconstrucciones con presupuesto finito, no soluciones globales convergidas.",
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
        id: "fwi-l2",
        title: T("Direct waveform L2", "L2 de onda directa"),
        explanation: T(
          "The objective compares all shot, receiver and time samples after normalizing by observed mean-square amplitude. A velocity-difference penalty discourages roughness. Deepwave supplies the discrete propagation gradient; Adam updates the bounded velocity parameter.",
          "El objetivo compara todos los disparos, receptores y tiempos, normalizado por amplitud cuadrática media observada. Una penalización de diferencias de velocidad desalienta rugosidad. Deepwave aporta el gradiente de propagación y Adam actualiza el parámetro acotado.",
        ),
        equation: E(
          String.raw`J_w(v)=\frac{\operatorname{mean}[(L_wF(v)-L_wd)^2]}{\operatorname{mean}(d^2)}+\frac{4\beta}{10^6}\left[\operatorname{mean}[(D_xv)^2]+\operatorname{mean}[(D_zv)^2]\right]`,
          "F maps velocity to receiver traces; d is observed pressure amplitude; Lw is a moving average of width w samples; Dₓ and D𝓏 are adjacent cell differences. The factor 4 preserves the derivative scale when cell spacing is halved.",
          "F transforma velocidad en trazas; d es amplitud observada; Lw es promedio móvil de w muestras; Dₓ y D𝓏 son diferencias de celdas adyacentes. El factor 4 conserva la escala de derivadas al reducir a la mitad el espaciamiento.",
        ),
        steps: [
          T(
            "Initialize v = 1,800 + 11 iz m/s, with iz the depth-node index; transform to the unconstrained parameter.",
            "Inicializar v = 1.800 + 11 iz m/s, con iz índice vertical; transformar al parámetro no acotado.",
          ),
          T(
            "Propagate all three shots; compute waveform and regularization terms.",
            "Propagar tres disparos; calcular términos de onda y regularización.",
          ),
          T(
            "Differentiate, clip the parameter-gradient norm to 10, and take one Adam update.",
            "Diferenciar, limitar norma del gradiente a 10 y aplicar Adam.",
          ),
          T(
            "After 28 updates, return the evaluated model with the lowest unfiltered relative waveform MSE.",
            "Tras 28 actualizaciones, devolver el modelo evaluado con menor MSE relativo de onda sin filtrar.",
          ),
        ],
        settings: T(
          "Adam rate 0.045; β = 0.002 or 0.06; w = 1. Fourth-order spatial differences, 24-cell PML (300 m), dt = 0.5 ms, 2,200 steps. Ricker source 8 Hz, 9 Hz for salt, or 5 Hz in the acquisition variant.",
          "Tasa Adam 0,045; β = 0,002 o 0,06; w = 1. Diferencias espaciales de cuarto orden, PML de 24 celdas (300 m), dt = 0,5 ms, 2.200 pasos. Ricker de 8 Hz, 9 Hz en sal o 5 Hz en adquisición modificada.",
        ),
        history: T(
          "Unfiltered relative waveform MSE at each pre-update model. It excludes the roughness penalty. Velocity frames are saved every two updates; the selected final model need not equal the last frame.",
          "MSE relativo de onda sin filtrar en cada modelo previo a actualizar. Excluye rugosidad. Se guardan velocidades cada dos actualizaciones; el modelo final seleccionado puede diferir del último cuadro.",
        ),
        limitation: T(
          "The best data fit can retain incorrect velocity and interfaces. Neither monotonic loss nor 28 updates certify convergence, and source estimation is not included.",
          "El mejor ajuste puede mantener velocidad e interfaces incorrectas. Ni pérdida monótona ni 28 pasos certifican convergencia; no se estima la fuente.",
        ),
      },
      {
        id: "fwi-multiscale",
        title: T(
          "Moving-average continuation",
          "Continuación por promedio móvil",
        ),
        explanation: T(
          "This variant uses the same wave propagator, parameterization and optimizer as direct FWI. Only the temporal averaging operator in the fitted data term changes with iteration. The filter reduces rapid oscillations but is not an ideal low-pass filter and does not add missing low-frequency observations.",
          "Esta variante usa el mismo propagador, parametrización y optimizador que FWI directa. Sólo cambia el promedio temporal en el término ajustado. El filtro reduce oscilaciones rápidas, pero no es un filtro ideal ni agrega observaciones de baja frecuencia ausentes.",
        ),
        equation: E(
          String.raw`(L_wd)_t=\frac1w\sum_{k=-(w-1)/2}^{(w-1)/2}d_{t+k},\qquad w(i)=\begin{cases}41&0\leq i<9\\17&9\leq i<18\\1&18\leq i<28\end{cases}`,
          "i is zero-based optimizer step, t time index and w window width in internal 0.5 ms samples. Trace ends use replicated boundary samples. The first two windows span 20 ms and 8 ms between their endpoints.",
          "i es paso de optimización desde cero, t índice temporal y w ancho en muestras internas de 0,5 ms. Los extremos replican muestras de borde. Las dos primeras ventanas abarcan 20 ms y 8 ms entre extremos.",
        ),
        steps: [
          T(
            "Apply the same averaging filter to predictions and observations.",
            "Aplicar el mismo promedio a predicciones y observaciones.",
          ),
          T(
            "Optimize the filtered loss for steps 0–8, then reduce the window for steps 9–17.",
            "Optimizar pérdida filtrada en pasos 0–8; reducir ventana en 9–17.",
          ),
          T(
            "Use unfiltered traces for the final ten updates.",
            "Usar trazas sin filtrar en las diez actualizaciones finales.",
          ),
          T(
            "Select the final model using unfiltered data error across all evaluated steps.",
            "Seleccionar el modelo final por error sin filtrar entre todos los pasos evaluados.",
          ),
        ],
        settings: T(
          "28 updates with widths 41 → 17 → 1; all other constants match direct FWI. The source wavelet itself is unchanged during this schedule.",
          "28 actualizaciones con anchos 41 → 17 → 1; las demás constantes coinciden con FWI directa. La ondícula no cambia durante esta secuencia.",
        ),
        history: T(
          "The plotted curve is always unfiltered relative MSE. Changes at filter transitions are not changes of the plotted metric, although the optimized objective changes.",
          "La curva muestra siempre MSE relativo sin filtrar. En las transiciones cambia el objetivo optimizado, no la definición de la métrica graficada.",
        ),
        limitation: T(
          "Averaging is a limited continuation strategy. Salt-boundary errors can persist even if the final waveform error is lower than direct FWI.",
          "El promedio es una estrategia de continuación limitada. Pueden persistir errores del límite salino aunque el error de onda sea menor que en FWI directa.",
        ),
      },
    ],
  },
  {
    id: "joint",
    title: T("Joint inversion", "Inversión conjunta"),
    refs: ["crossgradient", "adam"],
    paragraphs: [
      T(
        "Joint inversion combines gravity and magnetic observations while retaining separate density and susceptibility models. These properties can share lithological boundaries without being proportional in value. A cross-gradient penalty encodes that structural hypothesis: it is small where the two property gradients are parallel, antiparallel, or one gradient vanishes. It therefore cannot distinguish matching boundaries from locally constant models on its own. Independent data-fit terms are necessary to prevent a structurally simple but unsupported reconstruction.",
        "La inversión conjunta combina gravedad y magnetismo conservando modelos separados de densidad y susceptibilidad. Pueden compartir límites litológicos sin valores proporcionales. El gradiente cruzado representa esa hipótesis: es pequeño si los gradientes son paralelos, antiparalelos o alguno se anula. Por sí solo no distingue límites coincidentes de modelos localmente constantes. Los ajustes independientes son necesarios para evitar una reconstrucción simple pero no sustentada.",
      ),
      T(
        "Density is normalized by 0.5 g/cm³ and susceptibility by 0.03 SI before coupling. Without such scales, changing the units would change the relative strength of the structural term. The implementation takes finite differences in cell-index coordinates, not derivatives divided by physical metres. Coupling weights are consequently tied to this discretization and cannot be transferred unchanged to a differently spaced mesh as physical constants. The displayed cross-gradient magnitude is also not a geological probability.",
        "La densidad se normaliza por 0,5 g/cm³ y la susceptibilidad por 0,03 SI antes de acoplar. Sin escalas, cambiar unidades alteraría la fuerza relativa del término estructural. Se calculan diferencias en índices de celda, no derivadas divididas por metros. Los pesos de acoplamiento dependen de esta discretización y no pueden transferirse como constantes físicas a otra malla. La magnitud mostrada tampoco es probabilidad geológica.",
      ),
      T(
        "The shared-contact case assigns density and susceptibility to the same inclined unit. The conflicting case separates a dense body from a magnetic dyke. These are complementary tests of the structural assumption: the latter can reveal information being imposed by coupling rather than supported by both surveys. Compare each property’s data residual with density error and the structural penalty. A decrease in cross-gradient is expected when coupling is strengthened, but it is not itself evidence of a more accurate earth model.",
        "El caso compartido asigna densidad y susceptibilidad a la misma unidad inclinada. El caso conflictivo separa un cuerpo denso de un dique magnético. Son pruebas complementarias: el segundo puede revelar información impuesta por el acoplamiento y no sustentada por ambos levantamientos. Compare residuos de ambas propiedades con error de densidad y penalización estructural. Reducir gradiente cruzado al reforzar acoplamiento no demuestra por sí solo mayor precisión geológica.",
      ),
      T(
        "The initial density comes from the scalar L2 solve; susceptibility is initialized by a separate magnetic L2 solve. Adam then updates both normalized fields together for a fixed budget. There is no petrophysical Gaussian-mixture model, rock-type classification or equality constraint between density and susceptibility. Those would define different joint inversion methods. The output contains both recovered properties and predictions, allowing the two data fits to be checked separately rather than combined into a single quality score.",
        "La densidad inicial proviene de L2 escalar y la susceptibilidad de una inversión magnética independiente. Adam actualiza ambos campos normalizados durante un presupuesto fijo. No hay mezcla gaussiana petrofísica, clasificación de litologías ni igualdad entre densidad y susceptibilidad: serían otros métodos conjuntos. La salida contiene ambas propiedades y predicciones, permitiendo verificar los ajustes por separado y no como un único puntaje de calidad.",
      ),
    ],
    equations: [
      E(
        String.raw`a=\Delta\rho/0.5,\qquad b=\chi/0.03,\qquad \mathbf c=\nabla_i a\times\nabla_i b`,
        "a and b are normalized density and susceptibility; ∇ᵢ differentiates in cell-index coordinates; c is their cross-gradient. Density uses g/cm³ and susceptibility SI.",
        "a y b son densidad y susceptibilidad normalizadas; ∇ᵢ diferencia por índice de celda; c es su gradiente cruzado. Densidad en g/cm³ y susceptibilidad SI.",
      ),
      E(
        String.raw`\|\mathbf c\|^2=\|\nabla_i a\|^2\|\nabla_i b\|^2-(\nabla_i a\cdot\nabla_i b)^2`,
        "The coupling vanishes for parallel or antiparallel gradients and also when either gradient is zero. It constrains orientation, not equality of property values.",
        "El acoplamiento se anula para gradientes paralelos o antiparalelos y cuando alguno vale cero. Restringe orientación, no igualdad de propiedades.",
      ),
    ],
    assumptions: T(
      "Shared boundaries are an explicit hypothesis, not a universal relation between density and magnetism. Synthetic independent noise and a common rectangular mesh are assumed. No posterior uncertainty or petrophysically guided inversion is implemented.",
      "Los límites compartidos son una hipótesis, no una relación universal entre densidad y magnetismo. Se supone ruido sintético independiente y una malla rectangular común. No se implementan incertidumbre posterior ni inversión guiada petrofísicamente.",
    ),
    algorithms: [
      {
        id: "joint",
        title: T(
          "Cross-gradient optimization",
          "Optimización de gradiente cruzado",
        ),
        explanation: T(
          "Two noise-normalized data terms, a cross-gradient term and a smallness penalty form one differentiable objective. Active-station masks are applied to both surveys before optimization. Final WRMS values are evaluated over all stations, so under reduced coverage they also contain held-out locations.",
          "Dos términos normalizados por ruido, gradiente cruzado y penalización de tamaño forman un objetivo diferenciable. La máscara se aplica a ambos levantamientos antes de optimizar. Los WRMS finales usan todas las estaciones y, con cobertura reducida, incluyen posiciones excluidas del ajuste.",
        ),
        equation: E(
          String.raw`J(a,b)=\left\langle\left(\frac{0.5G_ga-d_g}{\sigma_g}\right)^2\right\rangle+\left\langle\left(\frac{0.03G_mb-d_m}{\sigma_m}\right)^2\right\rangle+\lambda\langle c_k^2\rangle+0.015(\langle a^2\rangle+\langle b^2\rangle)`,
          "Gg and Gm are gravity and magnetic operators; d and σ are observations and component noise; angle brackets are arithmetic means. The cross term averages squared components over all cells and three directions.",
          "Gg y Gm son operadores de gravedad y magnetismo; d y σ son observaciones y ruido; los corchetes indican medias. El término cruzado promedia componentes cuadrados sobre celdas y tres direcciones.",
        ),
        steps: [
          T(
            "Initialize density from the selected L2 result and susceptibility with β = 0.04 magnetic L2.",
            "Inicializar densidad con L2 del caso y susceptibilidad con L2 magnética de β = 0,04.",
          ),
          T(
            "Normalize property fields and compute central interior / one-sided boundary differences.",
            "Normalizar propiedades y calcular diferencias centrales interiores y unilaterales en bordes.",
          ),
          T(
            "Backpropagate the complete objective and update both fields with Adam.",
            "Retropropagar el objetivo completo y actualizar ambos campos con Adam.",
          ),
          T(
            "Return the final fields after 180 updates and evaluate separate gravity and magnetic predictions.",
            "Devolver campos finales tras 180 actualizaciones y evaluar predicciones de gravedad y magnetismo.",
          ),
        ],
        settings: T(
          "Adam rate 0.008; 180 updates; λ = 4 or 25; smallness coefficient 0.015. There is no automatic coupling-weight selection or early stopping.",
          "Tasa Adam 0,008; 180 actualizaciones; λ = 4 o 25; coeficiente de tamaño 0,015. Sin selección automática de acoplamiento ni parada temprana.",
        ),
        history: T(
          "Total objective every six updates. Recorded objective is pre-update; density frames are post-update. The final structural metric is mean vector magnitude, not the squared-component penalty used for fitting.",
          "Objetivo total cada seis actualizaciones. Pérdida previa a actualizar y cuadros posteriores. La métrica estructural final es media de magnitudes vectoriales, no la penalización de componentes cuadrados del ajuste.",
        ),
        limitation: T(
          "A wrong shared-structure prior can bias either property. Lower total loss does not imply lower density error, and the cross-gradient scale depends on the mesh.",
          "Un prior estructural incorrecto puede sesgar cualquiera de las propiedades. Menor pérdida no implica menor error de densidad; la escala del gradiente cruzado depende de la malla.",
        ),
      },
    ],
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
        "The validation set selects the checkpoint with lowest mean squared target error. The held-out test set evaluates that selected checkpoint once; it does not choose epochs. A classical projection baseline is also reported, but its present evaluation uses clean observations while the CNN test uses noisy input, and its regularization is fixed rather than tuned. Consequently the table is not a noise-matched ranking or a state-of-the-art claim. Comparing one visually sharper image cannot establish transfer to field geology.",
        "Validación selecciona el checkpoint de menor error cuadrático. La prueba independiente evalúa ese checkpoint sin seleccionar épocas. También se informa una proyección clásica, pero usa observaciones limpias mientras la CNN recibe ruido, y su regularización es fija, no calibrada. Por ello, la tabla no es una comparación con ruido igualado ni un resultado de estado del arte. Una imagen más definida tampoco establece transferencia a geología de campo.",
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
        "The anomaly threshold is the 99th percentile of mean reconstruction error on validation realizations. This defines an empirical threshold for that generator and noise distribution only. It is not a 99% confidence interval, and it does not guarantee a 1% false-positive rate on another survey. The threshold is fixed before the separate test set and the withheld geometries are evaluated. Sensitivity to unfamiliar geology must be assessed against those cases, including failures to exceed the threshold.",
        "El umbral es el percentil 99 del error medio de reconstrucción en validación. Es un umbral empírico para ese generador y ruido, no un intervalo de confianza del 99% ni garantía de 1% de falsos positivos en otro levantamiento. Se fija antes de evaluar prueba y geometrías excluidas. La sensibilidad a geología desconocida debe evaluarse con esos casos, incluyendo cuando no superan el umbral.",
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
        String.raw`\tau=Q_{0.99}\{J_{AE}(x):x\in validation\},\qquad flag(x)=\mathbf1[J_{AE}(x)>\tau]`,
        "τ is the empirical validation threshold; Q is a sample quantile; flag is a binary threshold decision. It is not a posterior probability or a geological classification.",
        "τ es el umbral empírico de validación; Q un cuantil muestral; flag una decisión binaria. No es probabilidad posterior ni clasificación geológica.",
      ),
    ],
    assumptions: T(
      "Observation reconstruction is only a candidate novelty signal. Unfamiliar geometries may produce familiar gravity maps and remain below threshold. No calibrated geological detection rate can be inferred from two withheld examples.",
      "Reconstruir observaciones es sólo una señal candidata de novedad. Geometrías desconocidas pueden generar mapas familiares y quedar bajo el umbral. Dos ejemplos excluidos no permiten inferir una tasa geológica calibrada de detección.",
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
            "Select the minimum-validation-MSE checkpoint and calculate validation error quantile 0.99.",
            "Seleccionar mínimo MSE de validación y calcular cuantil 0,99 de sus errores.",
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
