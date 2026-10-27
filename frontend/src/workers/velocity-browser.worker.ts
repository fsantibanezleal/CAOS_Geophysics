import { parseAndCalculateVelocity, velocityRequestWithLambda } from "../api/velocity-browser";

self.onmessage = async (event: MessageEvent<{ sourceBytes: ArrayBuffer; lambda: number }>) => {
  try {
    const sourceBytes = new Uint8Array(event.data.sourceBytes);
    const requestBytes = velocityRequestWithLambda(sourceBytes, event.data.lambda);
    const result = parseAndCalculateVelocity(requestBytes);
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
