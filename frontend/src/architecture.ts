import type { ArchitectureConfig } from "@fasl-work/caos-app-shell";
import diagram1 from '../public/svg/tech/01-the-app.svg?raw';
import diagram2 from '../public/svg/tech/02-lanes.svg?raw';
import diagram3 from '../public/svg/tech/03-web-flow.svg?raw';
import diagram4 from '../public/svg/tech/04-the-science.svg?raw';
import diagram5 from '../public/svg/tech/05-data-contracts.svg?raw';
export const architecture: ArchitectureConfig = {
  tabs: [
    {
      id: "app",
      en: "The instrument",
      es: "El instrumento",
      svg: diagram1,
      body_en:
        "Twenty geological questions use distinct volumes, layers and sections. Every result keeps the known earth, observations, predicted response and residual separate. No posterior confidence is inferred from a pleasing reconstruction.",
      body_es:
        "Veinte preguntas geológicas usan volúmenes, capas y secciones distintos. Cada resultado separa Tierra conocida, observaciones, predicción y residuo. Una reconstrucción atractiva no implica confianza posterior.",
    },
    {
      id: "lanes",
      en: "Compute and replay",
      es: "Cálculo y reproducción",
      svg: diagram2,
      body_en:
        "Local SimPEG/SciPy and CUDA PyTorch/Deepwave produce canonical artifacts. Both public hosts serve the same static files. Browsers render those arrays and run a parity-tested layered-earth impedance calculator. No remote GPU service is claimed.",
      body_es:
        "SimPEG/SciPy local y PyTorch/Deepwave CUDA producen artefactos. Ambos hosts sirven los mismos archivos. El navegador representa arreglos y ejecuta una calculadora de impedancia validada por paridad. No se anuncia servicio GPU remoto.",
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
        "Construct geology, configure acquisition, solve forward, add seeded noise, mask observations, invert, compare with known truth, export and validate. Neural models use separate realization seeds for training, validation and test. The UI exposes failures and non-uniqueness, not a combined score.",
      body_es:
        "Construir geología, configurar adquisición, resolver, agregar ruido sembrado, enmascarar, invertir, comparar, exportar y validar. Redes usan semillas distintas para entrenamiento, validación y prueba. La UI expone fallos y no unicidad, no un puntaje combinado.",
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
