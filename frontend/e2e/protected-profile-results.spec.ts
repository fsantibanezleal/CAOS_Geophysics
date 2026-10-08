import { test, expect } from "@playwright/test";
import { spawn, execFileSync } from "node:child_process";
import { createServer } from "node:net";
import { readFileSync, mkdirSync, writeFileSync } from "node:fs";
import { resolve, join } from "node:path";

// Real canonical result bytes and real authenticated API. No API interception
// and no solver replay during rendering. Native execution is a separate gate.
const required=(key:string)=>{if(!process.env[key])throw new Error(`Supply ${key}`);return resolve(process.env[key]!);};
const python=required("GEOPHYSICS_REVIEW_PYTHON"),build=required("GEOPHYSICS_PROFILE_BUILD"),evidence=required("GEOPHYSICS_PROFILE_EVIDENCE");
const cases=[{name:"ert",root:required("GEOPHYSICS_PROFILE_QA_ERT_CASE"),receipt:required("GEOPHYSICS_PROFILE_JOB_ERT")},
  {name:"traveltime",root:required("GEOPHYSICS_PROFILE_QA_TRAVELTIME_CASE"),receipt:required("GEOPHYSICS_PROFILE_JOB_TRAVELTIME")}];

test("owned_result_roundtrip",async({browser})=>{
  test.setTimeout(240000);mkdirSync(evidence,{recursive:false});
  const outcomes:unknown[]=[];
  for(const item of cases){
    const packet=JSON.parse(readFileSync(join(item.receipt,"bindings.json"),"utf8")),original=JSON.parse(readFileSync(join(item.receipt,"result.json"),"utf8"));
    const sock=createServer();await new Promise<void>(done=>sock.listen(0,"127.0.0.1",done));const address=sock.address();if(!address||typeof address==="string")throw new Error("No loopback port");await new Promise<void>(done=>sock.close(()=>done()));
    const origin=`http://127.0.0.1:${address.port}`,server=spawn(python,["-B",resolve("e2e/protected-profile-server.py")],{
      cwd:resolve(".."),windowsHide:true,stdio:"ignore",env:{...process.env,PYTHONPATH:resolve(".."),GEOPHYSICS_PROFILE_QA_CASE:item.root,GEOPHYSICS_PROFILE_BUILD:build,GEOPHYSICS_PROFILE_QA_ORIGIN:origin,GEOPHYSICS_PROFILE_QA_PORT:String(address.port)}});
    const context=await browser.newContext({viewport:{width:1600,height:900},acceptDownloads:true}),page=await context.newPage(),errors:string[]=[];
    page.on("pageerror",error=>errors.push(error.message));
    try {
      await expect.poll(async()=>{if(server.exitCode!==null)throw new Error("Owned API exited");try{return(await fetch(origin+"/api/auth/config")).ok;}catch{return false;}},{timeout:30000}).toBe(true);
      // Existing test-only account from test_profile_jobs; never operator secrets.
      const csrf=await(await context.request.get(origin+"/api/auth/csrf")).json();
      const login=await context.request.post(origin+"/api/auth/cookie/login",{headers:{Origin:origin,"X-CSRF-Token":csrf.csrf_token},form:{username:"local-owner@example.org",password:"test-only-password-872"}});
      expect(login.status()).toBe(204);
      for(const lang of ["en","es"])for(const theme of ["light","dark"])for(const width of [1600,390]){
        await context.addInitScript(({lang,theme})=>{localStorage.setItem("caos.lang",lang);localStorage.setItem("caos.theme",theme);},{lang,theme});await page.setViewportSize({width,height:width===390?844:900});
        await page.goto(`${origin}/?project=${packet.job.project_id}&instrument=profiles`);
        await expect(page.getByTestId("profile-local-instrument")).toBeVisible();
        expect(await page.locator("polygon[data-cell-index]").count()).toBe(item.name==="ert"?original.profile.engine_report.inverse.mesh_cells:original.profile.engine_report.inverse.interleaved.mesh_cells);
        expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
        const main=page.locator(".processing-main");await main.locator(".science-plot").first().scrollIntoViewIfNeeded();await page.screenshot({path:join(evidence,`${item.name}-${lang}-${theme}-${width}-mesh.png`)});
        await page.getByRole("combobox",{name:lang==="es"?"Vista de mediciones":"Measurement view",exact:true}).selectOption("standardized");
        await main.locator(".science-plot").last().scrollIntoViewIfNeeded();await page.screenshot({path:join(evidence,`${item.name}-${lang}-${theme}-${width}-residual.png`)});
        if(lang==="en"&&theme==="light"&&width===1600){
          await page.getByRole("combobox",{name:"Original measurement row",exact:true}).selectOption("3");await page.getByLabel("Native model cell",{exact:true}).fill("4");
          const [inspection]=await Promise.all([page.waitForEvent("download"),page.getByRole("button",{name:"Export exact inspection JSON",exact:true}).click()]);const inspectedPath=join(evidence,item.name+"-inspection.json");await inspection.saveAs(inspectedPath);const inspected=JSON.parse(readFileSync(inspectedPath,"utf8"));expect(inspected.result).toEqual(original.profile);expect(inspected.execution_lane).toBe("protected-worker");expect(inspected.selected.row.index).toBe(3);
          const [bundle]=await Promise.all([page.waitForEvent("download"),page.getByRole("button",{name:"Download verified result ZIP",exact:true}).click()]);const zipPath=join(evidence,item.name+"-export.zip");await bundle.saveAs(zipPath);
          await page.getByLabel("Open saved ZIP for selected job",{exact:true}).setInputFiles(zipPath);await expect(page.getByText("Saved ZIP verified against this selected job; no upload or new computation.",{exact:true})).toBeVisible();
          await page.getByRole("button",{name:"MT transfer functions",exact:true}).click();await expect(page.getByRole("button",{name:"ERT / first-arrival profiles",exact:true})).toBeVisible();await page.getByRole("button",{name:"ERT / first-arrival profiles",exact:true}).click();await expect(page.getByTestId("profile-local-instrument")).toBeVisible();
        }
        outcomes.push({case:item.name,lang,theme,width,verdict:original.numerical_verdict,result_sha256:packet.job.result_sha256});
      }
      expect(errors).toEqual([]);
    } finally {
      await context.close();if(server.pid&&server.exitCode===null)execFileSync(python,["-B","-c","import psutil,sys\np=psutil.Process(int(sys.argv[1]));p.terminate();p.wait(timeout=10)",String(server.pid)]);
    }
  }
  writeFileSync(join(evidence,"outcomes.json"),JSON.stringify({schema:"geophysics.protected-profile-rendered-qa/v1",api_interception:false,physics_replayed:false,outcomes},null,2));
});
