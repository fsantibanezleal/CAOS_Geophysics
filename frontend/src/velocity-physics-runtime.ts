import wasmUrl from "../node_modules/onnxruntime-web/dist/ort-wasm-simd-threaded.wasm?url";

export const M12_ONNX_SHA256 = "92e5a3cc5bc70d81c122a1d64c2b4bd722eed47cfa55e2f2473f755cf499f261";
export const M12_CHECKPOINT_SHA256 = "23d51c42b079f37c85fe77796556962e9b7f4f2fe179650a329641a6faa9ded1";

export interface M12VelocitySession {
  infer(features: Float32Array): Promise<Float32Array>;
  release(): Promise<void>;
}

/** Load the frozen M12 artifact in WebAssembly; no inference request leaves this browser. */
export async function createM12VelocitySession(modelBytes: ArrayBuffer): Promise<M12VelocitySession> {
  const ort = await import("onnxruntime-web/wasm");
  ort.env.wasm.numThreads = 1;
  ort.env.wasm.wasmPaths = { wasm: wasmUrl };
  const session = await ort.InferenceSession.create(new Uint8Array(modelBytes), {
    executionProviders: ["wasm"],
  });
  const input = session.inputNames[0];
  const output = session.outputNames[0];
  if (session.inputNames.length !== 1 || input !== "features"
      || session.outputNames.length !== 1 || output !== "velocity_m_s") {
    await session.release();
    throw new Error("M12 ONNX graph must expose the frozen feature and velocity tensors");
  }
  return {
    async infer(features) {
      if (features.length !== 512 || features.some(value => !Number.isFinite(value)))
        throw new Error("M12 feature tensor has invalid shape or values");
      const tensor = new ort.Tensor("float32", features, [1, 2, 16, 16]);
      const values = await session.run({ features: tensor });
      const result = values.velocity_m_s;
      if (!result || result.type !== "float32" || !(result.data instanceof Float32Array)
          || result.dims.join(",") !== "1,16,16")
        throw new Error("M12 ONNX output must be one 16 by 16 float32 velocity field");
      return result.data;
    },
    release: () => session.release(),
  };
}
