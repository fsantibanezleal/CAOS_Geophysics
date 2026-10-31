import { defineConfig } from "@playwright/test";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { courseQaPaths } from "./e2e/m01-course-output";

const output = courseQaPaths(process.env.GEOPHYSICS_VELOCITY_CALCULATOR_QA_OUTPUT,
  process.env.GEOPHYSICS_VELOCITY_CALCULATOR_QA_RUN ?? "run-01",
  fileURLToPath(new URL("../", import.meta.url)), "GEOPHYSICS_VELOCITY_CALCULATOR_QA_OUTPUT");

export default defineConfig({
  testDir: "./e2e", testMatch: "velocity-browser-calculator.spec.ts", workers: 1,
  timeout: 120_000, expect: { timeout: 20_000 }, outputDir: output.results,
  reporter: [["list"], ["json", { outputFile: output.report }]],
  use: { baseURL: "http://127.0.0.1:4341", viewport: { width: 1440, height: 960 }, trace: "retain-on-failure" },
  webServer: { command: "npm run preview -- --host 127.0.0.1 --port 4341 --strictPort", cwd: resolve("."),
    url: "http://127.0.0.1:4341/", reuseExistingServer: false, timeout: 60_000 },
});
