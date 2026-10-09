import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e", testMatch: "online-mt-course.spec.ts", workers: 1,
  timeout: 120_000, expect: { timeout: 10_000 },
  outputDir: "./node_modules/.mt-course-qa/results",
  reporter: [["list"], ["json", { outputFile: "node_modules/.mt-course-qa/report.json" }]],
  use: { baseURL: "http://127.0.0.1:4337", trace: "retain-on-failure" },
  webServer: { command: "npm run dev -- --port 4337 --strictPort", url: "http://127.0.0.1:4337", reuseExistingServer: false, timeout: 60_000 },
});
