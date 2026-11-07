import { defineConfig } from "@playwright/test";
export default defineConfig({testDir:"./e2e",testMatch:"local-profile-results.spec.ts",workers:1,
  timeout:120000,expect:{timeout:30000},outputDir:process.env.GEOPHYSICS_PROFILE_QA_OUTPUT,
  use:{headless:true,trace:"retain-on-failure"}});
