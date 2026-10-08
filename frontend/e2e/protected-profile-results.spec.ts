import { test, expect } from "@playwright/test";
import { spawn, execFileSync } from "node:child_process";
import { createServer } from "node:net";
import { readFileSync, mkdirSync, writeFileSync } from "node:fs";
import { resolve, join } from "node:path";
import { installLib } from "../node_modules/@fasl-work/caos-app-shell/gate/inpage.mjs";
import { decodePng, paintedBox, unionArea } from "../node_modules/@fasl-work/caos-app-shell/gate/png.mjs";

// Real canonical result bytes and real authenticated API. No API interception
// and no solver replay during rendering. Native execution is a separate gate.
const required=(key:string)=>{if(!process.env[key])throw new Error(`Supply ${key}`);return resolve(process.env[key]!);};
const python=required("GEOPHYSICS_REVIEW_PYTHON"),build=required("GEOPHYSICS_PROFILE_BUILD"),evidence=required("GEOPHYSICS_PROFILE_EVIDENCE");
const cases=[{name:"ert",root:required("GEOPHYSICS_PROFILE_QA_ERT_CASE"),receipt:required("GEOPHYSICS_PROFILE_JOB_ERT")},
  {name:"traveltime",root:required("GEOPHYSICS_PROFILE_QA_TRAVELTIME_CASE"),receipt:required("GEOPHYSICS_PROFILE_JOB_TRAVELTIME")}];

