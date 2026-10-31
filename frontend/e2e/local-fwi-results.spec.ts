import { test, expect } from "@playwright/test";
import { spawn, type ChildProcess } from "node:child_process";
import { createServer } from "node:net";
import { createHash } from "node:crypto";
import { readFileSync, readdirSync, mkdirSync, writeFileSync } from "node:fs";
import { resolve, join } from "node:path";

const required=(key:string)=>{if(!process.env[key])throw new Error(`Supply ${key}`);return resolve(process.env[key]!);};
const build=required("GEOPHYSICS_FWI_BUILD"),generation=required("GEOPHYSICS_FWI_GENERATION"),evidenceRoot=required("GEOPHYSICS_FWI_EVIDENCE");
let server:ChildProcess,origin:string,evidence:string;
const manifest=JSON.parse(readFileSync(join(generation,"manifest.json"),"utf8")),paths=readdirSync(generation).map(name=>join(generation,name));
const before=paths.map(path=>createHash("sha256").update(readFileSync(path)).digest("hex"));
test.beforeAll(async({},info)=>{
  evidence=join(evidenceRoot,`worker-${info.workerIndex}`);mkdirSync(evidence,{recursive:true});
  const socket=createServer();await new Promise<void>(done=>socket.listen(0,"127.0.0.1",done));const address=socket.address();if(!address||typeof address==="string")throw new Error("No loopback address");await new Promise<void>(done=>socket.close(()=>done()));origin=`http://127.0.0.1:${address.port}`;
  server=spawn(process.execPath,[resolve("node_modules/vite/bin/vite.js"),"preview","--outDir",build,"--host","127.0.0.1","--port",String(address.port),"--strictPort"],{windowsHide:true,stdio:"ignore"});
  await expect.poll(async()=>{if(server.exitCode!==null)throw new Error("Owned preview exited");try{return(await fetch(origin)).ok;}catch{return false;}},{timeout:30000}).toBe(true);
});
test.afterAll(async()=>{if(server?.pid&&server.exitCode===null){server.kill();await new Promise<void>(done=>{server.once("exit",()=>done());setTimeout(()=>done(),5000);});}expect(paths.map(path=>createHash("sha256").update(readFileSync(path)).digest("hex"))).toEqual(before);});

