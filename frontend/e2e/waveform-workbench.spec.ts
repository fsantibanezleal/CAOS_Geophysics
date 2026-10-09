import { test, expect, type APIRequestContext, type BrowserContext, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { createHash } from "node:crypto";

const origin=process.env.GEOPHYSICS_QA_URL??"http://127.0.0.1:8898";
const evidence=process.env.GEOPHYSICS_QA_EVIDENCE!;
mkdirSync(evidence,{recursive:true});
test.describe.configure({mode:"serial"});
let context:BrowserContext,page:Page,project:string,dataset:string,success:string,request:unknown,zip:string;
const errors:string[]=[];
async function post(api:APIRequestContext,path:string,data?:unknown,form?:Record<string,string>){
  const csrf=await (await api.get(origin+"/api/auth/csrf")).json();
  return api.post(origin+path,{headers:{Origin:origin,"X-CSRF-Token":csrf.csrf_token},...(form?{form}:data===undefined?{}:{data})});
}
const select=(name:string)=>page.getByRole("combobox",{name,exact:true});
test.beforeAll(async({browser})=>{
  context=await browser.newContext({viewport:{width:1440,height:900},acceptDownloads:true});
  page=await context.newPage();page.on("pageerror",e=>errors.push(e.message));
  const email=`waveform-${Date.now()}@example.org`,password="actual isolated waveform QA password";
  expect((await post(context.request,"/api/auth/register",{email,password})).status()).toBe(201);
  const {token}=await (await context.request.get(origin+"/__qa/mail/latest")).json();
  expect((await post(context.request,"/api/auth/verify/verify",{token})).ok()).toBe(true);
  expect((await post(context.request,"/api/auth/cookie/login",undefined,{username:email,password})).status()).toBe(204);
  const created=await post(context.request,"/api/projects",{name:"Actual waveform browser control",description:"Authored control, not field truth"});
  expect(created.status()).toBe(201);project=(await created.json()).id;
  const fixture=await (await context.request.get(origin+"/__qa/waveform")).json();request=fixture.request;
  expect(fixture.harness).toBe("actual-waveform-native-v1");
  let xml="";
  for(const role of ["stationxml","miniseed"]){
    const {base64,metadata}=fixture.inputs[role];const buffer=Buffer.from(base64,"base64");
    expect(createHash("sha256").update(buffer).digest("hex")).toBe(metadata.source.expected_sha256);
    if(role==="miniseed")metadata.physical.geometry.stationxml_asset_id=xml;
    const csrf=await (await context.request.get(origin+"/api/auth/csrf")).json();
    const upload=await context.request.post(origin+`/api/projects/${project}/assets`,{headers:{Origin:origin,"X-CSRF-Token":csrf.csrf_token,"Content-Type":metadata.mime,"X-Asset-Metadata":JSON.stringify(metadata)},data:buffer});
    expect(upload.status(),await upload.text()).toBe(201);xml=(await upload.json()).asset_id;
  }
  await page.goto(origin+`/?project=${project}`);
});
test.afterAll(async()=>{await context?.request.post(origin+"/__qa/worker/stop");await context?.close();});

test("index immutable originals, queued cancel, actual native calculation and all-array export",async()=>{
  await expect(select("Stored MiniSEED").locator("option")).toHaveCount(2);
  await select("Stored MiniSEED").selectOption({label:"trace.mseed"});
  await page.getByLabel("Scientific request JSON",{exact:true}).fill(JSON.stringify(request));
  await page.getByRole("button",{name:"Index exact pair and request",exact:true}).click();
  await expect(page.getByRole("button",{name:"Run full processing",exact:true})).toBeEnabled();
  dataset=await select("Immutable dataset").inputValue();expect(dataset).toMatch(/^[a-f0-9-]{36}$/);
  await page.getByRole("button",{name:"Run full processing",exact:true}).click();
  await expect(page.getByRole("status").filter({hasText:"Queued"})).toBeVisible();
  await page.getByRole("button",{name:"Cancel job",exact:true}).click();
  await expect(page.getByRole("status").filter({hasText:"Cancelled"})).toBeVisible();
  expect((await context.request.post(origin+"/__qa/worker/start")).ok()).toBe(true);
  await page.getByRole("button",{name:"Run full processing",exact:true}).click();
  await expect(page.getByRole("status").filter({hasText:"Succeeded"})).toBeVisible({timeout:90000});
  await expect(page.getByRole("button",{name:"Verify, plot and export all arrays",exact:true})).toBeEnabled();
  success=await select("Job history").inputValue();
  const result=await (await context.request.get(origin+`/api/projects/${project}/jobs/${success}/result`)).json();
  expect(result.scientific_status).toBe("computed");expect(result.resources.host_admitted).toBe(false);
  expect(result.calculation.field_truth).toBeNull();expect(result.calculation.array_descriptors.length).toBeGreaterThan(10);
  const [download]=await Promise.all([page.waitForEvent("download"),page.getByRole("button",{name:"Verify, plot and export all arrays",exact:true}).click()]);
  zip=resolve(evidence,"actual-native-waveform.zip");await download.saveAs(zip);
  await expect(page.locator(".waveform-trace")).toHaveCount(7);
  await page.getByLabel("Reopen saved ZIP against this successful job",{exact:true}).setInputFiles(zip);
  await expect(page.locator(".waveform-trace")).toHaveCount(7);
  const plot=page.getByRole("img",{name:"counts; t [s]; counts",exact:true});
  await plot.scrollIntoViewIfNeeded();const bounds=(await plot.boundingBox())!;
  await page.mouse.move(bounds.x+bounds.width*.6,bounds.y+bounds.height*.5);
  await expect(page.getByText(/Shared time cursor relative to conditioning start:/)).not.toContainText("0.000 s");
  await plot.focus();await page.keyboard.press("Home");
  await expect(page.getByText(/Shared time cursor relative to conditioning start:/)).toContainText("0.000 s");
  await page.keyboard.press("ArrowRight");
  await expect(page.getByText(/Shared time cursor relative to conditioning start:/)).not.toContainText("0.000 s");
  await page.getByRole("button",{name:"Reload project",exact:true}).click();
  await expect(page.getByRole("button",{name:"Verify, plot and export all arrays",exact:true})).toBeEnabled();
  await page.getByLabel("Reopen saved ZIP against this successful job",{exact:true}).setInputFiles(zip);
  await expect(page.locator(".waveform-trace")).toHaveCount(7);expect(errors).toEqual([]);
});

test("bilingual light/dark desktop/phone plots fit the existing shell and reopen verified arrays",async()=>{
  for(const lang of ["en","es"])for(const theme of ["light","dark"])for(const [width,height] of [[1440,900],[390,844]]){
    const es=lang==="es";await page.setViewportSize({width,height});
    await page.evaluate(({lang,theme})=>{localStorage.setItem("caos.lang",lang);localStorage.setItem("caos.theme",theme);},{lang,theme});
    await page.reload();await expect(page.locator("html")).toHaveAttribute("data-theme",theme);
    if(width<760)await page.getByRole("button",{name:es?"Controles de procesamiento":"Processing controls",exact:true}).click();
    await expect(select(es?"Conjunto inmutable":"Immutable dataset").locator("option")).toHaveCount(2);
    await select(es?"Conjunto inmutable":"Immutable dataset").selectOption(dataset);
    await select(es?"Historial de trabajos":"Job history").selectOption(success);
    await page.getByLabel(es?"Reabrir ZIP guardado contra este trabajo exitoso":"Reopen saved ZIP against this successful job",{exact:true}).setInputFiles(zip);
    if(width<760)await page.getByRole("button",{name:es?"Controles de procesamiento":"Processing controls",exact:true}).click();
    const plot=page.getByRole("img",{name:"counts; t [s]; counts",exact:true});await plot.scrollIntoViewIfNeeded();
    await expect(plot).toBeVisible();
    const dimensions=await page.evaluate(()=>({w:document.documentElement.scrollWidth,h:document.documentElement.scrollHeight,iw:innerWidth,ih:innerHeight}));
    expect(dimensions.w).toBe(dimensions.iw);expect(dimensions.h).toBe(dimensions.ih);
    expect(await plot.locator("polyline").evaluate(n=>getComputedStyle(n).stroke)).not.toBe("none");
    // Test rendered size, not just a CSS font declaration: the old fixed
    // viewBox silently reduced 11px labels to about 5px on a phone.
    const axis=await plot.locator("text").last().evaluate(n=>{const box=n.getBoundingClientRect(),svg=n.ownerSVGElement!;return {height:box.height,width:svg.viewBox.baseVal.width,actual:svg.getBoundingClientRect().width};});
    expect(axis.height).toBeGreaterThanOrEqual(10);expect(Math.abs(axis.width-axis.actual)).toBeLessThan(1);
    await page.screenshot({path:resolve(evidence,`${lang}-${theme}-${width}.png`)});
  }
  expect(errors).toEqual([]);
});

test("selected job boundary, corrupt local export and expired session never show accepted arrays",async()=>{
  await page.setViewportSize({width:1440,height:900});await page.evaluate(()=>localStorage.setItem("caos.lang","en"));await page.reload();
  await expect(select("Immutable dataset").locator("option")).toHaveCount(2);await select("Immutable dataset").selectOption(dataset);
  await select("Job history").selectOption(success);
  await page.getByLabel("Reopen saved ZIP against this successful job",{exact:true}).setInputFiles({name:"corrupt.zip",mimeType:"application/zip",buffer:Buffer.from("not a ZIP")});
  await expect(page.getByRole("alert")).toBeVisible();await expect(page.locator(".waveform-trace")).toHaveCount(0);
  const jobs=await (await context.request.get(origin+`/api/projects/${project}/jobs`)).json();
  const cancelled=jobs.jobs.find((j:{state:string})=>j.state==="cancelled");expect(cancelled).toBeTruthy();
  await select("Job history").selectOption(cancelled.job_id);
  await expect(page.getByRole("button",{name:"Verify, plot and export all arrays",exact:true})).toHaveCount(0);
  await context.clearCookies();await page.reload();await expect(page.getByRole("alert")).toBeVisible();
  await expect(page.getByRole("button",{name:"Run full processing",exact:true})).toBeDisabled();expect(errors).toEqual([]);
});
