import { defineConfig } from "@playwright/test";
const run = process.env.M01_COURSE_QA_RUN ?? "run-01";
if (!/^[a-z0-9-]+$/.test(run)) throw new Error("Invalid owned QA run name");

export default defineConfig({
  testDir: "./e2e", testMatch: "m01-scientific-course.spec.ts", workers: 1,
  timeout: 180_000, expect: { timeout: 15_000 },
  outputDir: `./node_modules/.m01-course-qa/${run}/results`,
  reporter: [["list"], ["json", { outputFile: `node_modules/.m01-course-qa/${run}/report.json` }]],
  use: { baseURL: "http://127.0.0.1:4338", channel: "msedge", trace: "retain-on-failure" },
  webServer: { command: "npm run dev -- --port 4338 --strictPort", url: "http://127.0.0.1:4338", reuseExistingServer: false, timeout: 60_000 },
});
