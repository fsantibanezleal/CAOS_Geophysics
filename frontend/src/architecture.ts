import type { ArchitectureConfig } from "@fasl-work/caos-app-shell";
import diagram1 from "../public/svg/tech/01-the-app.svg?raw";
import diagram2 from "../public/svg/tech/02-lanes.svg?raw";
import diagram3 from "../public/svg/tech/03-web-flow.svg?raw";
import diagram4 from "../public/svg/tech/04-the-science.svg?raw";
import diagram5 from "../public/svg/tech/05-data-contracts.svg?raw";
export const architecture: ArchitectureConfig = {
  tabs: [
    {
      id: "app",
      en: "System",
      es: "Sistema",
      svg: diagram1,
      body_en:
        "Approved target: one selected project moves from a rights-aware source through immutable raw bytes, a versioned observation dataset, method eligibility and a recorded solver job to a typed result. Field results contain observed and predicted data, residuals and interpretation hypotheses; synthetic truth appears only in generated controls. Clear Lake cl061 remains QC-only and cannot enter a 1D inverse without a different eligible station.\n\nThe live 0.04.001 release remains a static synthetic replay on Pages and the ML VPS. This diagram describes the approved target, not a currently available online job service.",
      body_es:
        "Objetivo aprobado: un proyecto elegido pasa de una fuente con derechos conocidos a bytes crudos inmutables, datos observados versionados, aptitud de métodos y una tarea registrada, hasta un resultado tipado. Los resultados de campo contienen datos, predicción, residuos e hipótesis; la verdad conocida sólo existe en controles sintéticos. Clear Lake cl061 sigue apto sólo para QC, no para inversión 1D sin otra estación admisible.\n\nLa versión live 0.04.001 sigue siendo repetición sintética estática en Pages y ML VPS. El diagrama representa el objetivo aprobado, no un servicio de tareas ya disponible.",
    },
    {
      id: "lanes",
      en: "Lanes",
      es: "Rutas",
      svg: diagram2,
      body_en:
        "Approved target: local CPU/GPU runs the complete offline pipeline, full FWI and M12/M13 training. A separate CPU worker on the one ML VPS origin may run only individually benchmarked bounded methods after API admission. The browser inspects typed results and released replay; M13 phase picking on real held-out traces may run in the browser only after numerical parity, latency and memory gates. The host has no server GPU.\n\nLive 0.04.001 has two static origins, Pages and ML VPS. It replays saved synthetic arrays and computes only bounded MT forward curves in the browser; it has no online solver API.",
      body_es:
        "Objetivo aprobado: CPU/GPU local ejecuta el proceso completo, FWI y entrenamiento M12/M13. Un worker CPU separado en el único origen ML VPS podrá ejecutar sólo métodos acotados evaluados individualmente y admitidos por la API. El navegador inspecciona resultados y reproducciones; M13 con trazas reales reservadas sólo podrá funcionar en web tras validar paridad, latencia y memoria. El servidor no tiene GPU.\n\nLive 0.04.001 tiene dos orígenes estáticos, Pages y ML VPS. Reproduce arreglos sintéticos y sólo calcula MT directo acotado en el navegador; no posee API de inversión.",
    },
    {
      id: "flow",
      en: "Flow",
      es: "Flujo",
      svg: diagram3,
      body_en:
        "Approved target: App remains one selected-project workbench under the six shared-shell routes. Source choice, processing, compatible method configuration, admitted job state, evaluation and export are operations inside that workbench. Physical controls must change a genuine computation; display controls change only camera, slice or colour mapping. Ineligible methods expose a reason and offline methods provide a local recipe plus attributable artifact import.\n\nLive 0.04.001 selects a precomputed case/variant and replays its saved arrays. No project drawer, job queue or server-side solve is online in that release.",
      body_es:
        "Objetivo aprobado: App sigue siendo banco de un proyecto elegido bajo seis rutas compartidas. Fuente, proceso, configuración de método compatible, estado de tarea, evaluación y exportación operan dentro de ese banco. Controles físicos deben cambiar un cálculo real; controles de vista sólo cambian cámara, corte o color. Métodos no aptos explican el motivo y los locales ofrecen receta ejecutable e importación atribuible.\n\nLive 0.04.001 elige caso y variante calculados y reproduce arreglos guardados. Esa versión no ofrece proyectos, cola de tareas ni cálculo remoto.",
    },
    {
      id: "science",
      en: "Science",
      es: "Ciencia",
      svg: diagram4,
      body_en:
        "Approved target: M01–M13 each need an independent numerical or physical oracle and a visible negative control. Synthetic controls use known truth with a distinct forward discretization; field studies use withheld observations and never assert a true subsurface volume. M12 learned velocity inversion requires family-disjoint tests and forward consistency. M13 learned P/S picking requires event/station-disjoint real traces and a same-input M08 classical comparator, with browser export held behind parity.\n\nLive 0.04.001 contains synthetic method results and bounded EDI screening, not this complete field and learned-method ladder.",
      body_es:
        "Objetivo aprobado: M01–M13 requieren criterio físico o numérico independiente y control negativo visible. Los controles sintéticos usan verdad conocida con discretización directa distinta; los estudios de campo reservan observaciones y nunca afirman volumen verdadero. M12 de velocidad aprendida exige familias disjuntas y consistencia directa. M13 de fases P/S exige trazas reales separadas por evento/estación y comparación clásica M08 con la misma entrada; su exportación web espera paridad.\n\nLive 0.04.001 contiene resultados sintéticos y filtro EDI acotado, no esta escala completa de métodos de campo y aprendizaje.",
    },
    {
      id: "contracts",
      en: "Data",
      es: "Datos",
      svg: diagram5,
      body_en:
        "Approved target: SourceRecord captures provider, rights decision, URL or upload and SHA-256; RawAsset keeps immutable owned bytes; ObservationDataset versions physical axes, CRS or local frame, units, geometry, masks, uncertainties and parser lineage. ProcessingRun records transforms. SolverJob records method, lane, admission, state and measured resources. ResultArtifact binds observed/predicted/residual arrays, model, coverage, rights and file hashes; field truth is absent. Clear Lake cl061 is QC-only because its present dimensionality screen rejects 1D eligibility.\n\nLive 0.04.001 reads the separate v2 static JSON and EDI screen. The typed API mirror is a frontend foundation; no upload or job API is online from it.",
      body_es:
        "Objetivo aprobado: SourceRecord registra proveedor, derechos, URL o carga y SHA-256; RawAsset conserva bytes originales propios; ObservationDataset versiona ejes, CRS o marco local, unidades, geometría, máscaras, incertidumbre y linaje. ProcessingRun registra transformaciones. SolverJob registra método, ruta, admisión, estado y recursos. ResultArtifact liga datos observados, predichos, residuos, modelo, cobertura, derechos y hashes; no hay verdad de campo. Clear Lake cl061 sólo admite QC porque su filtro dimensional actual rechaza inversión 1D.\n\nLive 0.04.001 lee JSON v2 y filtro EDI estáticos por separado. El contrato API tipado es una base web; no habilita carga ni tareas en línea.",
    },
  ],
};
