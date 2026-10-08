import { test, expect, type APIRequestContext, type BrowserContext, type Page } from "@playwright/test";
import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { createHash } from "node:crypto";
import { waveformUtcUs } from "../src/components/waveform-request";

const origin=process.env.GEOPHYSICS_QA_URL??"http://127.0.0.1:8898";
const evidence=process.env.GEOPHYSICS_QA_EVIDENCE!;
mkdirSync(evidence,{recursive:true});
test.describe.configure({mode:"serial"});
let context:BrowserContext,page:Page,project:string,dataset:string,success:string,request:Record<string,any>,zip:string,nativeUnit:string,responseUnit:string,fixtureCase:string;
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
  const created=await post(context.request,"/api/projects",{name:"Actual waveform browser control",description:"Exact supplied originals; local validation, not field truth"});
  expect(created.status()).toBe(201);project=(await created.json()).id;
  const fixture=await (await context.request.get(origin+"/__qa/waveform")).json();request=fixture.request;
  expect(fixture.harness).toBe("actual-waveform-native-v1");
  fixtureCase=fixture.case;
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
  // Enter every scientific value through actual grouped controls, not just JSON.
  await page.getByRole("button",{name:"Add explicit channel",exact:true}).click();
  for(const [label,key] of [["Network c00","network"],["Station c00","station"],["Channel c00","channel"]])await page.getByLabel(label,{exact:true}).fill(request.channels[0][key]);
  await page.getByLabel("Location is explicitly blank c00",{exact:true}).check();
  for(const [label,key] of [["Conditioning start UTC","conditioning_start_utc"],["Conditioning end UTC","conditioning_end_utc"],["Analysis start UTC","analysis_start_utc"],["Analysis end UTC","analysis_end_utc"]])await page.getByLabel(label,{exact:true}).fill(request[key]);
  await page.getByText("Source declaration and rights",{exact:true}).click();
  await select("Source kind").selectOption(request.source.kind);await select("Processing rights").selectOption(request.source.rights);
  await page.getByLabel("Source citation",{exact:true}).fill(request.source.citation);
  await page.getByLabel("Previous processing statement",{exact:true}).fill(request.source.processing_statement);
  await page.getByText("Response and prefilter",{exact:true}).click();
  for(let i=0;i<4;i++)await page.getByLabel(`Prefilter corner ${i+1} [Hz]`,{exact:true}).fill(String(request.processing.prefilter_hz[i]));
  await page.getByLabel("Water level [dB]",{exact:true}).fill(String(request.processing.water_level_db));
  await page.getByText("Acausal filter",{exact:true}).click();
  for(const [label,key] of [["Filter order [2–6]","filter_order"],["Time taper fraction [0.01–0.10]","taper_fraction"],["Edge guard [s]","edge_guard_s"]])await page.getByLabel(label,{exact:true}).fill(String(request.processing[key]));
  await page.getByLabel("Bandpass low [Hz]",{exact:true}).fill(String(request.processing.bandpass_hz[0]));
  await page.getByLabel("Bandpass high [Hz]",{exact:true}).fill(String(request.processing.bandpass_hz[1]));
  await page.getByText("STA/LTA · unlabelled triggers",{exact:true}).click();
  for(const [label,key] of [["STA [s]","sta_s"],["LTA [s]","lta_s"],["Trigger on ratio","threshold_on"],["Trigger off ratio","threshold_off"],["Refractory [s]","refractory_s"]])await page.getByLabel(label,{exact:true}).fill(String(request.processing[key]));
  await page.getByText("Welch PSD",{exact:true}).click();await page.getByLabel("Welch segment [samples]",{exact:true}).fill(String(request.processing.welch_segment_samples));
  await page.getByText("Advanced JSON · import/export exact request",{exact:true}).click();
  const draft=JSON.parse(await page.getByLabel("Scientific request JSON",{exact:true}).inputValue());
  expect(draft).toEqual({...request,source:{...request.source,declared_sha256:null,provider_url:null}});
  // Explicit advanced evidence fields preserve original declared URL/hash.
  await page.getByLabel("Scientific request JSON",{exact:true}).fill(JSON.stringify({...draft,source:request.source}));
  const [requestDownload]=await Promise.all([page.waitForEvent("download"),page.getByRole("button",{name:"Save explicit request JSON",exact:true}).click()]);
  const requestFile=resolve(evidence,"exact-scientific-request.json");await requestDownload.saveAs(requestFile);
  await page.getByLabel("STA [s]",{exact:true}).fill("");
  await expect(page.getByRole("button",{name:"Index exact pair and request",exact:true})).toBeDisabled();
  await page.getByLabel("Load request file",{exact:true}).setInputFiles(requestFile);
  await expect(page.getByLabel("STA [s]",{exact:true})).toHaveValue(String(request.processing.sta_s));
  const review=page.getByLabel("I reviewed this exact request against the selected original pair",{exact:true});
  const index=page.getByRole("button",{name:"Index exact pair and request",exact:true});
  await expect(index).toBeDisabled();await review.check();await expect(index).toBeEnabled();
  await select("Stored MiniSEED").selectOption("");await expect(index).toBeDisabled();
  await select("Stored MiniSEED").selectOption({label:"trace.mseed"});await expect(review).not.toBeChecked();await review.check();
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
  // Preserve the actual owned API envelope alongside the portable scientific
  // ZIP. Its measured resource summary is not carried by that portable receipt.
  for(const [name,value] of [["owned-result.json",result],
    ["owned-job.json",await (await context.request.get(origin+`/api/projects/${project}/jobs/${success}`)).json()],
    ["owned-dataset.json",await (await context.request.get(origin+`/api/projects/${project}/datasets/${dataset}`)).json()]] as const){
    const body=JSON.stringify(value);expect(Buffer.byteLength(body)).toBeLessThanOrEqual(4194304);
    writeFileSync(resolve(evidence,name),body,{flag:"wx"});
  }
  nativeUnit=result.calculation.channels[0].native_unit;responseUnit=result.calculation.array_descriptors.find((d:{name:string})=>d.name==="response_real").unit;
  if(fixtureCase==="ridgecrest-original-aligned"){
    expect(result.sources.miniseed.raw_sha256).toBe("425a7184012a5403e0431e5ed5161e0bd16115d6eab5132a51d27b66c3830ef6");
    expect(nativeUnit).toBe("m/s2");expect(result.calculation.candidates.length).toBeGreaterThan(0);
    expect(result.calculation.candidates.every((row:{phase:unknown;timing_sigma_s:unknown})=>row.phase===null&&row.timing_sigma_s===null)).toBe(true);
  }
  expect(result.calculation.field_truth).toBeNull();expect(result.calculation.array_descriptors.length).toBeGreaterThan(10);
  const [download]=await Promise.all([page.waitForEvent("download"),page.getByRole("button",{name:"Verify, plot and export all arrays",exact:true}).click()]);
  zip=resolve(evidence,"actual-native-waveform.zip");await download.saveAs(zip);
  await expect(page.locator(".waveform-trace")).toHaveCount(12);
  await expect(page.getByRole("img",{name:`Response amplitude; f [Hz]; ${responseUnit}`,exact:true})).toHaveCount(1);
  await expect(page.getByRole("img",{name:"Response principal phase; f [Hz]; rad",exact:true})).toHaveCount(1);
  await expect(page.getByText("Native physical unit from this StationXML channel:",{exact:false})).toContainText(nativeUnit);
  await page.getByLabel("Reopen saved ZIP against this successful job",{exact:true}).setInputFiles(zip);
  await expect(page.locator(".waveform-trace")).toHaveCount(12);
  const plot=page.getByRole("img",{name:"counts; t [s]; counts",exact:true});
  await plot.scrollIntoViewIfNeeded();const bounds=(await plot.boundingBox())!;
  await page.mouse.move(bounds.x+bounds.width*.6,bounds.y+bounds.height*.5);
  await expect(page.getByText(/Shared time cursor relative to conditioning start:/)).not.toContainText("0.000 s");
  await plot.focus();await page.keyboard.press("Home");
  const first=(result.calculation.channels[0].start_us-waveformUtcUs(result.calculation.request.submitted.conditioning_start_utc))/1e6;
  await expect(page.getByText(/Shared time cursor relative to conditioning start:/)).toContainText(`${first.toFixed(3)} s`);
  await page.keyboard.press("ArrowRight");
  await expect(page.getByText(/Shared time cursor relative to conditioning start:/)).toContainText(`${(first+1/result.calculation.channels[0].sample_rate_hz).toFixed(3)} s`);
  await page.getByRole("button",{name:"Reload project",exact:true}).click();
  await expect(page.getByRole("button",{name:"Verify, plot and export all arrays",exact:true})).toBeEnabled();
  await page.getByLabel("Reopen saved ZIP against this successful job",{exact:true}).setInputFiles(zip);
  await expect(page.locator(".waveform-trace")).toHaveCount(12);expect(errors).toEqual([]);
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
    const chart=(await plot.boundingBox())!;expect(chart.width/width).toBeGreaterThan(width<760?.85:.65);
    const response=page.getByRole("img",{name:`${es?"Amplitud de respuesta":"Response amplitude"}; f [Hz]; ${responseUnit}`,exact:true});
    await response.scrollIntoViewIfNeeded();await expect(response).toBeVisible();
    await page.screenshot({path:resolve(evidence,`${lang}-${theme}-${width}-response.png`)});
    await plot.scrollIntoViewIfNeeded();
    await page.screenshot({path:resolve(evidence,`${lang}-${theme}-${width}.png`)});
    if(width<760)await page.getByRole("button",{name:es?"Controles de procesamiento":"Processing controls",exact:true}).click();
    await page.getByRole("button",{name:es?"Editar solicitud indexada como nuevo borrador":"Edit indexed request as a new draft",exact:true}).click();
    await expect(page.getByLabel(es?"Inicio de acondicionamiento UTC":"Conditioning start UTC",{exact:true})).toHaveValue(request.conditioning_start_utc);
    await page.screenshot({path:resolve(evidence,`${lang}-${theme}-${width}-controls.png`)});
    if(width<760)await page.getByRole("button",{name:es?"Controles de procesamiento":"Processing controls",exact:true}).click();
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
