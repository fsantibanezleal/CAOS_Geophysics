import { defineConfig } from "@playwright/test";
import { isAbsolute, join, relative, resolve, sep } from "node:path";
import { tmpdir } from "node:os";
const backend=process.env.GEOPHYSICS_MT_QA_BACKEND_ROOT, python=process.env.GEOPHYSICS_MT_QA_PYTHON;
if(!backend||!python)throw new Error("Explicit read-only MT backend and interpreter paths required");
const outputDir=resolve(process.env.GEOPHYSICS_MT_QA_OUTPUT??join(tmpdir(),"caos-geophysics-mt-qa-test-results"));
const outputRelative=relative(resolve(".."),outputDir);
if(!isAbsolute(outputDir)||!outputRelative||outputRelative===".."||outputRelative.startsWith(`..${sep}`))throw new Error("MT Playwright output must be outside the repository checkout");
export default defineConfig({
  testDir:"./e2e",testMatch:"mt-workbench.spec.ts",workers:1,timeout:240000,expect:{timeout:60000},outputDir,
  use:{baseURL:"http://127.0.0.1:8877",viewport:{width:1600,height:900},trace:"retain-on-failure"},
  webServer:{command:`"${python}" -B "${resolve("../tests/ui/mt_devserver.py")}"`,cwd:resolve(".."),url:"http://127.0.0.1:8877/__qa/mt",timeout:60000,reuseExistingServer:false,
    env:{GEOPHYSICS_MT_QA_BACKEND_ROOT:backend,GEOPHYSICS_MT_QA_ROOT:process.env.GEOPHYSICS_MT_QA_ROOT??join(tmpdir(),"caos-geophysics-mt-qa"),PYTHONDONTWRITEBYTECODE:"1",GEOPHYSICS_MT_QA_ENABLE:process.env.GEOPHYSICS_MT_QA_ENABLE??"",GEOPHYSICS_MT_QA_PORT:"8877"}},
});
