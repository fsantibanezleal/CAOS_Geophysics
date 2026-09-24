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
      en: "Physical models",
      es: "Modelos físicos",
      svg: diagram1,
      body_en:
        "Potential fields use 3D property volumes, MT uses resistivity layers, and seismic uses 2D velocity sections. Each result contains the known model, measured response, inverse solution and residuals. Joint and learned methods operate on these specified physical targets.",
      body_es:
        "Campos potenciales usan volúmenes 3D, MT capas de resistividad y sísmica secciones 2D de velocidad. Cada resultado contiene modelo conocido, respuesta observada, solución inversa y residuos. Métodos conjuntos y aprendidos operan sobre esos objetivos físicos.",
    },
    {
      id: "lanes",
      en: "Compute and replay",
      es: "Cálculo y reproducción",
      svg: diagram2,
      body_en:
        "Local SimPEG/SciPy and CUDA PyTorch/Deepwave produce canonical artifacts. Both public hosts serve the same static files. Browsers render those arrays and run a parity-tested layered-earth impedance calculator. Wave propagation and network training execute locally, not on either static host.",
      body_es:
        "SimPEG/SciPy local y PyTorch/Deepwave CUDA producen artefactos. Ambos hosts sirven los mismos archivos. El navegador representa arreglos y ejecuta una calculadora de impedancia validada por paridad. Propagación de ondas y entrenamiento se ejecutan localmente, no en los hosts estáticos.",
    },
    {
      id: "flow",
      en: "Interaction flow",
      es: "Flujo de interacción",
      svg: diagram3,
      body_en:
        "Case, experiment and method select a computed result. Camera controls change the view, not geology. Wave playback advances acoustic time; inversion playback advances recorded solver states. Amplitude gain changes display clipping only. Export preserves the full numerical record.",
      body_es:
        "Caso, experimento y método seleccionan un resultado calculado. La cámara cambia vista, no geología. Ondas avanzan tiempo acústico; inversión avanza estados guardados. Ganancia sólo cambia saturación visual. Exportar conserva el registro numérico.",
    },
    {
      id: "science",
      en: "Scientific workflow",
      es: "Flujo científico",
      svg: diagram4,
      body_en:
        "Construct geology, configure acquisition, solve forward, add seeded noise, mask observations, invert, compare with known truth, export and validate. Neural models use separate realization seeds for training, validation and test. Model error and data misfit are reported separately, with their units and evaluation populations.",
      body_es:
        "Construir geología, configurar adquisición, resolver, agregar ruido sembrado, enmascarar, invertir, comparar, exportar y validar. Redes usan semillas distintas para entrenamiento, validación y prueba. Error de modelo y desajuste de datos se informan por separado, con unidades y poblaciones evaluadas.",
    },
    {
      id: "contracts",
      en: "Data contracts",
      es: "Contratos de datos",
      svg: diagram5,
      body_en:
        "CSV ingestion checks five named columns, finite values, positive uncertainties and duplicate coordinates. External tutorial archives are checked by SHA-256 and remain local. Release validation checks every result identity, finite values, hashes, sizes, model weights and catalogue completeness.",
      body_es:
        "Ingesta CSV verifica cinco columnas, finitud, incertidumbres positivas y coordenadas duplicadas. Archivos externos se verifican SHA-256 y permanecen locales. Validación de release revisa identidad, valores, hashes, tamaños, pesos y catálogo completo.",
    },
  ],
};
