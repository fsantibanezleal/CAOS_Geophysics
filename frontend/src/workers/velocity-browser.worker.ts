import { calculateM12PhysicsInBrowser, parseAndCalculateVelocity, velocityRequestWithLambda } from "../api/velocity-browser";
import { artifactBase, deploymentMode } from "../lib/deployment";
import { createM12VelocitySession, M12_CHECKPOINT_SHA256, M12_ONNX_SHA256 } from "../velocity-physics-runtime";

async function loadM12Model() {
  const base = artifactBase(deploymentMode, self.location.pathname);
  const receiptResponse = await fetch(`${base}data/models/m12-physics-v2/m12-physics-browser-receipt.json`, { cache: "force-cache" });
  if (!receiptResponse.ok)
    throw new Error("M12 model receipt is unavailable");
  const receiptBytes = await receiptResponse.arrayBuffer();
  if (receiptBytes.byteLength < 1 || receiptBytes.byteLength > 65536)
    throw new Error("M12 model receipt exceeds its size limit");
  const receipt = JSON.parse(new TextDecoder("utf-8", { fatal: true }).decode(receiptBytes)) as Record<string, unknown>;
  const model = receipt.model as Record<string, unknown> | undefined;
  const checkpoint = receipt.checkpoint as Record<string, unknown> | undefined;
  const training = receipt.training as Record<string, unknown> | undefined;
  const parity = receipt.parity as Record<string, unknown> | undefined;
  if (receipt.schema !== "geophysics.m12-browser-model/v1" || receipt.status !== "parity-verified"
      || model?.file !== "m12-physics.onnx" || model.sha256 !== M12_ONNX_SHA256
      || checkpoint?.sha256 !== M12_CHECKPOINT_SHA256 || typeof model.bytes !== "number"
      || training?.scientific_verdict !== "failed-held-out-comparator"
      || parity?.passed !== true || parity.max_absolute_error_m_s !== 0.00048828125)
    throw new Error("M12 model receipt does not match the pinned experiment");
  const response = await fetch(`${base}data/models/m12-physics-v2/m12-physics.onnx`, { cache: "force-cache" });
  if (!response.ok) throw new Error("M12 ONNX model is unavailable");
  const modelBytes = await response.arrayBuffer();
  if (modelBytes.byteLength < 1 || modelBytes.byteLength > 1024 * 1024
      || model.bytes !== modelBytes.byteLength)
    throw new Error("M12 model size differs from its receipt");
  const digest = [...new Uint8Array(await crypto.subtle.digest("SHA-256", modelBytes))]
    .map(value => value.toString(16).padStart(2, "0")).join("");
  if (digest !== M12_ONNX_SHA256) throw new Error("M12 model integrity check failed");
  return { session: await createM12VelocitySession(modelBytes), digest };
}

self.onmessage = async (event: MessageEvent<{ sourceBytes: ArrayBuffer; lambda: number; includeM12?: boolean }>) => {
  try {
    const sourceBytes = new Uint8Array(event.data.sourceBytes);
    const requestBytes = velocityRequestWithLambda(sourceBytes, event.data.lambda);
    const result = parseAndCalculateVelocity(requestBytes);
    if (event.data.includeM12) {
      const { session, digest } = await loadM12Model();
      try {
        result.learned = await calculateM12PhysicsInBrowser(result.request, features => session.infer(features), {
          checkpointSha256: M12_CHECKPOINT_SHA256,
          onnxSha256: digest,
        });
      } finally {
        await session.release();
      }
    }
    const inputSha256 = [...new Uint8Array(await crypto.subtle.digest("SHA-256", sourceBytes.slice().buffer))]
      .map(value => value.toString(16).padStart(2, "0")).join("");
    const requestSha256 = [...new Uint8Array(await crypto.subtle.digest("SHA-256", requestBytes.slice().buffer))]
      .map(value => value.toString(16).padStart(2, "0")).join("");
    self.postMessage({ ok: true, result, inputSha256, inputBytes: sourceBytes.byteLength,
      requestSha256, requestBytes: requestBytes.byteLength });
  } catch {
    self.postMessage({ ok: false, error: "Request rejected or calculation failed. Check schema, units, ray geometry and parameter bounds." });
  }
};
