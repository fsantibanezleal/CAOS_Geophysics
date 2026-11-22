import { defineConfig } from "@playwright/test";
import { fileURLToPath } from "node:url";
import { courseQaPaths } from "./e2e/m01-course-output";
const output = courseQaPaths(process.env.MAGNETIC_THEORY_QA_OUTPUT,
  process.env.MAGNETIC_THEORY_QA_RUN ?? "run-01",
  fileURLToPath(new URL("../", import.meta.url)), "MAGNETIC_THEORY_QA_OUTPUT");
if (!process.env.MAGNETIC_THEORY_QA_BUILD) throw new Error("Supply exact existing MAGNETIC_THEORY_QA_BUILD");
export default defineConfig({
  testDir: "./e2e", testMatch: "magnetic-theory.spec.ts", workers: 1,
  timeout: 180_000, expect: { timeout: 15_000 }, outputDir: output.results,
  reporter: [["list"], ["json", { outputFile: output.report }]],
  use: { baseURL: "http://127.0.0.1:4339", channel: "msedge", trace: "retain-on-failure" },
  webServer: { command: `node node_modules/vite/bin/vite.js preview --outDir "${process.env.MAGNETIC_THEORY_QA_BUILD}" --host 127.0.0.1 --port 4339 --strictPort`,
    url: "http://127.0.0.1:4339", reuseExistingServer: false, timeout: 60_000 },
});
