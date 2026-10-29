import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  testMatch: "local-access.spec.ts",
  grep: /(invalid login clears secret|anonymous browser MT forward calculator|unknown\/unavailable profiles fail private closed|direct private project and MT URLs deny guests|closing a pending probe prevents late owner restoration|inactive account receives no private controls)/,
  workers: 1,
  timeout: 120_000,
  expect: { timeout: 15_000 },
  reporter: "line",
  use: { browserName: "chromium", headless: true },
  webServer: {
    command: "npm run preview -- --host 127.0.0.1 --port 8899 --strictPort",
    url: "http://127.0.0.1:8899/",
    reuseExistingServer: false,
    timeout: 30_000,
  },
});
