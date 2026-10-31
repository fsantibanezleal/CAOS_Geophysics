import { defineConfig } from "@playwright/test";
import { resolve, join } from "node:path";
import { tmpdir } from "node:os";
export default defineConfig({
  testDir: "./e2e", testMatch: "processing-workbench.spec.ts", workers: 1,
  timeout: 120_000, expect: {timeout: 30_000}, outputDir: "./node_modules/.processing-qa/test-results",
  use: {baseURL: "http://127.0.0.1:8876", viewport: {width: 1440, height: 900}, trace: "retain-on-failure"},
  webServer: {command: `"${resolve("../.venv-api/Scripts/python.exe")}" "${resolve("../tests/ui/processing_devserver.py")}"`, cwd: resolve(".."), url: "http://127.0.0.1:8876/__qa/processing", reuseExistingServer: false, timeout: 60_000,
    env: {PYTHONPATH: resolve(".."), GEOPHYSICS_QA_PORT: "8876",
      GEOPHYSICS_QA_ROOT: join(tmpdir(), "caos-geophysics-processing-qa")}},
});
