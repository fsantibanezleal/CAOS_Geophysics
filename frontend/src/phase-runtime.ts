import { PHASE_SAMPLES, validateProbabilities, type PhaseScores, type PhaseTrace } from "./phase-picker";
import wasmUrl from "../node_modules/onnxruntime-web/dist/ort-wasm-simd-threaded.wasm?url";

export interface PhaseSession {
  run(trace: PhaseTrace): Promise<PhaseScores>;
  release(): Promise<void>;
}

/** This imports ORT only when the user loads a model; no server inference is involved. */
export async function createPhaseSession(modelBytes: ArrayBuffer): Promise<PhaseSession> {
  const ort = await import("onnxruntime-web/wasm");
  ort.env.wasm.numThreads = 1;
  ort.env.wasm.wasmPaths = { wasm: wasmUrl };
  const session = await ort.InferenceSession.create(new Uint8Array(modelBytes), { executionProviders: ["wasm"] });
  if (session.inputNames.length !== 1 || session.inputNames[0] !== "waveform" ||
      session.outputNames.length !== 1 || session.outputNames[0] !== "probabilities") {
    await session.release();
    throw new Error("ONNX model must expose waveform input and probabilities output");
  }
  return {
    async run(trace) {
      if (trace.input.length !== 3 * PHASE_SAMPLES) throw new Error("Input tensor has the wrong ENZ length");
      const input = new ort.Tensor("float32", trace.input, [1, 3, PHASE_SAMPLES]);
      const outputs = await session.run({ waveform: input });
      const result = outputs.probabilities;
      if (!result || result.type !== "float32" || !(result.data instanceof Float32Array))
        throw new Error("ONNX output must be float32 probabilities");
      return validateProbabilities(result.data, result.dims);
    },
    release: () => session.release(),
  };
}
