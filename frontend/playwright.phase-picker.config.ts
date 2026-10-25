import { defineConfig } from "@playwright/test";
import { resolve } from "node:path";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "phase-picker-live.spec.ts",
  workers: 1,
  timeout: 120_000,
  expect: { timeout: 30_000 },
  outputDir: "./node_modules/.phase-picker-qa/test-results",
  reporter: [["list"], ["json", { outputFile: "./node_modules/.phase-picker-qa/report.json" }]],
  use: { baseURL: "http://127.0.0.1:8899", viewport: { width: 1440, height: 1000 }, trace: "retain-on-failure" },
  webServer: {
    command: "npm run preview -- --host 127.0.0.1 --port 8899 --strictPort",
    cwd: resolve("."),
    url: "http://127.0.0.1:8899/",
    reuseExistingServer: false,
    timeout: 60_000,
  },
});
