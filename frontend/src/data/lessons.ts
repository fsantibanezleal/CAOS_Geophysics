type Lesson = {
  question: [string, string];
  read: [string, string];
  try: [string, string];
  limit: [string, string];
};
const L = (
  question: Lesson["question"],
  read: Lesson["read"],
  experiment: Lesson["try"],
  limit: Lesson["limit"],
): Lesson => ({ question, read, try: experiment, limit });
export const lessons: Record<string, Lesson> = {
  GRAVITY_INTRUSION: L(
    [
      "Can a surface survey recover the depth of an offset intrusion?",
      "¿Puede un levantamiento superficial recuperar la profundidad de una intrusión desplazada?",
    ],
    [
      "The stock has a narrow neck and a displaced deep chamber. Gravity integrates both; a broad anomaly does not uniquely locate the chamber.",
      "El cuerpo tiene un cuello estrecho y una cámara profunda desplazada. La gravedad integra ambos; una anomalía amplia no localiza la cámara de forma única.",
    ],
    [
      "Compare compact IRLS with L2, then raise the survey. Inspect the recovered section, not only the data fit.",
      "Compare IRLS compacto con L2 y eleve el levantamiento. Inspeccione la sección recuperada, no sólo el ajuste.",
    ],
    [
      "Density and depth trade off. A small residual does not establish a unique body.",
      "Densidad y profundidad se compensan. Un residuo pequeño no establece un cuerpo único.",
    ],
  ),
  GRAVITY_DEEP_BODY: L(
    ["Where does the basin end?", "¿Dónde termina la cuenca?"],
    [
      "An asymmetric low-density sedimentary basin thickens away from its edge. The steep flank contains more short-wavelength information than the broad centre.",
      "Una cuenca sedimentaria asimétrica de baja densidad se engrosa desde su borde. El flanco abrupto contiene más información de onda corta que el centro.",
    ],
    [
      "Remove half the stations and follow the basin edge in the recovered section.",
      "Retire la mitad de las estaciones y siga el borde en la sección recuperada.",
    ],
    [
      "The mesh truncates geology; no external regional field is estimated.",
      "La malla trunca la geología; no se estima un campo regional externo.",
    ],
  ),
  GRAVITY_NOISY: L(
    [
      "Can opposite density contrasts cancel each other?",
      "¿Pueden cancelarse contrastes de densidad opuestos?",
    ],
    [
      "A positive body and a negative body produce overlapping fields. A weak observation may reflect cancellation rather than absent geology.",
      "Un cuerpo positivo y otro negativo producen campos superpuestos. Una observación débil puede reflejar cancelación, no ausencia de geología.",
    ],
    [
      "Compare the signed model and field; add noise and check which lobe survives.",
      "Compare el modelo y campo con signo; agregue ruido y observe qué lóbulo sobrevive.",
    ],
    [
      "Regularization can merge or suppress bodies even when the observations fit.",
      "La regularización puede unir o suprimir cuerpos aun cuando las observaciones ajustan.",
    ],
  ),
  GRAVITY_TILTED: L(
    [
      "Can gravity distinguish dip from fault throw?",
      "¿Puede la gravedad distinguir buzamiento y salto de falla?",
    ],
    [
      "A dipping density layer is displaced across a fault. Its surface response blends both structures.",
      "Una capa inclinada de densidad está desplazada por una falla. La respuesta superficial combina ambas estructuras.",
    ],
    [
      "Move the northing section across the fault and compare L2 with IRLS.",
      "Desplace la sección norte-sur a través de la falla y compare L2 con IRLS.",
    ],
    [
      "A cell-wise inverse model is not a fitted geological fault surface.",
      "Un modelo inverso por celdas no es una superficie de falla geológica ajustada.",
    ],
  ),
  MAGNETIC_DYKE: L(
    [
      "How many dykes can the survey resolve?",
      "¿Cuántos diques puede resolver el levantamiento?",
    ],
    [
      "Three inclined narrow dykes interfere in total magnetic intensity. The field extrema need not lie above the bodies.",
      "Tres diques estrechos inclinados interfieren en intensidad magnética total. Los extremos no necesariamente están sobre los cuerpos.",
    ],
    [
      "Raise the survey and reduce coverage. Compare signed TMI with the 3D susceptibility.",
      "Eleve el levantamiento y reduzca cobertura. Compare TMI con signo y susceptibilidad 3D.",
    ],
    [
      "Linearized TMI assumes the anomalous field is small relative to the inducing field.",
      "TMI linealizado supone un campo anómalo pequeño respecto del inductor.",
    ],
  ),
  MAGNETIC_REMANENCE: L(
    [
      "What if magnetization does not follow the present field?",
      "¿Qué ocurre si la magnetización no sigue el campo actual?",
    ],
    [
      "The tabular body has a prescribed remanent direction. The scalar induced model is deliberately mismatched; vector inversion permits three components.",
      "El cuerpo tabular tiene una dirección remanente prescrita. El modelo escalar inducido es deliberadamente incompatible; la inversión vectorial permite tres componentes.",
    ],
    [
      "Compare scalar and vector data residuals before trusting either geometry.",
      "Compare residuos de datos escalares y vectoriales antes de confiar en la geometría.",
    ],
    [
      "Vector inversion adds degrees of freedom; a better fit is not proof of the recovered magnetization direction.",
      "La inversión vectorial agrega grados de libertad; un mejor ajuste no prueba la dirección recuperada.",
    ],
  ),
  MAGNETIC_DEEP: L(
    [
      "What is lost when a magnetic lens is deep?",
      "¿Qué se pierde cuando una lente magnética es profunda?",
    ],
    [
      "Depth attenuates short spatial wavelengths. The deep magnetite lens produces a broad, shifted anomaly.",
      "La profundidad atenúa longitudes de onda espaciales cortas. La lente profunda de magnetita produce una anomalía amplia desplazada.",
    ],
    [
      "Compare the true lens with the recovered vertical smearing and then raise the survey.",
      "Compare la lente real con el alargamiento vertical recuperado y eleve el levantamiento.",
    ],
    [
      "The independently calibrated depth prior changes the depth preference; it does not restore missing information.",
      "El prior de profundidad calibrado independientemente y derivadas físicas regulariza el problema; no recupera información ausente.",
    ],
  ),
  MAGNETIC_NOISY: L(
    [
      "Can crossing dykes be separated in noisy TMI?",
      "¿Pueden separarse diques cruzados en TMI ruidoso?",
    ],
    [
      "Two intersecting dyke systems produce a non-separable response. High gradients accentuate both structure and noise.",
      "Dos sistemas de diques cruzados producen una respuesta no separable. Los gradientes altos acentúan estructura y ruido.",
    ],
    [
      "Increase regularization and inspect what disappears in the model and remains in the residual.",
      "Aumente la regularización e inspeccione lo que desaparece del modelo y permanece en el residuo.",
    ],
    [
      "The synthetic noise is independent Gaussian noise, not realistic cultural contamination.",
      "El ruido sintético es gaussiano independiente, no contaminación cultural realista.",
    ],
  ),
  MT_RESISTIVE: L(
    [
      "Which frequencies see through a resistive cover?",
      "¿Qué frecuencias atraviesan una cobertura resistiva?",
    ],
    [
      "Low frequencies sample a larger depth range. Apparent resistivity is a response, not the true resistivity at a single depth.",
      "Las frecuencias bajas muestrean mayor profundidad. La resistividad aparente es una respuesta, no la resistividad real a una profundidad única.",
    ],
    [
      "Extend the low-frequency band and compare the three inversion parameterizations.",
      "Extienda la banda de baja frecuencia y compare las tres parametrizaciones inversas.",
    ],
    [
      "Layer thicknesses are known in this experiment; only resistivities are inverted.",
      "Los espesores son conocidos en este experimento; sólo se invierten resistividades.",
    ],
  ),
  MT_CONDUCTIVE: L(
    [
      "Can a thin conductive aquifer be identified?",
      "¿Puede identificarse un acuífero conductor delgado?",
    ],
    [
      "A buried conductive layer bends apparent resistivity and phase across the transition band. Its conductance can be better constrained than its individual thickness or resistivity.",
      "Una capa conductora enterrada modifica resistividad aparente y fase en la banda de transición. Su conductancia puede estar mejor restringida que espesor o resistividad.",
    ],
    [
      "Remove alternating frequencies and compare the recovered conductor with the full-band solution.",
      "Retire frecuencias alternas y compare el conductor recuperado con la solución de banda completa.",
    ],
    [
      "This isotropic 1D response omits lateral structure, static shift and galvanic distortion.",
      "Esta respuesta 1D isotrópica omite estructura lateral, desplazamiento estático y distorsión galvánica.",
    ],
  ),
  MT_MIXED: L(
    [
      "Can alternating crustal layers remain distinct?",
      "¿Pueden distinguirse capas corticales alternadas?",
    ],
    [
      "Several conductivity contrasts overlap in frequency. A good impedance fit may conceal substantial layer-wise error.",
      "Varios contrastes de conductividad se superponen en frecuencia. Un buen ajuste de impedancia puede ocultar errores por capa.",
    ],
    [
      "Compare fitted phase with the true and recovered resistivity columns, especially under strong smoothing.",
      "Compare fase ajustada y columnas real y recuperada, especialmente con suavizado fuerte.",
    ],
    [
      "The neural parameterization is optimized per sounding; it is not a pretrained universal inverse.",
      "La parametrización neuronal se optimiza por sondeo; no es un inversor universal preentrenado.",
    ],
  ),
  MT_NOISY: L(
    [
      "Is the deep conductor constrained by this bandwidth?",
      "¿Está restringido el conductor profundo por esta banda?",
    ],
    [
      "The low-frequency end carries the deepest sensitivity. Added noise and missing frequencies change the inferred basement.",
      "El extremo de baja frecuencia tiene la mayor sensibilidad profunda. Ruido y frecuencias faltantes cambian el basamento inferido.",
    ],
    [
      "Compare noise, coverage and extended-band experiments; look for instability rather than only fit.",
      "Compare ruido, cobertura y banda extendida; busque inestabilidad, no sólo ajuste.",
    ],
    [
      "No posterior credible intervals are computed. Variation across experiments is not a probability distribution.",
      "No se calculan intervalos posteriores. La variación entre experimentos no es una distribución de probabilidad.",
    ],
  ),
  FWI_LAYERED: L(
    [
      "Which arrivals carry information about each interface?",
      "¿Qué arribos aportan información sobre cada interfaz?",
    ],
    [
      "A finite-difference acoustic wave crosses three layers. Reflections and moveout emerge in the receiver gather.",
      "Una onda acústica de diferencias finitas cruza tres capas. Las reflexiones y el moveout aparecen en los receptores.",
    ],
    [
      "Pause the wavefield when the front crosses an interface; compare arrival times across receivers.",
      "Pause el campo cuando el frente cruce una interfaz; compare tiempos de arribo entre receptores.",
    ],
    [
      "Constant-density 2D acoustics: no elastic modes, attenuation or free-surface multiples.",
      "Acústica 2D de densidad constante: sin modos elásticos, atenuación ni múltiples de superficie libre.",
    ],
  ),
  FWI_FAULT: L(
    [
      "Can waveform inversion recover a displaced reflector?",
      "¿Puede la inversión de onda recuperar un reflector desplazado?",
    ],
    [
      "A normal fault offsets a velocity interface. Diffraction near the discontinuity differs from a flat-layer reflection.",
      "Una falla normal desplaza una interfaz de velocidad. La difracción cerca de la discontinuidad difiere de una reflexión plana.",
    ],
    [
      "Compare left, middle and right shots; inspect the reconstructed displacement and the residual gathers.",
      "Compare disparos izquierdo, central y derecho; inspeccione desplazamiento reconstruido y residuos.",
    ],
    [
      "Three shots and a small mesh provide limited illumination; this is not a field-scale survey.",
      "Tres disparos y una malla pequeña ofrecen iluminación limitada; no es un levantamiento de escala de campo.",
    ],
  ),
  FWI_CYCLE_SKIP: L(
    [
      "Does low-frequency continuation improve this salt inversion?",
      "¿Mejora la continuación de baja frecuencia esta inversión salina?",
    ],
    [
      "A high-velocity salt dome refracts the wavefront. A smooth starting model can predict arrivals more than half a cycle away.",
      "Un domo salino rápido refracta el frente. Un modelo inicial suave puede predecir arribos alejados más de medio ciclo.",
    ],
    [
      "Compare direct and multiscale full-waveform losses. A lower loss alone does not certify the salt boundary.",
      "Compare pérdidas directas y multiescala. Una pérdida menor no certifica el límite salino.",
    ],
    [
      "Moving-average continuation is a time-domain low-pass schedule, not an exhaustive frequency-domain strategy.",
      "La continuación por promedio móvil es un filtrado temporal, no una estrategia frecuencial exhaustiva.",
    ],
  ),
  FWI_NOISY: L(
    [
      "Can a low-velocity gas channel survive noisy inversion?",
      "¿Puede recuperarse un canal lento de gas con ruido?",
    ],
    [
      "A curved shallow channel delays and scatters energy. Its response competes with stronger deeper reflectors.",
      "Un canal curvo somero retrasa y dispersa energía. Compite con reflectores profundos más fuertes.",
    ],
    [
      "Compare true velocity, recovered velocity and error under reduced receiver coverage.",
      "Compare velocidad real, recuperada y error con menor cobertura de receptores.",
    ],
    [
      "The source wavelet is assumed known; source estimation and acquisition errors are not included.",
      "La ondícula se considera conocida; no se incluyen estimación de fuente ni errores de adquisición.",
    ],
  ),
  JOINT_SHARED: L(
    [
      "When does structural coupling help?",
      "¿Cuándo ayuda el acoplamiento estructural?",
    ],
    [
      "Density and susceptibility share an inclined lithological boundary. A cross-gradient penalty encourages parallel gradients, not equal property values.",
      "Densidad y susceptibilidad comparten un límite inclinado. La penalización de gradiente cruzado fomenta gradientes paralelos, no propiedades iguales.",
    ],
    [
      "Compare gravity-only and coupled results, then increase coupling and inspect both data fits.",
      "Compare resultados gravimétricos y conjuntos; aumente acoplamiento e inspeccione ambos ajustes.",
    ],
    [
      "Shared structure is a hypothesis. Cross-gradient reduction does not demonstrate geological correctness.",
      "La estructura compartida es una hipótesis. Reducir gradiente cruzado no demuestra corrección geológica.",
    ],
  ),
  JOINT_CONFLICT: L(
    [
      "What happens when shared structure is the wrong assumption?",
      "¿Qué ocurre si la estructura compartida es una hipótesis incorrecta?",
    ],
    [
      "The dense body and magnetic body are deliberately separated. Structural coupling can impose features unsupported by one data type.",
      "El cuerpo denso y el magnético están separados deliberadamente. El acoplamiento puede imponer rasgos no sustentados por uno de los datos.",
    ],
    [
      "Increase coupling and compare density error, magnetic fit and cross-gradient together.",
      "Aumente acoplamiento y compare error de densidad, ajuste magnético y gradiente cruzado.",
    ],
    [
      "A visually coherent joint model can be more biased than independent reconstructions.",
      "Un modelo conjunto visualmente coherente puede tener más sesgo que reconstrucciones independientes.",
    ],
  ),
  LEARNED_CNN: L(
    [
      "Will a learned prior generalize to an oblique intrusion?",
      "¿Generaliza un prior aprendido a una intrusión oblicua?",
    ],
    [
      "The CNN predicts depth-integrated density from a gravity map. The oblique geometry is withheld from training, exposing prior bias.",
      "La CNN predice densidad integrada desde un mapa gravimétrico. La geometría oblicua no aparece en entrenamiento, exponiendo sesgo del prior.",
    ],
    [
      "Compare the prediction with the true column density and the physical L2 baseline; change survey height.",
      "Compare predicción, densidad integrada real y referencia L2; cambie altura del levantamiento.",
    ],
    [
      "The network does not recover 3D depth. Its training distribution and fixed survey geometry limit transfer.",
      "La red no recupera profundidad 3D. Su distribución de entrenamiento y geometría fija limitan transferencia.",
    ],
  ),
  LEARNED_AUTOENCODER: L(
    [
      "Does reconstruction error reveal unfamiliar geology?",
      "¿Revela el error de reconstrucción una geología desconocida?",
    ],
    [
      "A ring dyke is excluded from training. The autoencoder maps observations through a 12-dimensional bottleneck and highlights reconstruction errors.",
      "Un dique anular queda fuera del entrenamiento. El autoencoder usa un cuello de 12 dimensiones y destaca errores de reconstrucción.",
    ],
    [
      "Compare the error against a validation-set threshold and test whether added noise alone triggers it.",
      "Compare error y umbral de validación; evalúe si sólo agregar ruido lo supera.",
    ],
    [
      "An anomaly score is not a probability of geological novelty and may respond to acquisition shift.",
      "Un puntaje anómalo no es probabilidad de novedad geológica y puede responder a cambios de adquisición.",
    ],
  ),
};
