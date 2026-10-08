import { test, expect, type Locator } from "@playwright/test";
import { readFileSync, mkdirSync, writeFileSync } from "node:fs";
import { resolve, isAbsolute } from "node:path";

// Layout prerequisite only: consume a declared real owned export. Never start
// a worker, submit a job, upload originals or claim replay as computation.
const origin=process.env.GEOPHYSICS_QA_URL!;
const evidence=process.env.GEOPHYSICS_QA_EVIDENCE!;
const artifacts=process.env.GEOPHYSICS_QA_LAYOUT_ARTIFACTS!;
if(!artifacts||!isAbsolute(artifacts))throw new Error("Declare exact external real artifact inputs");
const owned=JSON.parse(readFileSync(resolve(artifacts,"owned-job.json"),"utf8"));
mkdirSync(evidence,{recursive:true});

test("retained actual arrays: shared rail sections and all controls are reachable in eight contexts",async({browser})=>{
  const context=await browser.newContext(),page=await context.newPage();
  const errors:string[]=[],walked:Record<string,unknown>[]=[];
  page.on("pageerror",e=>errors.push(e.message));
  page.on("request",r=>{if(r.method()==="POST"&&/\/api\/projects\/.*\/(jobs|datasets|assets)(?:\?|$)/.test(r.url()))errors.push("Layout prerequisite attempted scientific mutation");});
  async function reach(control:Locator){
    await control.scrollIntoViewIfNeeded();await expect(control).toBeVisible();
    const bounds=(await control.boundingBox())!;
    expect(bounds.width).toBeGreaterThan(0);expect(bounds.height).toBeGreaterThan(0);
    const center={x:bounds.x+bounds.width/2,y:bounds.y+bounds.height/2};
    await page.mouse.move(center.x,center.y);
    expect(await control.evaluate(el=>{const r=el.getBoundingClientRect(),hit=document.elementFromPoint(r.x+r.width/2,r.y+r.height/2);return hit===el||Boolean(hit&&el.contains(hit));})).toBe(true);
    expect(center.x).toBeGreaterThanOrEqual(0);expect(center.x).toBeLessThanOrEqual((await page.viewportSize())!.width);
    expect(center.y).toBeGreaterThanOrEqual(0);expect(center.y).toBeLessThanOrEqual((await page.viewportSize())!.height);
    return center;
  }
  async function walk(scope:Locator){
    // Open actual evidence disclosure controls, including nested summaries;
    // merely proving that a closed heading exists is not reachability proof.
    const summaries=scope.locator("summary");
    for(let i=0;i<await summaries.count();i++){
      const summary=summaries.nth(i);if(!await summary.isVisible())continue;
      const center=await reach(summary);
      if(!await summary.evaluate(e=>e.parentElement?.hasAttribute("open")))await page.mouse.click(center.x,center.y);
    }
    const controls=scope.locator('button,input,select,textarea,summary');
    const labels:string[]=[];
    for(let i=0;i<await controls.count();i++){const control=controls.nth(i);if(!await control.isVisible())continue;await reach(control);labels.push(await control.evaluate(e=>e.getAttribute("aria-label")??e.textContent??e.tagName));}
    return labels;
  }
  try{
    const account=await (await context.request.get(origin+"/__qa/local-account")).json();
    const csrf=await (await context.request.get(origin+"/api/auth/csrf")).json();
    expect((await context.request.post(origin+"/api/auth/cookie/login",{headers:{Origin:origin,"X-CSRF-Token":csrf.csrf_token},form:{username:account.email,password:account.password}})).status()).toBe(204);
    const actual=await context.request.get(origin+`/api/projects/${owned.project_id}/jobs/${owned.job_id}/result`);
    expect(actual.ok()).toBe(true);
    expect(await actual.body()).toEqual(readFileSync(resolve(artifacts,"exact-native-result-receipt.json")));
    for(const lang of ["en","es"])for(const theme of ["light","dark"])for(const [width,height] of [[1440,900],[390,844]]){
      const es=lang==="es",key=`${lang}-${theme}-${width}`;
      await page.setViewportSize({width,height});await page.goto(origin+`/?project=${owned.project_id}`);
      await page.evaluate(({lang,theme})=>{localStorage.setItem("caos.lang",lang);localStorage.setItem("caos.theme",theme);},{lang,theme});await page.reload();
      const tab=(name:string)=>page.getByRole("tab",{name,exact:true});
      const jobs=tab(es?"Trabajos":"Jobs"),jobsPoint=await reach(jobs);await page.mouse.click(jobsPoint.x,jobsPoint.y);
      const dataset=page.getByRole("combobox",{name:es?"Conjunto inmutable":"Immutable dataset",exact:true});
      await expect(dataset.locator(`option[value="${owned.dataset_id}"]`)).toHaveCount(1);await dataset.selectOption(owned.dataset_id);
      await page.getByRole("combobox",{name:es?"Historial de trabajos":"Job history",exact:true}).selectOption(owned.job_id);
      await page.getByLabel(es?"Reabrir comprobante guardado contra este trabajo exitoso":"Reopen saved receipt against this successful job",{exact:true}).setInputFiles(resolve(artifacts,"exact-native-result-receipt.json"));
      await page.getByLabel(es?"Reabrir ZIP guardado contra este trabajo exitoso":"Reopen saved ZIP against this successful job",{exact:true}).setInputFiles(resolve(artifacts,"actual-native-waveform.zip"));
      await expect(page.locator(".waveform-trace")).toHaveCount(12);
      await page.getByRole("button",{name:es?"Editar solicitud indexada como nuevo borrador":"Edit indexed request as a new draft",exact:true}).click();
      for(const name of [es?"Fuente / índice":"Source / index",es?"Solicitud científica":"Scientific request",es?"Trabajos":"Jobs"]){
        const current=tab(name);await reach(current);await current.click();
        if(name===(es?"Solicitud científica":"Scientific request")){
          const section=page.getByRole("combobox",{name:es?"Sección de solicitud":"Request section",exact:true});
          await reach(section);await section.focus();await page.keyboard.press("Home");await page.keyboard.press("Enter");
          const groups=["utc","nslc","source","response","filter","trigger","psd","advanced"];
          for(let groupIndex=0;groupIndex<groups.length;groupIndex++){
            const group=groups[groupIndex];
            if(groupIndex){await reach(section);await section.focus();await page.keyboard.press("ArrowDown");await page.keyboard.press("Enter");}
            await expect(section).toHaveValue(group);
            walked.push({context:key,section:group,controls:await walk(page.locator("[data-rail]"))});
            if(group==="advanced")expect(JSON.parse(await page.getByLabel(es?"Solicitud científica JSON":"Scientific request JSON",{exact:true}).inputValue())).toEqual(owned.request.scientific_request);
          }
        }else walked.push({context:key,section:name,controls:await walk(page.locator("[data-rail]"))});
      }
      walked.push({context:key,section:"instrument",controls:await walk(page.locator("[data-instrument]"))});
      for(let i=0;i<12;i++){
        const plot=page.locator(".waveform-trace svg").nth(i);await reach(plot);
        const measure=await plot.evaluate(svg=>{const node=svg as SVGSVGElement,r=node.getBoundingClientRect(),axis=node.querySelector("text:last-child")!;return {width:r.width,viewBox:node.viewBox.baseVal.width,axisHeight:axis.getBoundingClientRect().height};});
        expect(measure.width/width).toBeGreaterThan(width<760?.85:.65);expect(measure.axisHeight).toBeGreaterThanOrEqual(10);expect(Math.abs(measure.width-measure.viewBox)).toBeLessThan(1);
        if(i===0||i===10)await page.screenshot({path:resolve(evidence,`${key}-plot${i}.png`)});
      }
      const dimensions=await page.evaluate(()=>({width:document.documentElement.scrollWidth,height:document.documentElement.scrollHeight,innerWidth,innerHeight}));
      expect(dimensions.width).toBe(dimensions.innerWidth);if(width>=1280)expect(dimensions.height).toBe(dimensions.innerHeight);
      walked.push({context:key,dimensions});
    }
    expect(errors).toEqual([]);writeFileSync(resolve(evidence,"control-walk.json"),JSON.stringify({schema:1,scientificMutation:false,job:owned.job_id,walked}),{flag:"wx"});
  }finally{await context.close();}
});
