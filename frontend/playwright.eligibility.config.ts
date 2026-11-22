import { defineConfig } from "@playwright/test";
import { resolve, join } from "node:path";
import { tmpdir } from "node:os";

const python = process.env.GEOPHYSICS_QA_PYTHON ?? resolve("../.venv-api/Scripts/python.exe");

export default defineConfig({
  testDir: "./e2e", testMatch: "eligibility.spec.ts", workers: 1,
  timeout: 60_000, expect: { timeout: 15_000 },
  outputDir: "./node_modules/.eligibility-qa/test-results",
  use: { baseURL: "http://127.0.0.1:8877", viewport: { width: 1440, height: 900 }, trace: "retain-on-failure" },
  webServer: {
    command: `"${python}" "${resolve("../tests/ui/processing_devserver.py")}"`,
    cwd: resolve(".."), url: "http://127.0.0.1:8877/__qa/processing",
    reuseExistingServer: false, timeout: 60_000,
    env: { PYTHONPATH: resolve(".."), GEOPHYSICS_QA_PORT: "8877",
      GEOPHYSICS_QA_ROOT: join(tmpdir(), "caos-geophysics-eligibility-qa") },
  },
});
