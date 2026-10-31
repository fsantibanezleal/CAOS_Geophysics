import { defineConfig } from "@playwright/test";
import { existsSync } from "node:fs";
import { dirname, isAbsolute, join, relative, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const frontend = dirname(fileURLToPath(import.meta.url));
const root = resolve(frontend, "..");
const output = process.env.CAOS_VISUAL_MATRIX_OUTPUT;
if (!output || !isAbsolute(output)) {
  throw new Error("Set CAOS_VISUAL_MATRIX_OUTPUT to an absolute path outside every Git checkout.");
}
const outputPath = resolve(output);
const fromRoot = relative(root, outputPath);
if (!fromRoot.startsWith("..") && !isAbsolute(fromRoot)) {
  throw new Error("Visual-matrix evidence must be outside the product checkout.");
}
for (let parent = outputPath; ; parent = dirname(parent)) {
  if (existsSync(join(parent, ".git"))) {
    throw new Error("Visual-matrix evidence must be outside every Git checkout.");
  }
  if (parent === dirname(parent)) break;
}

export default defineConfig({
  testDir: "./e2e",
  testMatch: "visual-matrix.spec.ts",
  fullyParallel: true,
  workers: 4,
  timeout: 120_000,
  expect: { timeout: 20_000 },
  outputDir: resolve(outputPath, "playwright-results"),
  reporter: [["list"], ["json", { outputFile: resolve(outputPath, "playwright-report.json") }]],
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
