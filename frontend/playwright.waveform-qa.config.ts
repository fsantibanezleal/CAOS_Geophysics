import { defineConfig } from "@playwright/test";
import { existsSync } from "node:fs";
import { dirname, isAbsolute, resolve } from "node:path";
const value=process.env.GEOPHYSICS_QA_EVIDENCE;
if(!value||!isAbsolute(value))throw new Error("Select explicit external GEOPHYSICS_QA_EVIDENCE");
const root=resolve(value);
for(let parent=root;;parent=dirname(parent)){
  if(existsSync(resolve(parent,".git")))throw new Error("QA evidence must be outside checkouts");
  if(parent===dirname(parent))break;
}
const layout=process.env.GEOPHYSICS_QA_SCOPE==="layout-only";
export default defineConfig({testDir:"e2e",testMatch:layout?"waveform-layout.spec.ts":"waveform-workbench.spec.ts",workers:1,timeout:120000,
  outputDir:resolve(root,"test-results"),reporter:[["list"],["json",{outputFile:resolve(root,"report.json")}]],
  use:{headless:true,acceptDownloads:true,trace:"retain-on-failure",screenshot:"only-on-failure"},
});