test("actual local CUDA generation: languages, themes, phone, full-sample linked values and real recorded states",async({browser})=>{
  const results:unknown[]=[];
  for(const lang of ["en","es"])for(const theme of ["light","dark"])for(const width of [1600,390]){
    const context=await browser.newContext({viewport:{width,height:width===390?844:900},reducedMotion:"reduce",acceptDownloads:true}),page=await context.newPage(),errors:string[]=[],writes:string[]=[];
    page.on("pageerror",error=>errors.push(error.message));page.on("request",request=>{if(request.method()!=="GET")writes.push(request.url());});
    await context.addInitScript(({lang,theme})=>{localStorage.setItem("caos.lang",lang);localStorage.setItem("caos.theme",theme);},{lang,theme});
    try{
      await page.goto(origin+"/?instrument=fwi-local");
      if(width===390)await page.getByRole("button",{name:lang==="es"?"Controles acústicos locales":"Local acoustic controls",exact:true}).click();
      await page.getByLabel(lang==="es"?"Generación acústica local completa":"Complete local acoustic generation",{exact:true}).setInputFiles(paths);
      await page.getByRole("button",{name:lang==="es"?"Abrir resultado acústico verificado":"Open verified acoustic result",exact:true}).click();
      const instrument=page.getByTestId("fwi-local-instrument");await expect(instrument).toBeVisible();
      await expect(instrument).toContainText(manifest.request.id);
      await expect(instrument.locator(".heatmap-area")).toHaveCount(2);
      const area=instrument.locator(".heatmap-area").first();await area.scrollIntoViewIfNeeded();const bounds=(await area.boundingBox())!;expect(bounds.width/bounds.height).toBeCloseTo(128/96,2);
      await page.screenshot({path:join(evidence,`${lang}-${theme}-${width}-model.png`)});
      await page.getByLabel(lang==="es"?"Índice de disparo":"Source shot index",{exact:true}).fill("1");await page.getByLabel(lang==="es"?"Índice original de receptor":"Original receiver index",{exact:true}).fill("2");await page.getByLabel(lang==="es"?"Índice original de muestra temporal":"Original time-sample index",{exact:true}).fill("962");
      await expect(page.getByTestId("fwi-exact-sample")).toContainText(lang==="es"?"receptor reservado":"withheld receiver");
      await page.getByLabel(lang==="es"?"Vista científica":"Scientific view",{exact:true}).selectOption("gathers");await expect(instrument.locator("canvas")).toHaveCount(3);
      for(const canvas of await instrument.locator("canvas").all()) {await expect(canvas).toHaveAttribute("width","20");await expect(canvas).toHaveAttribute("height","3200");}
      const gatherBounds=(await instrument.locator(".heatmap-area").first().boundingBox())!;expect(gatherBounds.width/gatherBounds.height).toBeCloseTo(1.45,2);
      await instrument.locator("canvas").first().scrollIntoViewIfNeeded();await page.screenshot({path:join(evidence,`${lang}-${theme}-${width}-gathers.png`)});
      await page.getByLabel(lang==="es"?"Vista científica":"Scientific view",{exact:true}).selectOption("trace");const trace=instrument.locator("svg[data-selected-index='962']");await expect(trace).toBeVisible();await trace.scrollIntoViewIfNeeded();await page.screenshot({path:join(evidence,`${lang}-${theme}-${width}-trace.png`)});
      expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
      if(lang==="en"&&theme==="light"&&width===1600){
        const [download]=await Promise.all([page.waitForEvent("download"),page.getByRole("button",{name:"Export exact FWI inspection JSON",exact:true}).click()]);const output=join(evidence,"exact-inspection.json");await download.saveAs(output);const inspection=JSON.parse(readFileSync(output,"utf8"));const offset=((1*20+2)*3200+962)*4;
        expect(inspection.observed).toBe(readFileSync(join(generation,"observed.f32")).readFloatLE(offset));expect(inspection.predicted).toBe(readFileSync(join(generation,"fwi-multiscale-predicted.f32")).readFloatLE(offset));expect(inspection.residual).toBe(readFileSync(join(generation,"fwi-multiscale-residual.f32")).readFloatLE(offset));expect(inspection.physics_replayed).toBe(false);
        await page.getByLabel("Scientific view",{exact:true}).selectOption("model");const slider=page.getByLabel("Recorded velocity state",{exact:true});await slider.fill("0");await page.getByRole("button",{name:"Play recorded iterations",exact:true}).click();await expect.poll(()=>slider.inputValue()).not.toBe("0");await page.getByRole("button",{name:"Pause recorded iterations",exact:true}).click();const paused=await slider.inputValue();await page.waitForTimeout(600);expect(await slider.inputValue()).toBe(paused);
        await page.getByLabel("FWI schedule",{exact:true}).selectOption("fwi-l2");await expect(slider).toHaveValue(String(manifest.arrays["fwi-l2-frames"].shape[0]-1));
      }
      expect(errors).toEqual([]);expect(writes).toEqual([]);results.push({lang,theme,width,full_samples:3200,physics_replayed:false,uploaded:false});
    }finally{await context.close();}
  }
  writeFileSync(join(evidence,"outcomes.json"),JSON.stringify(results,null,2));
});

test("integrated supplied joint course: all six questions through the existing citation provider",async({browser})=>{
  for(const lang of ["en","es"])for(const theme of ["light","dark"])for(const width of [1600,390]){
    const context=await browser.newContext({viewport:{width,height:width===390?844:900},reducedMotion:"reduce"}),page=await context.newPage(),errors:string[]=[];
    page.on("pageerror",error=>errors.push(error.message));await context.addInitScript(({lang,theme})=>{localStorage.setItem("caos.lang",lang);localStorage.setItem("caos.theme",theme);},{lang,theme});
    try{
      await page.goto(origin+"/");await page.getByLabel(lang==="es"?"Caso geológico":"Geological case",{exact:true}).selectOption("JOINT_SHARED");
      await page.getByRole("tab",{name:lang==="es"?"Teoría para levantamientos":"Supplied-survey theory",exact:true}).click();const course=page.locator("[data-m11-course]");await expect(course).toBeVisible();
      const question=course.getByLabel(lang==="es"?"Pregunta científica":"Scientific question",{exact:true});
      for(let chapter=0;chapter<6;chapter++){
        await question.selectOption(String(chapter));await expect(course.locator(".katex-error")).toHaveCount(0);await expect(course.locator(".katex").first()).toBeVisible();await course.getByRole("button",{name:lang==="es"?"Revelar razonamiento":"Reveal reasoning",exact:true}).click();await expect(course.getByRole("status")).toBeVisible();expect(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1)).toBe(true);
        if(chapter===0||chapter===5){await course.scrollIntoViewIfNeeded();await page.screenshot({path:join(evidence,`joint-${lang}-${theme}-${width}-${chapter}.png`)});}
      }
      expect(errors).toEqual([]);
    }finally{await context.close();}
  }
});
