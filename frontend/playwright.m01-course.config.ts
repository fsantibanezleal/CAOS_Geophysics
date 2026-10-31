import { defineConfig } from "@playwright/test";
import { fileURLToPath } from "node:url";
import { courseQaPaths } from "./e2e/m01-course-output";
const run = process.env.M01_COURSE_QA_RUN ?? "run-01";
const output = courseQaPaths(process.env.M01_COURSE_QA_OUTPUT, run, fileURLToPath(new URL("../", import.meta.url)));

export default defineConfig({
  testDir: "./e2e", testMatch: "m01-scientific-course.spec.ts", workers: 1,
  timeout: 180_000, expect: { timeout: 15_000 },
  outputDir: output.results,
  reporter: [["list"], ["json", { outputFile: output.report }]],
  use: { baseURL: "http://127.0.0.1:4338", channel: "msedge", trace: "retain-on-failure" },
  webServer: { command: "npm run dev -- --port 4338 --strictPort", url: "http://127.0.0.1:4338", reuseExistingServer: false, timeout: 60_000 },
});
