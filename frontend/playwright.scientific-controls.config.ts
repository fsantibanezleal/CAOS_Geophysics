import { defineConfig } from "@playwright/test";
import { existsSync } from "node:fs";
import { dirname, isAbsolute, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const frontend = dirname(fileURLToPath(import.meta.url));
const root = resolve(frontend, "..");
const evidence = process.env.CAOS_SCIENTIFIC_CONTROLS_OUTPUT;
if (!evidence || !isAbsolute(evidence)) {
  throw new Error("Set CAOS_SCIENTIFIC_CONTROLS_OUTPUT to an absolute path outside every Git checkout.");
}
const output = resolve(evidence);
const fromRoot = relative(root, output);
if (!fromRoot.startsWith("..") && !isAbsolute(fromRoot)) {
  throw new Error("Scientific-controls evidence must be outside the product checkout.");
}
for (let parent = output; ; parent = dirname(parent)) {
  if (existsSync(join(parent, ".git"))) {
    throw new Error("Scientific-controls evidence must be outside every Git checkout.");
  }
  if (parent === dirname(parent)) break;
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: ["selected-case-reactivity.spec.ts", "scientific-views.spec.ts", "animation-controls.spec.ts"],
  fullyParallel: false,
  workers: 1,
  timeout: 90_000,
  expect: { timeout: 20_000 },
  outputDir: resolve(output, "playwright-results"),
  reporter: [["list"], ["json", { outputFile: resolve(output, "playwright-report.json") }]],
  use: {
    baseURL: "http://127.0.0.1:8897",
    viewport: { width: 1440, height: 900 },
    trace: "retain-on-failure",
  },
  webServer: {
    command: "node node_modules/vite/bin/vite.js preview --host 127.0.0.1 --port 8897 --strictPort",
    cwd: frontend,
    url: "http://127.0.0.1:8897/",
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
