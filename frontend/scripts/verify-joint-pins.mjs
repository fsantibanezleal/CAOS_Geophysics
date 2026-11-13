import { createHash } from "node:crypto";
import { readFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const frontendRoot = dirname(fileURLToPath(import.meta.url)).replaceAll("\\", "/").replace(/\/scripts$/, "");
const repoRoot = resolve(frontendRoot, "..");
const optimizerPath = resolve(repoRoot, "data-pipeline/physical_nonlinear_optimizer.py");
const adapterPath = resolve(repoRoot, "data-pipeline/joint_survey_optimizer.py");
const clientPath = resolve(frontendRoot, "src/api/joint-result.ts");
const [optimizerBytes, adapterBytes, clientBytes] = await Promise.all([
  readFile(optimizerPath), readFile(adapterPath, "utf8"), readFile(clientPath, "utf8"),
]);
const optimizerSha = createHash("sha256").update(optimizerBytes).digest("hex");
const adapter = adapterBytes.match(/^SOLVER_SHA='([a-f0-9]{64})'\s*\nVENDOR_SHA='([a-f0-9]{64})'/m);
const client = clientBytes.match(/export const JOINT_CLIENT_PINS = Object\.freeze\(\{\s*optimizer_source_sha256: "([a-f0-9]{64})",\s*vendor_source_sha256: "([a-f0-9]{64})",\s*runtime_epoch: "([^"]+)"/);
if (!adapter || !client) throw new Error("M11 source pin declarations changed shape; review all three sources");
const expectedVendor = adapter[2];
const clientPins = { optimizer: client[1], vendor: client[2] };
if (adapter[1] !== optimizerSha || clientPins.optimizer !== optimizerSha || clientPins.vendor !== expectedVendor) {
  throw new Error(JSON.stringify({
    error: "M11 browser/source optimizer pins diverged",
    optimizer_sha256: optimizerSha,
    adapter_sha256: adapter[1],
    browser_optimizer_sha256: clientPins.optimizer,
    adapter_vendor_sha256: expectedVendor,
    browser_vendor_sha256: clientPins.vendor,
  }, null, 2));
}
console.log(`M11 browser pins verified: optimizer=${optimizerSha}, vendor=${expectedVendor}`);
