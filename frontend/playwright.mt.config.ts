import { defineConfig } from "@playwright/test";
import { resolve } from "node:path";
const backend=process.env.GEOPHYSICS_MT_QA_BACKEND_ROOT, python=process.env.GEOPHYSICS_MT_QA_PYTHON;
if(!backend||!python)throw new Error("Explicit read-only MT backend and interpreter paths required");
export default defineConfig({
  testDir:"./e2e",testMatch:"mt-workbench.spec.ts",workers:1,timeout:240000,expect:{timeout:60000},outputDir:"./node_modules/.mt-qa/test-results",
  use:{baseURL:"http://127.0.0.1:8877",viewport:{width:1600,height:900},trace:"retain-on-failure"},
  webServer:{command:`"${python}" -B "${resolve("../tests/ui/mt_devserver.py")}"`,cwd:resolve(".."),url:"http://127.0.0.1:8877/__qa/mt",timeout:60000,reuseExistingServer:false,
    env:{GEOPHYSICS_MT_QA_BACKEND_ROOT:backend,PYTHONDONTWRITEBYTECODE:"1",GEOPHYSICS_MT_QA_ENABLE:process.env.GEOPHYSICS_MT_QA_ENABLE??"",GEOPHYSICS_MT_QA_PORT:"8877"}},
});
