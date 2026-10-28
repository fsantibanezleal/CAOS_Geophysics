"""Build the bilingual M04 objective/validation lesson pair from one cell set."""

import json
import uuid
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REFERENCE = ROOT / "notebooks/en/03-magnetics/03-m04-induced-prism-forward.ipynb"


def _cell(kind, source):
    return {"cell_type": kind, "id": uuid.uuid4().hex[:8], "metadata": {},
            "source": source.splitlines(keepends=True),
            **({"execution_count": None, "outputs": []} if kind == "code" else {})}


def _notebook(language):
    es = language == "es"
    translated = {
        "title": ("M04 — Assemble and score a magnetic fit fold" if not es else
                  "M04 — Ensamblar y evaluar un pliegue magnético"),
        "question": ("How does a physical magnetic prediction enter a noise-weighted objective, "
                     "and how do we keep held-out rows out of fitting?" if not es else
                     "¿Cómo entra una predicción magnética física en un objetivo ponderado por ruido, "
                     "y cómo evitamos que las filas retenidas participen en el ajuste?"),
        "prereq": ("**Level 3 · Prerequisites: the M04 forward and M03 spatial-holdout lessons; read time: 30 minutes.**" if not es else
                   "**Nivel 3 · Requisitos: las lecciones M04 de problema directo y M03 de partición espacial; lectura: 30 minutos.**"),
        "objectives": ("## Objectives\n\n" if not es else "## Objetivos\n\n"),
        "objective_text": ("Build a real fit-fold objective from the closed survey protocol, an actual SimPEG/Geoana prism kernel, "
                           "Gaussian uncertainty, and volume-normalized regularization. Check its derivative numerically, "
                           "then score a frozen model on a separate validation fold. This lesson does not run or claim a magnetic inversion." if not es else
                           "Construir un objetivo real de un pliegue de ajuste a partir del protocolo cerrado, un kernel de prismas "
                           "SimPEG/Geoana, incertidumbre gaussiana y regularización normalizada por volumen. Verificar su derivada "
                           "numéricamente y evaluar después un modelo congelado en un pliegue de validación separado. Esta lección no ejecuta ni afirma una inversión magnética."),
        "setup": ("## Setup\n\n" if not es else "## Preparación\n\n"),
        "setup_text": ("Use the pinned Python 3.12 pipeline environment. The notebook installs nothing. The authored survey below is a "
                       "protocol control, not a provider acquisition or field dataset." if not es else
                       "Usa el entorno fijado de la tubería Python 3.12. El notebook no instala paquetes. El levantamiento creado abajo "
                       "es un control del protocolo, no una adquisición de proveedor ni datos de campo."),
        "imports": ("Locate the repository and import the exact implementations. The helper fixture is explicitly protocol-only." if not es else
                    "Localiza el repositorio e importa las implementaciones exactas. El fixture auxiliar es explícitamente solo de protocolo."),
        "data": ("## Data\n\n" if not es else "## Datos\n\n"),
        "data_text": ("The fixture contains 288 receiver rows, a bounded 3D active-cell mesh, a uniform inducing-field declaration, "
                      "zero protocol observations and diagonal conditional standard deviations. We set a nonzero starting susceptibility "
                      "to exercise the physical response; that value is a prior start, not geological truth. Hashes are recomputed before parsing." if not es else
                      "El fixture contiene 288 filas receptoras, una malla 3D acotada de celdas activas, un campo inductor uniforme declarado, "
                      "observaciones de protocolo nulas y desviaciones estándar diagonales condicionales. Fijamos una susceptibilidad inicial "
                      "no nula para activar la respuesta física; ese valor es el inicio del prior, no la verdad geológica. Recalculamos los hashes antes de analizar."),
        "method": ("## Method\n\n" if not es else "## Método\n\n"),
        "method_text": ("For secondary ENU data, the prism response is linear in susceptibility: `s(q)=G(0.01q)`, where `q=chi/0.01`. "
                        "For selected fit rows the Gaussian objective is `phi_d = ||L^-1 (s(q)-d)||_2^2`; for diagonal SD, `L=diag(sigma)`, "
                        "and for full covariance `LL^T=C` on the selected principal submatrix. The data gradient is `2 J_q^T C^-1(s-d)`. "
                        "The regularizer uses cell-volume fractions and active-neighbor face terms with physical length scales. This code assembles and evaluates those terms; it does not choose beta or optimize q." if not es else
                        "Para datos secundarios ENU, la respuesta de prismas es lineal en susceptibilidad: `s(q)=G(0.01q)`, con `q=chi/0.01`. "
                        "En las filas de ajuste seleccionadas, el objetivo gaussiano es `phi_d = ||L^-1 (s(q)-d)||_2^2`; para SD diagonal, "
                        "`L=diag(sigma)`, y para covarianza completa `LL^T=C` en la submatriz principal seleccionada. El gradiente de datos es "
                        "`2 J_q^T C^-1(s-d)`. El regularizador usa fracciones de volumen de celdas y caras entre vecinas activas con escalas físicas. "
                        "Este código ensambla y evalúa esos términos; no elige beta ni optimiza q."),
        "state": ("## State of the art\n\n" if not es else "## Estado del arte\n\n"),
        "state_text": ("Potential-field inversion is non-unique: a small residual does not identify a unique geology. Spatially blocked "
                       "validation estimates predictive behavior under the declared survey geometry; it does not prove field transfer. "
                       "The scorer below is deliberately separate from the fit assembler and returns aggregate metrics only. It cannot select a candidate or open the outer holdout." if not es else
                       "La inversión de campos potenciales no es única: un residual pequeño no identifica una geología única. La validación "
                       "por bloques espaciales estima el comportamiento predictivo bajo la geometría declarada; no demuestra transferencia "
                       "a campo. El evaluador de abajo está separado deliberadamente del ensamblador de ajuste y devuelve solo métricas agregadas. No puede seleccionar candidatos ni abrir la partición externa."),
        "results": ("## Results\n\n" if not es else "## Resultados\n\n"),
        "results_text": ("Plan the original survey, inspect the row assignment, and confirm that fit, validation and outer rows are disjoint. "
                         "Geometry planning sees no amplitudes or noise values." if not es else
                        "Planifica el levantamiento original, inspecciona la asignación de filas y confirma que ajuste, validación y partición "
                        "externa son disjuntos. El planificador geométrico no lee amplitudes ni valores de ruido."),
        "assemble_text": ("Assemble only fold 0 fit rows. The actual forward operator evaluates the user-declared mesh and field; the regularizer is the pinned SimPEG WLS implementation." if not es else
                          "Ensambla solo las filas de ajuste del pliegue 0. El operador directo evalúa la malla y el campo declarados; el regularizador es la implementación WLS fijada de SimPEG."),
        "plot_text": ("Map the computed east-component prediction and its observed-minus-predicted fit residual at their actual ENU coordinates. The inputs are a protocol control, so these points must not be presented as a field survey." if not es else
                      "Representa en el mapa la predicción calculada de la componente este y su residual observado-menos-predicho en las coordenadas ENU reales. Las entradas son un control de protocolo, por lo que estos puntos no deben presentarse como un levantamiento de campo."),
        "fd_text": ("Check one model direction with a centered finite difference. The exact linear forward operator makes the data objective smooth here; the check validates the assembled derivative at this parameter point." if not es else
                    "Verifica una dirección del modelo con diferencia finita centrada. El operador directo lineal hace suave el objetivo de datos aquí; la verificación comprueba la derivada ensamblada en este punto paramétrico."),
        "score_text": ("Freeze the model bytes first, then score only fold 0 validation rows. The result contains aggregate diagnostics, the model hash and geometry seal, but no observation, prediction or residual vectors." if not es else
                       "Congela primero los bytes del modelo y luego evalúa solo las filas de validación del pliegue 0. El resultado contiene métricas agregadas, el hash del modelo y el sello geométrico, pero no vectores de observaciones, predicciones o residuales."),
        "summary": ("## Summary\n\n" if not es else "## Resumen\n\n"),
        "summary_text": ("You have reproduced one physics-backed fit objective and one frozen-model validation score with explicit row provenance. "
                         "No beta search, IRLS loop, final refit, outer evaluation, result bundle, field-source acceptance or inverse model is produced. "
                         "The zero observations and authored geometry are protocol controls, not scientific accuracy evidence." if not es else
                         "Has reproducido un objetivo de ajuste basado en física y una puntuación de validación para un modelo congelado, con "
                         "procedencia explícita de filas. No se ejecuta búsqueda de beta, ciclo IRLS, reajuste final, evaluación externa, paquete "
                         "de resultados, aceptación de fuente de campo ni modelo inverso. Las observaciones nulas y la geometría creada son controles del protocolo, no evidencia de precisión científica."),
        "refs": ("## References\n\n- SimPEG potential-field framework and inversion methodology: https://doi.org/10.1016/j.cageo.2015.09.015\n"
                 "- Implemented operator: `data-pipeline/magnetic_forward.py`; objective: `data-pipeline/magnetic_objective.py`; fold scorer: `data-pipeline/magnetic_fold_score.py`." if not es else
                "## Referencias\n\n- Marco de campos potenciales y metodología de inversión SimPEG: https://doi.org/10.1016/j.cageo.2015.09.015\n"
                "- Operador implementado: `data-pipeline/magnetic_forward.py`; objetivo: `data-pipeline/magnetic_objective.py`; evaluador de pliegues: `data-pipeline/magnetic_fold_score.py`."),
    }
    code = [
        "# Import the closed survey, actual objective assembly and development-fold scorer.\n"
        "from pathlib import Path\nimport sys\nimport numpy as np\n\n"
        "ROOT = Path.cwd()\nwhile not (ROOT / 'data-pipeline').is_dir():\n    ROOT = ROOT.parent\n"
        "sys.path[:0] = [str(ROOT / 'data-pipeline'), str(ROOT / 'tests' / 'data')]\n"
        "from magnetic_survey_support import encode, rehash, request\n"
        "from magnetic_survey_json import parse_request\n"
        "from magnetic_survey import plan_geometry\n"
        "from magnetic_fit_assembly import assemble_magnetic_fit_objective\n"
        "from magnetic_fold_score import model_q_sha256, score_magnetic_validation_fold\n",
        "# Create an authored protocol request with a nonzero start model and rebind its descriptor hash.\n"
        "survey = request()\nsurvey['prior']['start_si']['data'] = [0.002] * len(survey['prior']['start_si']['data'])\n"
        "rehash(survey, 'prior/start_si')\nhandle = parse_request(encode(survey))\n"
        "plan = plan_geometry(handle)\nmeta = handle.metadata()\n"
        "fit = np.asarray(plan['partition']['folds'][0]['fit_rows']['data'], dtype=np.int64)\n"
        "validation = np.asarray(plan['partition']['folds'][0]['validation_rows']['data'], dtype=np.int64)\n"
        "outer = np.asarray(plan['partition']['outer_rows']['data'], dtype=np.int64)\n"
        "assert not (set(fit) & set(validation) or set(fit) & set(outer) or set(validation) & set(outer))\n"
        "print('rows:', {'fit': len(fit), 'validation': len(validation), 'outer': len(outer),\n"
        "               'fit_validation_overlap': len(set(fit) & set(validation)),\n"
        "               'fit_outer_overlap': len(set(fit) & set(outer))})\n",
        "# Build the actual fold-scoped SimPEG/Geoana kernel, Gaussian term and WLS regularizer.\n"
        "assembled = assemble_magnetic_fit_objective(handle, 0)\nq = assembled['start_q']\n"
        "fit_eval = assembled['objective'].evaluate(q)\nreg_eval = assembled['regularizer'].evaluate(q)\n"
        "print({'quantity': assembled['quantity'], 'fit_receivers': len(assembled['fit_rows']),\n"
        "       'active_cells': len(q), 'chi_start_si': float(q[0] * 0.01),\n"
        "       'phi_d': fit_eval['phi_d'], 'phi_m': reg_eval['phi'],\n"
        "       'gradient_inf_q': float(np.linalg.norm(fit_eval['gradient_q'], ord=np.inf)),\n"
        "       'claim': assembled['claim']})\n",
        "# Plot physical fit-station coordinates and computed E-component fit values in nT.\n"
        "import matplotlib.pyplot as plt\n"
        "xyz = np.asarray(meta['geometry']['receivers_m']['data'], dtype=np.float64).reshape(-1, 3)[assembled['fit_rows']]\n"
        "pred = fit_eval['predicted_selected_nT'].reshape(-1, 3)\n"
        "resid = fit_eval['residual_observed_minus_predicted_nT'].reshape(-1, 3)\n"
        "fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)\n"
        "for ax, values, title in zip(axes, (pred[:, 0], resid[:, 0]),\n"
        "        ('Predicted east component', 'Observed minus predicted east residual')):\n"
        "    image = ax.scatter(xyz[:, 0], xyz[:, 1], c=values, s=34, cmap='coolwarm', edgecolors='0.15', linewidths=.25)\n"
        "    ax.set(title=title, xlabel='Easting (m)', ylabel='Northing (m)', aspect='equal')\n"
        "    fig.colorbar(image, ax=ax, label='nT')\n"
        "fig.suptitle('Authored protocol control · fit rows only · not field observations')\nplt.show()\n",
        "# Compare the analytic objective gradient with a centered difference along one q coordinate.\n"
        "direction = np.zeros_like(q)\ndirection[0] = 1.0\nstep = 1e-5\n"
        "phi_plus = assembled['objective'].evaluate(q + step * direction)['phi_d']\n"
        "phi_minus = assembled['objective'].evaluate(q - step * direction)['phi_d']\n"
        "fd = (phi_plus - phi_minus) / (2 * step)\n"
        "analytic = float(fit_eval['gradient_q'] @ direction)\n"
        "print({'central_difference': fd, 'analytic_directional_derivative': analytic,\n"
        "       'absolute_difference': abs(fd - analytic)})\n"
        "assert np.isclose(fd, analytic, rtol=2e-5, atol=2e-6)\n",
        "# Freeze canonical model bytes before asking the isolated validation scorer for aggregate metrics.\n"
        "frozen_hash = model_q_sha256(q)\n"
        "score = score_magnetic_validation_fold(handle, 0, q, frozen_hash)\n"
        "print(score)\nassert score['candidate_selection_performed'] is False\n"
        "assert score['outer_evaluation_performed'] is False\n",
    ]
    code_comments = [
        ("Importa el protocolo cerrado, el ensamblador real del objetivo y el evaluador de validación." if es else None),
        ("Crea una solicitud de protocolo con un modelo inicial no nulo y actualiza el hash del descriptor." if es else None),
        ("Ensambla el kernel SimPEG/Geoana del pliegue, el término gaussiano y el regularizador WLS reales." if es else None),
        ("Grafica las coordenadas físicas de ajuste y los valores calculados de la componente E en nT." if es else None),
        ("Compara el gradiente analítico con una diferencia centrada en una coordenada de q." if es else None),
        ("Congela los bytes canónicos del modelo antes de pedir métricas agregadas al evaluador aislado." if es else None),
    ]
    if es:
        # Preserve executable cells while translating their leading explanation comments.
        code = ["# " + comment + "\n" + cell.split("\n", 1)[1]
                for comment, cell in zip(code_comments, code)]

    cells = [_cell("markdown", f"# {translated['title']}\n\n{translated['question']}\n\n{translated['prereq']}\n"),
             _cell("markdown", translated["objectives"] + translated["objective_text"]),
             _cell("markdown", translated["setup"] + translated["setup_text"] + "\n"),
             _cell("markdown", translated["imports"]), _cell("code", code[0]),
             _cell("markdown", translated["data"] + translated["data_text"] + "\n"),
             _cell("code", code[1]),
             _cell("markdown", translated["method"] + translated["method_text"]),
             _cell("markdown", translated["state"] + translated["state_text"]),
             _cell("markdown", translated["results"] + translated["results_text"]),
             _cell("markdown", translated["assemble_text"]), _cell("code", code[2]),
             _cell("markdown", translated["plot_text"]), _cell("code", code[3]),
             _cell("markdown", translated["fd_text"]), _cell("code", code[4]),
             _cell("markdown", translated["score_text"]), _cell("code", code[5]),
             _cell("markdown", translated["summary"] + translated["summary_text"]),
             _cell("markdown", translated["refs"])]
    ref = json.loads(REFERENCE.read_text(encoding="utf-8"))
    topic = "03-magnetics"
    title = translated["title"].split(" — ", 1)[1]
    path = ROOT / f"notebooks/{language}/{topic}/04-m04-fit-objective-validation.ipynb"
    notebook = {"cells": cells, "metadata": {
        "kernelspec": ref["metadata"]["kernelspec"],
        "language_info": ref["metadata"]["language_info"],
        "caos": {"language": language, "topic": topic, "level": 3, "title": title,
                 "packages": [], "data": [
                     "data-pipeline/magnetic_fit_assembly.py",
                     "data-pipeline/magnetic_fold_score.py",
                     "data-pipeline/magnetic_forward.py",
                     "data-pipeline/magnetic_objective.py",
                     "data-pipeline/magnetic_regularization.py",
                     "tests/fixtures/magnetic_survey/generate.py",
                     "docs/design/features/m04-survey-inversion/validation.md"],
                 "sources": ["https://doi.org/10.1016/j.cageo.2015.09.015"], "beyond": []}},
        "nbformat": 4, "nbformat_minor": 5}
    path.write_text(json.dumps(notebook, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    return path


def main():
    for lang in ("en", "es"):
        print(_notebook(lang))


if __name__ == "__main__":
    main()
