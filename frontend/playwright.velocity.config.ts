import { defineConfig } from "@playwright/test";
import { fileURLToPath } from "node:url";
import { courseQaPaths } from "./e2e/m01-course-output";

// Reuse the checked external-path guard; no evidence beneath node_modules.
const output = courseQaPaths(process.env.GEOPHYSICS_VELOCITY_QA_OUTPUT,
  process.env.GEOPHYSICS_VELOCITY_QA_RUN ?? "run-01",
  fileURLToPath(new URL("../", import.meta.url)), "GEOPHYSICS_VELOCITY_QA_OUTPUT");

export default defineConfig({
  testDir: "./e2e", testMatch: "local-velocity-results.spec.ts", workers: 1,
  timeout: 240_000, expect: { timeout: 30_000 }, outputDir: output.results,
  reporter: [["list"], ["json", { outputFile: output.report }]],
  use: { channel: "msedge", trace: "retain-on-failure" },
});
