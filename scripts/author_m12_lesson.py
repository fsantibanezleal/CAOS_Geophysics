"""Build the bilingual frozen-checkpoint M12 lesson."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BOOT = """# Load the frozen, hash-bound model; this lesson does not train.
import hashlib, json, sys
from pathlib import Path
root = next(p for p in Path.cwd().parents if (p / "data-pipeline/velocity_validation.py").is_file())
sys.path.insert(0, str(root / "data-pipeline"))
import velocity_validation as method
artifact = root / "models/experimental/m12-velocity-cpu-20260928"
receipt = json.loads((artifact / "receipt.json").read_text(encoding="utf-8"))
checkpoint = artifact / receipt["checkpoint"]
assert hashlib.sha256(checkpoint.read_bytes()).hexdigest() == receipt["checkpoint_sha256"]
source_hash = hashlib.sha256((root / "data-pipeline/velocity_validation.py").read_bytes()).hexdigest()
assert source_hash == receipt["code_sha256"]
operators = method.operators()
selected_lambda, selection = method.select_classical(method.make_cohort("validation", operators), operators)
frozen_model = method.load_checkpoint(checkpoint, receipt["checkpoint_sha256"], "cpu")
print(receipt["status"], receipt["checkpoint_sha256"])
print("lambda", selected_lambda, selection)
from importlib.metadata import version
print({name: version(name) for name in ("numpy", "scipy", "matplotlib", "torch")})
"""
RESULTS = """# Recreate every held-out group and report aggregate metrics, not records.
cohort_results = {}
for name in ("id_test", "family_only", "acquisition_only", "joint_ood"):
    cohort = method.make_cohort(name, operators)
    learned = method._predict(frozen_model, cohort, "cpu")
    classical = method.classical_predict(cohort, operators, selected_lambda)
    cohort_results[name] = method.score(
        cohort, learned, classical, operators, receipt["forward_threshold_ms"])
for name, score in cohort_results.items():
    print(f"{name:18s} n={score['count']} velocity "
          f"{score['learned_velocity_rmse_m_s']:.2f}/"
          f"{score['classical_velocity_rmse_m_s']:.2f} m/s, "
          f"ratio {score['learned_to_classical_velocity_ratio']:.3f}; "
          f"time {score['learned_oracle_rmse_ms']:.3f}/"
          f"{score['classical_oracle_rmse_ms']:.3f} ms, "
          f"ratio {score['learned_to_classical_oracle_ratio']:.3f}; "
          f"above screen {score['forward_threshold_exceedances']}/{score['count']}")
