import { parseAndCalculateVelocity } from "../api/velocity-browser";

self.onmessage = async (event: MessageEvent<ArrayBuffer>) => {
  try {
    const bytes = new Uint8Array(event.data);
    const result = parseAndCalculateVelocity(bytes);
    const inputSha256 = [...new Uint8Array(await crypto.subtle.digest("SHA-256", bytes))]
      .map(value => value.toString(16).padStart(2, "0")).join("");
    self.postMessage({ ok: true, result, inputSha256, inputBytes: bytes.byteLength });
  } catch {
    self.postMessage({ ok: false, error: "Request rejected or calculation failed. Check schema, units, ray geometry and parameter bounds." });
  }
};