test("owned_result_roundtrip",async({browser})=>{
  test.setTimeout(240000);mkdirSync(evidence,{recursive:false});
  const outcomes:unknown[]=[],drawingGates:{case:string;lang:string;theme:string;width:number;share:number;stage_fill:number;passed:boolean}[]=[];
  for(const item of cases){
    const packet=JSON.parse(readFileSync(join(item.receipt,"bindings.json"),"utf8")),original=JSON.parse(readFileSync(join(item.receipt,"result.json"),"utf8"));
    const sock=createServer();await new Promise<void>(done=>sock.listen(0,"127.0.0.1",done));const address=sock.address();if(!address||typeof address==="string")throw new Error("No loopback port");await new Promise<void>(done=>sock.close(()=>done()));
    const origin=`http://127.0.0.1:${address.port}`,server=spawn(python,["-B",resolve("e2e/protected-profile-server.py")],{
      cwd:resolve(".."),windowsHide:true,stdio:"ignore",env:{...process.env,PYTHONPATH:resolve(".."),GEOPHYSICS_PROFILE_QA_CASE:item.root,GEOPHYSICS_PROFILE_BUILD:build,GEOPHYSICS_PROFILE_QA_ORIGIN:origin,GEOPHYSICS_PROFILE_QA_PORT:String(address.port)}});
    const context=await browser.newContext({viewport:{width:1600,height:900},acceptDownloads:true}),page=await context.newPage(),errors:string[]=[];
    await context.addInitScript(installLib);
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
        const methodNav=page.getByRole("navigation",{name:lang==="es"?"Método del proyecto":"Project method",exact:true});
        const methodSelect=methodNav.getByRole("combobox");
        await expect(methodSelect.locator("option")).toHaveCount(4);
        await expect(page.locator("polygon[data-cell-index]")).toHaveCount(item.name==="ert"?original.profile.engine_report.inverse.mesh_cells:original.profile.engine_report.inverse.interleaved.mesh_cells);
        expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
        const main=page.locator(".processing-main");await main.locator("[data-native-mesh]").scrollIntoViewIfNeeded();
        const screenshot=await page.screenshot({path:join(evidence,`${item.name}-${lang}-${theme}-${width}-mesh.png`)});
        const facts=await page.evaluate(()=>window.__caosGate.facts());
        const mesh=facts.surfaces.find((surface:any)=>surface.kind==="svg"),image=decodePng(screenshot);
        const paint=mesh?paintedBox(image,{x:mesh.x,y:mesh.y,w:mesh.w,h:mesh.h}):null;
        const stageFill=paint&&mesh?paint.w*paint.h/Math.max(1,mesh.stage.w*mesh.stage.h):0;
        const share=mesh&&paint&&stageFill>=.3?unionArea([mesh.view],facts.vw,facts.vh)/(facts.vw*facts.vh):0;
        drawingGates.push({case:item.name,lang,theme,width,share,stage_fill:stageFill,passed:stageFill>=.3&&share>=.5});
        writeFileSync(join(evidence,"drawing-gates.json"),JSON.stringify({schema:"geophysics.profile-shared-drawing-gate/v1",algorithm:"installed-caos-shell-0.8.1-G6",drawingGates},null,2));
        await page.getByText(lang==="es"?"Controles nativos de fila, celda y visualización":"Native row, cell and display controls",{exact:true}).click();
        const meshSvg=page.locator("[data-native-mesh]");
        const selectedPolygon=meshSvg.locator('polygon[data-cell-index="4"]');
        await selectedPolygon.scrollIntoViewIfNeeded();
        const centre=await selectedPolygon.evaluate((node:SVGPolygonElement)=>{
          const points=Array.from({length:node.points.numberOfItems},(_,i)=>node.points.getItem(i));
          const local=new DOMPoint(points.reduce((sum,p)=>sum+p.x,0)/points.length,points.reduce((sum,p)=>sum+p.y,0)/points.length);
          const matrix=node.getScreenCTM();if(!matrix)throw new Error("Native polygon has no rendered transform");
          const screen=local.matrixTransform(matrix);return{x:screen.x,y:screen.y};
        });
        await page.mouse.click(centre.x,centre.y);
        await expect(page.getByLabel(lang==="es"?"Celda nativa del modelo":"Native model cell",{exact:true})).toHaveValue("4");
        await meshSvg.focus();await page.keyboard.press("ArrowRight");
        await expect(page.getByLabel(lang==="es"?"Celda nativa del modelo":"Native model cell",{exact:true})).toHaveValue("5");
        await page.getByRole("combobox",{name:lang==="es"?"Vista de mediciones":"Measurement view",exact:true}).selectOption("standardized");
        await main.locator(".science-plot").last().scrollIntoViewIfNeeded();await page.screenshot({path:join(evidence,`${item.name}-${lang}-${theme}-${width}-residual.png`)});
        if(lang==="en"&&theme==="light"&&width===1600){
          await page.getByRole("combobox",{name:"Original measurement row",exact:true}).selectOption("3");await page.getByLabel("Native model cell",{exact:true}).fill("4");
          const [inspection]=await Promise.all([page.waitForEvent("download"),page.getByRole("button",{name:"Export exact inspection JSON",exact:true}).click()]);const inspectedPath=join(evidence,item.name+"-inspection.json");await inspection.saveAs(inspectedPath);const inspected=JSON.parse(readFileSync(inspectedPath,"utf8"));expect(inspected.result).toEqual(original.profile);expect(inspected.execution_lane).toBe("protected-worker");expect(inspected.selected.row.index).toBe(3);
          await page.getByText("Processing controls",{exact:true}).click();
          const [bundle]=await Promise.all([page.waitForEvent("download"),page.getByRole("button",{name:"Download verified result ZIP",exact:true}).click()]);const zipPath=join(evidence,item.name+"-export.zip");await bundle.saveAs(zipPath);
          await page.getByLabel("Open saved ZIP for selected job",{exact:true}).setInputFiles(zipPath);await expect(page.getByText("Saved ZIP verified against this selected job; no upload or new computation.",{exact:true})).toBeVisible();
          await expect(page.getByRole("button",{name:"MT transfer functions",exact:true})).toHaveCount(0);
          await methodSelect.selectOption("mt");await expect(methodSelect).toHaveValue("mt");
          await expect(page.getByRole("button",{name:"ERT / first-arrival profiles",exact:true})).toHaveCount(0);
          await methodSelect.selectOption("profiles");await expect(page.getByTestId("profile-local-instrument")).toBeVisible();
          await methodSelect.selectOption("waveform");
          await expect(page.getByRole("textbox",{name:"Scientific request JSON",exact:true})).toBeVisible();
          await expect(page.getByRole("combobox",{name:"Stored MiniSEED",exact:true})).toBeEnabled();
          expect(new URL(page.url()).searchParams.get("project")).toBe(packet.job.project_id);
          expect(new URL(page.url()).searchParams.get("instrument")).toBe("waveform");
          await methodSelect.selectOption("profiles");
          await expect(page.getByTestId("profile-local-instrument")).toBeVisible();
        }
        await methodSelect.selectOption("waveform");
        if(width===390)await page.getByRole("button",{name:lang==="es"?"Controles de procesamiento":"Processing controls",exact:true}).click();
        await expect(page.getByRole("textbox",{name:lang==="es"?"Solicitud científica JSON":"Scientific request JSON",exact:true})).toBeVisible();
        await expect(page.getByRole("combobox",{name:lang==="es"?"MiniSEED almacenado":"Stored MiniSEED",exact:true})).toBeEnabled();
        await page.screenshot({path:join(evidence,`${item.name}-${lang}-${theme}-${width}-waveform-navigation.png`)});
        expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
        await methodSelect.selectOption("profiles");await expect(page.getByTestId("profile-local-instrument")).toBeVisible();
        const instrumentBox=await page.locator(".processing-main").boundingBox();
        expect(instrumentBox!.width).toBeGreaterThan(width===390?width*.85:width*.65);
        outcomes.push({case:item.name,lang,theme,width,verdict:original.numerical_verdict,result_sha256:packet.job.result_sha256});
      }
      expect(errors).toEqual([]);
    } finally {
      await context.close();if(server.pid&&server.exitCode===null)execFileSync(python,["-B","-c","import psutil,sys\np=psutil.Process(int(sys.argv[1]));p.terminate();p.wait(timeout=10)",String(server.pid)]);
    }
  }
  writeFileSync(join(evidence,"outcomes.json"),JSON.stringify({schema:"geophysics.protected-profile-rendered-qa/v1",api_interception:false,physics_replayed:false,outcomes},null,2));
  expect(drawingGates.filter(gate=>!gate.passed),"Actual native drawing must meet the unchanged shared G6 floors").toEqual([]);
});