print("joint status", method.scientific_verdict(cohort_results["joint_ood"]))
"""
PLOT = """# Compare one fixed joint-shift survey and overlay its actual ray paths.
import matplotlib.pyplot as plt
joint = method.make_cohort("joint_ood", operators)
learned = method._predict(frozen_model, joint, "cpu")
classical = method.classical_predict(joint, operators, selected_lambda)
i = 0
layout = joint["acquisition"][i]
rays = operators[layout]["rays"]
fig, axes = plt.subplots(1, 3, figsize=(15, 4.6), constrained_layout=True)
for ax, field, title in zip(axes, (joint["velocity"][i], learned[i], classical[i]),
                            ("Known synthetic truth", "Frozen CNN", "Regularized ray inverse")):
    im = ax.imshow(field, origin="upper", extent=(0,800,800,0),
                   vmin=1400, vmax=4000, cmap="viridis")
    for ray in rays[::max(1, len(rays)//28)]:
        ax.plot((ray[0],ray[2]), (ray[1],ray[3]), color="white", alpha=.2, lw=.45)
    ax.set(title=title, xlabel="Distance x (m)")
    ax.set_ylabel("Depth z (m)")
fig.colorbar(im, ax=axes, label="Velocity (m/s)", shrink=.84)
plt.show()
"""

COVERAGE = """# Compare integrated ray support across the three declared survey layouts.
import matplotlib.pyplot as plt
fig, axes = plt.subplots(1, 3, figsize=(12, 4.2), constrained_layout=True)
for ax, layout in zip(axes, ("A", "B", "C")):
    support = operators[layout]["cell"].sum(axis=0)
    support = support.reshape(method.GRID, method.GRID)
    image = ax.imshow(support, origin="upper", extent=(0,800,800,0), cmap="magma")
    ax.set(title=f"Layout {layout}", xlabel="Distance x (m)")
    ax.set_ylabel("Depth z (m)")
fig.colorbar(image, ax=axes, label="Integrated ray length per cell (m)", shrink=.84)
plt.show()
"""
SWEEP = """# Add matched pick noise to fixed joint-shift records; keep truth and lambda fixed.
import numpy as np
noise_levels = np.array([0, .0005, .001, .002, .004])
noise = np.random.default_rng(99104).normal(size=joint["observed"].shape)
sweep = []
for extra in noise_levels:
    test = {**joint, "observed": joint["observed"] + extra * noise}
    test["features"] = np.stack([method.input_features(y, operators[g]["cell"])
                                 for y,g in zip(test["observed"], test["acquisition"])])
    pred = method._predict(frozen_model, test, "cpu")
    base = method.classical_predict(test, operators, selected_lambda)
    score = method.score(
        test, pred, base, operators, receipt["forward_threshold_ms"])
    sweep.append((extra, score))
fig, ax = plt.subplots(figsize=(8.2,4.7), constrained_layout=True)
for key,label in (("learned_to_classical_velocity_ratio","Velocity RMSE ratio"),
                  ("learned_to_classical_oracle_ratio","Independent time RMSE ratio")):
    values = [item[1][key] for item in sweep]
    ax.plot(noise_levels*1000, values, marker="o", lw=2.3, label=label)
ax.axhline(1,color="#333",ls="--",lw=1)
ax.set_yscale("log")
ax.set(xlabel="Additional pick-noise standard deviation (ms)",ylabel="Learned / classical RMSE",
       title="Fixed joint-shift cohort; same noise draw scaled across levels")
ax.grid(True,which="both",alpha=.22)
ax.legend(frameon=False)
plt.show()
for extra,score in sweep:
    print(f"{extra*1000:.1f} ms added: velocity ratio "
          f"{score['learned_to_classical_velocity_ratio']:.3f}; "
          f"time ratio {score['learned_to_classical_oracle_ratio']:.3f}")
"""
OWN = """# Exercise the actual local request parser with a clearly labelled synthetic control.
import json, sys
sys.path.insert(0, str(root / "data-pipeline"))
from velocity_user_data import calculate
survey = method.make_cohort("id_test", operators)
sample = next(i for i,g in enumerate(survey["acquisition"]) if g == "A")
rays = operators["A"]["rays"]
n = min(64, len(rays))
request = {"schema":"geophysics.velocity-user-data/v1","id":"lesson-control-a",
 "source":{"citation":"CAOS_Geophysics deterministic M12 control","rights":"CC0","scope":"synthetic-control"},
 "frame":"local-x-z-down","units":{"distance":"m","time":"s","velocity":"m/s"},
 "ray_ids":[f"ray-{i:03d}" for i in range(n)],"rays_m":rays[:n].tolist(),
 "times_s":survey["observed"][sample][:n].tolist(),"sigma_s":[method.NOISE_S]*n,"lambda":float(selected_lambda)}
encoded = json.dumps(request, sort_keys=True, separators=(",", ":")).encode()
result = calculate(encoded)
print(result["status"], result["warnings"])
print(result["claims"])
"""

EN = [
"""# Travel-time tomography: a learned inverse under held-out stress

This lesson asks whether a compact convolutional network trained to map first-arrival residuals to velocity can outperform a regularized straight-ray inverse when subsurface structure or acquisition geometry changes. It uses a frozen 40-epoch checkpoint and four deterministic cohorts. No model is trained here. Before inference, the notebook checks SHA-256 hashes for the exact weights and source implementation. It regenerates its arrays from declared seeds and lets the comparison fail. The negative result is scientifically useful: the method should be judged against a baseline and its assumptions, not by the smoothness or visual appeal of a panel.

All cases are synthetic two-dimensional first-arrival surveys on a 16 by 16 cell grid spanning 800 m by 800 m, with 50 m cells. Forward data are straight-ray path integrals of slowness with Gaussian pick noise. The examples are not waveforms, bent-ray calculations, field measurements or evidence of field accuracy. Learning objectives are to derive the discrete operator; distinguish amortized prediction from a survey-conditioned solve; inspect a locked train/validation/test split; compare model error with an independent forward score; and identify which changes in distribution expose failure. The last section executes the local user-data contract and makes its provenance requirements concrete.""",
"""## Setup, checkpoint and split provenance

The archived model used random seed 77212 and 40 epochs; validation selected epoch 39. Its compressed weights occupy 121,340 bytes. The receipt records hashes, software versions, split manifests, fixed scales, validation-selected regularization, and outcomes. The notebook loads the small network on CPU. It does not retrain or run the full verifier. This distinction matters: repeating training could produce a different selected checkpoint and would mix a reproduction lesson with a training workflow.

The four cohorts isolate complementary changes. The 160-record id_test group repeats familiar families and layouts. The 80-record family_only group introduces fault and salt structures while retaining layouts A and B. The 80-record acquisition_only group retains familiar structures but switches to layout C. The 160-record joint_ood group changes both. A record is generated deterministically from its seed, family and layout. Training data fit weights; validation selects the checkpoint and lambda; the four test groups estimate performance only after those choices are frozen.

This design makes shifts interpretable, but does not make the synthetic population representative of natural geology. Family categories and acquisition patterns are chosen by the generator. A held-out family is evidence about that controlled change, not every fault or salt body. The receipt and manifest hashes are provenance anchors; a chart alone is not. Test data must not be used to tune the model, features, threshold or interpretation after the scores are seen. If that happens, a new untouched test set is needed.""",
"""## Method: forward physics and its discretization

For a ray path Gamma_i through velocity v, travel time is the path integral of slowness s=1/v plus picking error. Dividing the model into cells makes the integral a sum. Matrix element A_ij is the length in metres that path i spends inside cell j, and s_j is measured in seconds per metre. A times s has seconds, which checks the units of the forward equation. The inverse uses a cell-length matrix. The independent score uses a separately discretized bilinear ray quadrature. Keeping the implementations separate can reveal a transposition or quadrature mismatch that a self-consistent forward/inverse pair could conceal.

$$
\\mathbf{t}=A\\mathbf{s}+\\boldsymbol{\\epsilon},\\qquad s_j=v_j^{-1},\\qquad \\epsilon_i\\sim\\mathcal{N}(0,\\sigma_t^2).
$$

The classical reference estimates a slowness perturbation about a 2,000 m/s background. It whitens by pick uncertainty and minimizes a data residual plus first-difference roughness and a small ridge term. The difference operator penalizes neighboring cell contrasts, so its effect is to suppress oscillation, not to add observations. Lambda is selected from fixed candidates using validation velocity RMSE only; the selected value is 100 and remains fixed for every test. The solver obtains an unconstrained regularized normal-system solution and clips the exported slowness perturbation to the declared physical interval. It is not a bounded least-squares optimizer.

$$
\\hat{\\delta s}=\\arg\\min_{\\delta s}\\|W(A\\delta s-\\delta t)\\|_2^2+\\lambda\\|D\\delta s\\|_2^2+0.01\\|\\delta s\\|_2^2.
$$

The CNN is an amortized deterministic residual model. It receives two channels: a backprojected velocity-scale residual normalized by ray coverage, and normalized coverage itself. A convolutional stack maps these channels to a velocity perturbation added to the reference background. Training minimizes cellwise velocity mean-square error on 800 generated surveys, with validation loss selecting the checkpoint. Once trained, it can return a model quickly, but it does not solve the current survey's regularized objective. The classical reference solves a data-conditioned system for each survey. Neither method removes the assumptions in the straight-ray forward operator, fixed grid, chosen background or synthetic data distribution.

A low data residual does not imply the true structure has been recovered. Rays leave weakly sampled cells with limited information, and smoothness trades localized detail against variance. Distinct velocity fields can predict similar times along a limited set of paths. This is an identifiability issue. Coverage, parameterization, data errors and regularization must be interpreted together. Model-space error against known truth and independently calculated time prediction answer different questions; reporting only one can conceal a failed inversion.""",
"""## Locked calculation and measurement definitions

The next cells verify the source and checkpoint hashes, rebuild the four fixed cohorts and calculate both methods. The baseline parameter comes from validation, never test. Velocity RMSE compares each estimated cell to the known synthetic model, then averages the per-survey values. The independent travel-time RMSE propagates estimated velocity through the separate quadrature operator and compares predictions with noisy picks. The learned/classical ratio is above one when the learned estimator has more error. The validation-derived screen is the 95th percentile of learned forward error on validation; exceedance is a screening flag, not a geological classifier or guarantee of accuracy.

The recomputed ratios are 27.60 and 26.80 on id_test, 5.62 and 12.28 on family_only, 27.22 and 25.60 on acquisition_only, and 5.62 and 12.23 on joint_ood, for velocity and independent time error respectively. In joint_ood, 43 of 160 surveys exceed the validation screen. These outcomes mean the frozen network loses on both measures in all four groups. A narrower ratio on joint shift does not mean the network becomes more useful: the classical baseline also degrades, so the ratio narrows while both absolute errors remain high. Always inspect numerator and denominator alongside a ratio.

The failure is already severe on id_test, so the result cannot be described only as distribution shift. The larger out-of-family and joint errors show additional sensitivity, but these measurements do not isolate whether the main cause is architecture, feature scaling, optimization, target distribution or another implementation issue. The receipt therefore labels the result failed-held-out-comparator. This conclusion rejects this checkpoint and protocol; it does not establish that all learned travel-time tomography fails. A new hypothesis and untouched test cohorts are needed to attribute a cause.""",
"""## Inspect an actual held-out result

The displayed survey is a fixed record from the joint family/acquisition shift. Truth, CNN estimate and regularized estimate share one velocity scale. Thin lines are a subset of actual layout-C rays, not a wavefield animation. The overlay makes support visible: ray intersections are uneven, so some cells rely more strongly on regularization or the learned prior. The picture can show where estimates differ, but one survey cannot establish how often a method wins. The locked cohort summaries carry that evidence.

A smooth output is not automatically physical. The CNN is not guaranteed to honor the current survey objective or a model bound just because its panel looks coherent. The classical result is not truth either: its linearization, roughness penalty, background and straight paths can bias it. For a real interpretation, inspect sensitivity and resolution as well as the estimated field. In cells with little crossing coverage, report that information is weak instead of assigning geological meaning to a colored feature. A prettier rendering cannot add missing observations.""",
"""## Sensitivity experiment: additional pick noise

The next experiment changes only one declared input. It holds the joint-shift truths, rays, record identities, checkpoint and selected lambda fixed, then adds independent zero-mean pick perturbations at five standard deviations. One standardized random draw is scaled across levels, keeping cases paired. Both methods receive the same perturbed picks. The plot shows learned error divided by classical error for velocity and independently forwarded time. Values over one mean the CNN remains worse.

The original synthetic observations already include generator noise. The horizontal axis is additional noise, not total uncertainty. This is a conditional stress test of one frozen model on one generated cohort. It does not retrain the CNN, retune the classical method, estimate real field noise, or add independent held-out evidence. A ratio moving toward one is not necessarily an improvement: inspect absolute errors, because either method may change. Correlated, heavy-tailed or frequency-dependent picking errors are outside this Gaussian perturbation experiment. No universal noise tolerance follows from this curve.""",
"""## Run the actual local user-data path

A user survey is not a filename with numbers attached. The accepted JSON contract records citation, rights and scope for its source; the local x-z-down coordinate frame; distance, time and velocity units; unique ray IDs; endpoints; times; pick uncertainties; and lambda. The parser rejects missing or ambiguous fields before numerical libraries are loaded. The worked call below takes rays and picks from one generated survey, labels the source synthetic-control, and invokes the actual local calculation function. This verifies the data path without presenting synthetic data as field data.

Replace the example only with observations whose source, reuse rights, datum, coordinate frame, units and pick convention are known. The current API uses its fixed 800 m domain and 16 by 16 grid. It requires 8 to 2,048 rays, finite endpoints inside the domain, positive times and uncertainties, and lambda within its accepted range. Passing validation proves structural compatibility, not scientific appropriateness. A different domain, larger survey or alternate forward physics needs a separately justified parameterization, memory budget and independent verification.

The result explicitly reports field truth unknown, field validation false and online admission false. This is a local CPU calculation; the request is not sent to the VPS. The learned estimator is not enabled because this checkpoint failed held-out comparison. For authentic work, preserve original picks, acquisition geometry, uncertainty estimates, source citation, rights, software versions, request hash, coverage and residuals. Never infer a datum or unit from plausible-looking values. This provenance lets another analyst review the calculation and its limits.""",
"""## Interpretation, limitations and next study

The evidence supports a narrow negative conclusion: this archived CNN does not beat the regularized straight-ray reference on the locked synthetic groups in either known-truth velocity error or independent travel-time error. Its large in-distribution gap suggests a mismatch, inadequate representation or training defect, while the shifted groups additionally demonstrate distribution sensitivity. The experiment cannot distinguish those causes. Choosing a new test after seeing these results would contaminate it; a revised method needs fresh, untouched family and geometry holdouts and an explicit acceptance protocol.

This is not a broad state-of-the-art comparison with eikonal tomography, probabilistic inversion, full-waveform inversion or current production packages. It evaluates one small CNN and one regularized baseline on synthetic straight-ray first arrivals. It does not claim novelty, field generalization or universal failure. Keep the negative receipt. A credible next study should state a falsifiable hypothesis, select models only on training/validation data, compare against a justified baseline, and score predictions with an independent forward implementation.

For field surveys, first establish data rights, quality control, acquisition geometry, datum, units, uncertainty weights and physics-appropriate forward modeling. Then inspect residual patterns, coverage and parameter sensitivity. A low residual can coexist with the wrong subsurface model. Report which data are authentic, what is synthetic, what assumptions are active and which regions are poorly resolved. Export original observations and provenance with derived models. A rendered image is a view of the calculation, never a substitute for it.""",
"""## Summary

Travel-time inversion maps incomplete path integrals into a spatial model. Acquisition geometry, parameterization, noise, prior information and regularization condition the answer; a learned map also depends on its training distribution and feature scaling. In this reproducible benchmark the frozen CNN loses to the classical reference on all four held-out groups. Retain that failure, limit the scientific claim and require untouched tests for any redesign. Smoothness is not evidence of accuracy.

## References

1. Berryman (1989), weighted least-squares criteria for seismic travel-time tomography. [doi:10.1109/36.17671](https://doi.org/10.1109/36.17671).
2. Aster, Borchers and Thurber (2018), *Parameter Estimation and Inverse Problems*, 3rd ed. [doi:10.1016/C2015-0-02458-3](https://doi.org/10.1016/C2015-0-02458-3).
3. Rawlinson, Pozgay and Fishwick (2010), seismic tomography. [doi:10.1016/j.pepi.2009.10.002](https://doi.org/10.1016/j.pepi.2009.10.002).
4. Araya-Polo et al. (2018), deep-learning tomography. [doi:10.1190/tle37010058.1](https://doi.org/10.1190/tle37010058.1).
5. Earp and Curtis (2020), “Probabilistic neural network-based 2D travel-time tomography,” *Neural Computing and Applications*, 32, 17077–17095. Its mixture-density approach is probabilistic and differs from the deterministic CNN implemented here. [doi:10.1007/s00521-020-04921-8](https://doi.org/10.1007/s00521-020-04921-8).
6. CAOS Geophysics (2026), M12 checkpoint receipt and cohort-generation source. [Repository](https://github.com/fsantibanezleal/CAOS_Geophysics)."""
]

ES = [
"""# Tomografía de tiempos de viaje: inversa aprendida bajo pruebas retenidas

Esta lección pregunta si una red convolucional compacta, entrenada para mapear residuos de primeras llegadas a velocidad, supera a una inversa regularizada de rayos rectos cuando cambia la estructura del subsuelo o la geometría de adquisición. Usa un checkpoint congelado de 40 épocas y cuatro cohortes deterministas. Aquí no se entrena ningún modelo. Antes de inferir, la libreta verifica los hashes SHA-256 de los pesos y de la implementación exacta. Regenera sus arreglos desde semillas declaradas y permite que la comparación falle. El resultado negativo es útil científicamente: el método debe juzgarse frente a una referencia y sus supuestos, no por la suavidad o atractivo de una imagen.

Todos los casos son levantamientos sintéticos 2-D de primeras llegadas en una malla de 16 por 16 celdas que cubre 800 m por 800 m, con celdas de 50 m. Los datos directos son integrales de lentitud sobre rayos rectos con ruido gaussiano. No son formas de onda, cálculos con rayos curvos, mediciones de campo ni evidencia de precisión en campo. Los objetivos son derivar el operador discreto; distinguir predicción amortizada de solución condicionada por el levantamiento; inspeccionar particiones bloqueadas de entrenamiento/validación/prueba; comparar error del modelo y puntaje directo independiente; e identificar cambios de distribución que exponen fallas. La última sección ejecuta el contrato local de datos y concreta sus requisitos de procedencia.""",
"""## Preparación, checkpoint y procedencia de particiones

El modelo archivado usó la semilla 77212 y 40 épocas; validación seleccionó la época 39. Los pesos comprimidos ocupan 121.340 bytes. El recibo registra hashes, versiones, manifiestos de partición, escalas fijas, regularización seleccionada en validación y resultados. La libreta carga la red pequeña en CPU. No vuelve a entrenar ni ejecuta el verificador integral. Esta distinción importa: repetir entrenamiento podría producir otro checkpoint y mezclar una lección de reproducción con un flujo de entrenamiento.

Las cuatro cohortes aíslan cambios complementarios. id_test contiene 160 registros de familias y geometrías conocidas. family_only contiene 80 estructuras de falla y sal con geometrías A y B. acquisition_only contiene 80 estructuras familiares con geometría C. joint_ood cambia ambas dimensiones y contiene 160 registros. Cada registro se genera determinísticamente desde semilla, familia y geometría. Los datos de entrenamiento ajustan los pesos; validación selecciona checkpoint y lambda; las cuatro pruebas estiman rendimiento después de congelar esas decisiones.

Este diseño permite interpretar desplazamientos, pero no convierte la población sintética en representativa de la geología natural. El generador elige familias y patrones de adquisición. Una familia retenida informa sobre ese cambio controlado, no sobre todas las fallas o cuerpos salinos. Los manifiestos y hashes del recibo son anclas de procedencia; una gráfica no lo es. Los datos de prueba no deben ajustar el modelo, características, umbral o interpretación una vez conocidos los puntajes. Si sucede, hace falta una nueva prueba intacta.""",
"""## Método: física directa y discretización

Para una trayectoria Gamma_i en velocidad v, el tiempo de viaje es la integral de lentitud s=1/v más el error de lectura. Dividir el modelo en celdas transforma la integral en una suma. El elemento A_ij es la longitud en metros que la trayectoria i recorre dentro de la celda j; s_j se mide en segundos por metro. Longitud por lentitud da segundos y permite comprobar unidades. La inversa usa una matriz de longitudes celulares. El puntaje independiente usa una cuadratura bilineal de rayos discretizada por separado. Mantener implementaciones distintas puede revelar una transposición o discrepancia de cuadratura que una pareja directa/inversa autorreferente ocultaría.

$$
\\mathbf{t}=A\\mathbf{s}+\\boldsymbol{\\epsilon},\\qquad s_j=v_j^{-1},\\qquad \\epsilon_i\\sim\\mathcal{N}(0,\\sigma_t^2).
$$

La referencia clásica estima una perturbación de lentitud alrededor de un fondo de 2.000 m/s. Pondera por incertidumbre de lectura y minimiza el residuo de datos más rugosidad de primeras diferencias y un ridge pequeño. El operador de diferencias penaliza contrastes entre celdas vecinas: reduce oscilación, no agrega observaciones. Lambda se elige entre candidatos fijos con el RMSE de velocidad de validación; el valor seleccionado es 100 y permanece fijo en todas las pruebas. El solucionador obtiene una solución no acotada del sistema normal regularizado y recorta la perturbación de lentitud exportada al intervalo físico declarado. No es mínimos cuadrados acotados.

$$
\\hat{\\delta s}=\\arg\\min_{\\delta s}\\|W(A\\delta s-\\delta t)\\|_2^2+\\lambda\\|D\\delta s\\|_2^2+0.01\\|\\delta s\\|_2^2.
$$

La CNN residual determinista es un modelo amortizado. Recibe dos canales: residuo de escala de velocidad retroproyectado y normalizado por cobertura, y cobertura de rayos normalizada. Una pila convolucional produce una perturbación de velocidad que se agrega al fondo. El entrenamiento minimiza el error cuadrático de velocidad por celda en 800 levantamientos; la pérdida de validación elige el checkpoint. Ya entrenada, predice rápido, pero no resuelve el objetivo regularizado del levantamiento actual. La referencia clásica sí resuelve un sistema condicionado por cada levantamiento. Ninguna elimina los supuestos del operador de rayos rectos, malla fija, fondo elegido o distribución sintética.

Un residuo pequeño no implica recuperar la estructura verdadera. Los rayos dejan celdas con información limitada y la suavidad intercambia detalle localizado por varianza. Campos de velocidad distintos pueden predecir tiempos similares a lo largo de pocos caminos. Es un problema de identificabilidad. Cobertura, parametrización, errores y regularización deben interpretarse conjuntamente. El error de modelo respecto de una verdad conocida y el error temporal calculado independientemente responden preguntas distintas; informar solo uno puede ocultar una inversa fallida.""",
"""## Cálculo bloqueado y definiciones de métricas

Las siguientes celdas verifican hashes, reconstruyen cuatro cohortes fijas y calculan ambos métodos. El parámetro de referencia proviene solo de validación. El RMSE de velocidad compara cada celda con el modelo sintético conocido y luego promedia por levantamiento. El RMSE temporal independiente propaga la velocidad estimada por la cuadratura separada y compara predicciones con lecturas ruidosas. La razón aprendido/clásico es mayor que uno cuando el método aprendido tiene más error. El umbral de validación es el percentil 95 del error directo aprendido en validación; excederlo es una señal de revisión, no un clasificador geológico ni garantía de precisión.

Las razones recalculadas son 27,60 y 26,80 en id_test; 5,62 y 12,28 en family_only; 27,22 y 25,60 en acquisition_only; y 5,62 y 12,23 en joint_ood, para velocidad y tiempo independiente. En joint_ood, 43 de 160 levantamientos superan el umbral de validación. Estos resultados muestran que la red congelada pierde en ambas métricas en los cuatro grupos. Una razón más estrecha en el cambio conjunto no la vuelve más útil: la referencia clásica también empeora, por lo que la razón se acerca a uno mientras ambos errores absolutos siguen altos. Revise siempre numerador y denominador junto a la razón.

La falla ya es severa en id_test, así que no puede describirse solo como cambio de distribución. Los mayores errores fuera de familia y en el grupo conjunto muestran sensibilidad adicional, pero estas mediciones no separan arquitectura, escalas, optimización, distribución objetivo u otro problema de implementación. El recibo clasifica el resultado como failed-held-out-comparator. Se rechaza este checkpoint y protocolo; no se demuestra que toda tomografía aprendida falle. Para atribuir una causa hacen falta hipótesis nuevas y cohortes de prueba intactas.""",
"""## Inspeccione un resultado retenido real

El levantamiento mostrado es un registro fijo con cambios conjuntos de familia y adquisición. Verdad, estimación CNN e inversa regularizada comparten escala de velocidad. Las líneas finas son rayos reales de geometría C, no una animación de campo de ondas. El trazado hace visible el soporte: las intersecciones son desiguales y algunas celdas dependen más de la regularización o del prior aprendido. La imagen muestra dónde difieren los modelos, pero un caso no establece con qué frecuencia gana un método. Para eso están los resúmenes de la cohorte intacta.

Una salida suave no es automáticamente física. La CNN no garantiza respetar el objetivo del levantamiento ni las cotas físicas por verse coherente. El resultado clásico tampoco es verdad: linealización, penalización, fondo y trayectorias rectas pueden sesgarlo. En una interpretación real, revise sensibilidad y resolución además del campo estimado. En celdas con poca cobertura de rayos cruzados, declare que la información es débil en vez de atribuir significado geológico a un color. Una visualización más bonita no agrega observaciones faltantes.""",
"""## Sensibilidad: ruido adicional en las lecturas

El siguiente experimento cambia solo una entrada declarada. Mantiene fijas las verdades, rayos, identidades de registro, checkpoint y lambda de la cohorte conjunta, y agrega ruido independiente de media cero en cinco desviaciones estándar. Una misma realización aleatoria estandarizada se escala entre niveles para emparejar casos. Ambos métodos reciben las mismas lecturas perturbadas. La gráfica muestra error aprendido dividido por error clásico para velocidad y tiempo directo independiente. Más de uno significa que la CNN sigue peor.

Las observaciones sintéticas originales ya contienen ruido del generador. El eje horizontal muestra ruido adicional, no incertidumbre total. Es una prueba condicional de fragilidad de un modelo congelado en una cohorte generada. No reentrena la CNN, no reajusta el método clásico, no estima ruido real de campo ni agrega evidencia de prueba independiente. Que una razón se acerque a uno no es necesariamente mejora: revise errores absolutos porque ambos métodos pueden cambiar. Errores correlacionados, de colas pesadas o dependientes de frecuencia quedan fuera de esta perturbación gaussiana. La curva no define una tolerancia universal.""",
"""## Ejecute la ruta local real de datos del usuario

Un levantamiento no es un nombre de archivo con números. El contrato JSON requiere cita, derechos y alcance de la fuente; marco local x-z hacia abajo; unidades de distancia, tiempo y velocidad; identificadores únicos; extremos; tiempos; incertidumbres de lectura y lambda. El parser rechaza campos ausentes o ambiguos antes de cargar bibliotecas numéricas. La llamada ilustrativa toma rayos y lecturas de un caso generado, lo marca synthetic-control e invoca la función local real. Verifica la ruta sin presentar datos sintéticos como mediciones de campo.

Reemplace el ejemplo solo por observaciones con fuente, derechos, datum, marco de coordenadas, unidades y convención de lectura conocidos. La API actual usa dominio fijo de 800 m y malla de 16 por 16. Requiere 8 a 2.048 rayos, extremos finitos dentro del dominio, tiempos e incertidumbres positivos y lambda admisible. La validación estructural no prueba que los datos sean físicamente apropiados. Otro dominio, levantamiento mayor o física distinta requieren parametrización justificada, memoria presupuestada y verificación independiente.

El resultado declara verdad de campo desconocida, validación de campo falsa y admisión en línea falsa. Es un cálculo CPU local; no se envía la solicitud al VPS. El estimador aprendido está desactivado porque falló la comparación retenida. En trabajo auténtico conserve lecturas originales, geometría, incertidumbres, fuente, versiones, hash de solicitud, cobertura y residuos. Nunca infiera datum o unidades porque los valores parezcan plausibles. Esa procedencia permite revisar tanto el cálculo como sus límites.""",
"""## Interpretación, límites y siguiente estudio

La evidencia sustenta una conclusión negativa acotada: esta CNN archivada no supera la referencia regularizada de rayos rectos en los grupos sintéticos bloqueados, ni en error de velocidad con verdad conocida ni en tiempos directos independientes. La gran brecha en distribución sugiere incompatibilidad, representación insuficiente o defecto de entrenamiento; los grupos desplazados también muestran sensibilidad a distribución. El experimento no distingue esas causas. Elegir una prueba nueva después de conocer estos resultados la contaminaría; el método revisado necesita familias y geometrías nuevas intactas y un protocolo de aceptación explícito.

Esto no es una comparación amplia con tomografía eikonal, inversión probabilística, forma de onda completa o paquetes actuales. Evalúa una CNN pequeña y una referencia regularizada con primeras llegadas sintéticas de rayos rectos. No afirma novedad, generalización a campo ni falla universal. Conserve el recibo negativo. Un estudio convincente debe declarar hipótesis falsable, seleccionar solo con entrenamiento/validación, usar una referencia justificada y puntuar predicciones mediante implementación directa independiente.

Para levantamientos de campo, establezca primero derechos, control de calidad, geometría, datum, unidades, incertidumbres y física apropiada para el operador directo. Luego examine patrones de residuos, cobertura y sensibilidad de parámetros. Un residuo bajo puede coexistir con un modelo incorrecto. Informe qué datos son auténticos, qué es sintético, qué supuestos se aplican y qué zonas están mal resueltas. Exporte observaciones originales y procedencia junto a los modelos derivados. Una imagen renderizada muestra el cálculo; nunca lo reemplaza.""",
"""## Resumen

La inversa de tiempos de viaje mapea integrales incompletas a un modelo espacial. Geometría, parametrización, ruido, información previa y regularización condicionan la respuesta; un mapa aprendido también depende de su distribución y escalas. En este benchmark reproducible la CNN congelada pierde frente a la referencia clásica en los cuatro grupos retenidos. Conserve la falla, limite la conclusión y exija pruebas intactas para cualquier rediseño. La suavidad no es evidencia de precisión.

## Referencias

1. Berryman (1989), criterios de mínimos cuadrados ponderados para tomografía sísmica. [doi:10.1109/36.17671](https://doi.org/10.1109/36.17671).
2. Aster, Borchers y Thurber (2018), *Parameter Estimation and Inverse Problems*, 3.ª ed. [doi:10.1016/C2015-0-02458-3](https://doi.org/10.1016/C2015-0-02458-3).
3. Rawlinson, Pozgay y Fishwick (2010), tomografía sísmica. [doi:10.1016/j.pepi.2009.10.002](https://doi.org/10.1016/j.pepi.2009.10.002).
4. Araya-Polo et al. (2018), tomografía con aprendizaje profundo. [doi:10.1190/tle37010058.1](https://doi.org/10.1190/tle37010058.1).
5. Earp y Curtis (2020), “Probabilistic neural network-based 2D travel-time tomography”, *Neural Computing and Applications*, 32, 17077–17095. Su enfoque de mezcla de densidades es probabilístico y difiere de la CNN determinista aquí implementada. [doi:10.1007/s00521-020-04921-8](https://doi.org/10.1007/s00521-020-04921-8).
6. CAOS Geophysics (2026), recibo del checkpoint M12 y código de cohortes. [Repositorio](https://github.com/fsantibanezleal/CAOS_Geophysics)."""
]

for lang, text in (("en", EN), ("es", ES)):
    cells = []
    if lang == "en":
        text[0] = text[0].replace("\n\nThis lesson asks", "\n\n**Question:** Does the frozen learned estimator outperform the regularized ray inverse on unseen surveys?\n\nThis lesson asks")
        text[0] = text[0].replace("Learning objectives are", "\n\n## Objectives\n\nLearning objectives are")
        text[0] += "\n\n## Setup\n\nUse the repository notebook environment. If packages need installation, run: pip install numpy==2.2.6 scipy==1.15.2 matplotlib==3.10.8 torch==2.14.0. The final setup cell prints the versions actually imported."
        text[1] = text[1].replace("## Setup, checkpoint and split provenance", "## Data")
        text[2] = text[2].replace("## Method: forward physics and its discretization", "## Method")
        text[2] += "\n\nThe linearization also defines what the baseline can resolve. If s=s0+delta_s, the predicted perturbation is A delta_s only while paths and the cell parameterization remain fixed. The diagonal data weights scale each residual by its stated standard deviation. The finite-difference matrix D encodes adjacency; changing grid spacing or boundary handling changes its physical meaning. Lambda therefore has meaning only with this mesh, data scaling and operator. Its selected numeric value is not transferable to another survey by name alone.\n\nAny vector n with A n near zero lies near the discrete null space: available rays barely change their times when that model perturbation is added. Regularization chooses a stable member of many data-compatible models; it does not turn the missing information into observations. Better coverage can shrink the null space, but a cell-coverage count is only a first diagnostic and does not capture all parameter tradeoffs. Resolution and uncertainty require explicit sensitivity or posterior analysis. The benchmark reports error against a known synthetic truth, not a formal covariance or uncertainty interval."
        text[3] = text[3].replace("## Locked calculation and measurement definitions", "## Comparison")
        text[4] = text[4].replace("## Inspect an actual held-out result", "### Inspect an actual held-out result")
        text[5] = text[5].replace("## Sensitivity experiment: additional pick noise", "### Sensitivity experiment: additional pick noise")
        text[6] = text[6].replace("## Run the actual local user-data path", "### Own data: run the local user-data path")
        text[7] = text[7].replace("## Interpretation, limitations and next study", "## Results\n\n**Answer:** No. On the joint held-out cohort, the learned/classical RMSE ratios are 5.616 for velocity and 12.231 for independent travel time; both exceed one.")
    else:
        text[0] = text[0].replace("\n\nEsta lección pregunta", "\n\n**Pregunta:** ¿La inversa aprendida congelada supera a la inversa regularizada en levantamientos no vistos?\n\nEsta lección pregunta")
        text[0] = text[0].replace("Los objetivos son", "\n\n## Objetivos\n\nLos objetivos son")
        text[0] += "\n\n## Preparación\n\nUse el entorno de notebooks del repositorio. Si debe instalar paquetes: pip install numpy==2.2.6 scipy==1.15.2 matplotlib==3.10.8 torch==2.14.0. La última celda de preparación informa las versiones importadas."
        text[1] = text[1].replace("## Preparación, checkpoint y procedencia de particiones", "## Datos")
        text[2] = text[2].replace("## Método: física directa y discretización", "## Método")
        text[2] += "\n\nLa linealización también define qué puede resolver la referencia. Si s=s0+delta_s, la perturbación predicha es A delta_s solo mientras las trayectorias y la parametrización celular permanezcan fijas. Los pesos diagonales escalan cada residuo por su desviación estándar. La matriz de diferencias D codifica vecindad; cambiar el espaciamiento de la malla o las condiciones de borde altera su significado físico. Por eso lambda solo tiene sentido con esta malla, escala de datos y operador. Su valor seleccionado no se transfiere a otro levantamiento por llevar el mismo nombre.\n\nTodo vector n con A n cercano a cero pertenece aproximadamente al espacio nulo discreto: los rayos disponibles apenas cambian sus tiempos al agregar esa perturbación al modelo. La regularización escoge un miembro estable entre muchos modelos compatibles con datos; no convierte información ausente en observaciones. Mejor cobertura puede reducir el espacio nulo, pero el conteo por celda es solo un diagnóstico inicial y no captura todos los compromisos entre parámetros. Resolución e incertidumbre requieren análisis de sensibilidad o posterior explícitos. El benchmark informa error frente a verdad sintética conocida, no covarianza formal ni intervalo de incertidumbre."
        text[3] = text[3].replace("## Cálculo bloqueado y definiciones de métricas", "## Comparación")
        text[4] = text[4].replace("## Inspeccione un resultado retenido real", "### Inspeccione un resultado retenido real")
        text[5] = text[5].replace("## Sensibilidad: ruido adicional en las lecturas", "### Sensibilidad: ruido adicional en las lecturas")
        text[6] = text[6].replace("## Ejecute la ruta local real de datos del usuario", "### Datos propios: ejecute la ruta local del usuario")
        text[7] = text[7].replace("## Interpretación, límites y siguiente estudio", "## Resultados\n\n**Respuesta:** No. En la cohorte conjunta retenida, las razones RMSE aprendido/clásico son 5,616 para velocidad y 12,231 para tiempo independiente; ambas superan uno.")
    def md(value): cells.append({"cell_type":"markdown","id":f"{lang}-cell-{len(cells):02d}","metadata":{},"source":value.splitlines(keepends=True)})
    def code(value): cells.append({"cell_type":"code","id":f"{lang}-cell-{len(cells):02d}","execution_count":None,"metadata":{},"outputs":[],"source":value.splitlines(keepends=True)})
    for i, section in enumerate(text):
        md(section)
        if i == 0:
            md("### Reproduce the frozen calculation\n\nThe next cell verifies archived inputs, selects the baseline parameter on validation, and loads the checkpoint for CPU inference. It does not train or run the end-to-end verifier." if lang == "en" else "### Reproduzca el cálculo congelado\n\nLa siguiente celda verifica los insumos archivados, elige el parámetro de referencia con validación y carga el checkpoint para inferencia en CPU. No entrena ni ejecuta el verificador integral.")
            code(BOOT)
        if i == 3:
            code(RESULTS)
        if i == 4:
            code(PLOT)
            md("### Ray support across the acquisition designs\n\nSummed cell path length exposes how layouts A, B and C sample the grid differently. It is a coverage diagnostic, not a resolution matrix: two regions with equal path length can still have different crossing angles and parameter tradeoffs. Compare the layout-C pattern with the joint-shift model panel before interpreting local detail." if lang == "en" else "### Soporte de rayos en las geometrías\n\nLa longitud acumulada de trayectorias por celda muestra diferencias de muestreo entre A, B y C. Es un diagnóstico de cobertura, no una matriz de resolución: regiones con igual longitud pueden tener ángulos de cruce y compromisos entre parámetros distintos. Compare el patrón C con el panel del modelo bajo cambio conjunto antes de interpretar detalles locales.")
            code(COVERAGE)
        if i == 5:
            code(SWEEP)
        if i == 6:
            code(OWN)
    sources = ["https://doi.org/10.1109/36.17671","https://doi.org/10.1016/C2015-0-02458-3","https://doi.org/10.1016/j.pepi.2009.10.002","https://doi.org/10.1190/tle37010058.1","https://doi.org/10.1007/s00521-020-04921-8"]
    nb = {"cells":cells,"metadata":{"kernelspec":{"display_name":"CAOS Pipeline Python","language":"python","name":"caos-pipeline"},"language_info":{"name":"python"},"caos":{"beyond":[],"data":["data-pipeline/velocity_validation.py","data-pipeline/velocity_user_data.py","models/experimental/m12-velocity-cpu-20260928/receipt.json","models/experimental/m12-velocity-cpu-20260928/m12-velocity.npz"],"language":lang,"level":3,"methods":["M-12"],"packages":["numpy==2.2.6","scipy==1.15.2","matplotlib==3.10.8","torch==2.14.0"],"sources":sources,"title":"Travel-time tomography: a learned inverse under held-out stress" if lang=="en" else "Tomografía de tiempos de viaje: inversa aprendida bajo pruebas retenidas","topic":"08-learning"}},"nbformat":4,"nbformat_minor":5}
    path = ROOT/"notebooks"/lang/"08-learning"/"05-m12-velocity-checkpoint.ipynb"
    path.write_text(json.dumps(nb,ensure_ascii=False,indent=1)+"\n",encoding="utf-8")
    words = sum(len("".join(c["source"]).split()) for c in cells if c["cell_type"]=="markdown")
    print(f"{lang}: {len(cells)} cells; {words} markdown words")
