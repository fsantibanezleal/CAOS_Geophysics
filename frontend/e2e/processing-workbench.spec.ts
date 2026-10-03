import { test, expect, type BrowserContext, type Page, type APIRequestContext } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { fixture } from "../src/test/fixtures/processing";

// Independent numerical control uploaded by a real owner; not a release dataset.
const origin = "http://127.0.0.1:8876", email = "processing-owner@example.org", password = "a separate long QA password";
const evidence = resolve("node_modules/.processing-qa/evidence");
mkdirSync(evidence,{recursive:true});
const csv = (values = [1,2,3,4,100], sigma = .1) => "station,x,y,z,g,sigma\n" + values.map((g,i) => `S${i+1},${500000+i*10},${6200000+(i%2)*10},100,${g},${sigma}`).join("\n") + "\n";
let context: BrowserContext, page: Page, projectId: string, datasetId: string, successJob: string;
test.describe.configure({mode:"serial"});

async function unsafe(request: APIRequestContext, path: string, data?: unknown, form?: Record<string,string>) {
  const csrf = await (await request.get(origin+"/api/auth/csrf")).json();
  return request.post(origin+path,{headers:{Origin:origin,"X-CSRF-Token":csrf.csrf_token},...(form ? {form} : data === undefined ? {} : {data})});
}
async function login() {
  expect((await unsafe(context.request,"/api/auth/cookie/login",undefined,{username:email,password})).ok()).toBe(true);
}
const combo = (name: string) => page.getByRole("combobox",{name,exact:true});
async function section(name: string) {await combo("Control section").selectOption(name);}
async function additionalOriginal(name: string, values: number[], sigma = .1) {
  const buffer = Buffer.from(csv(values,sigma));
  const metadata = {filename:name,format:"gravity_csv",mime:"text/csv",physical:fixture().dataset.physical_metadata,
    source:{provider:"QA survey owner",doi:null,citation:null,rights_statement:"Private independent QA control",rights_decision:"provider-link-only",private_storage_permission:"attested",attribution:"QA survey",expected_bytes:buffer.length,expected_sha256:createHash("sha256").update(buffer).digest("hex")}};
  const csrf = await (await context.request.get(origin+"/api/auth/csrf")).json();
  const response = await context.request.post(origin+`/api/projects/${projectId}/assets`,{headers:{Origin:origin,"X-CSRF-Token":csrf.csrf_token,"Content-Type":"text/csv","X-Asset-Metadata":JSON.stringify(metadata)},data:buffer});
  expect(response.ok(),await response.text()).toBe(true); return (await response.json()).asset_id as string;
}

test.beforeAll(async ({browser}) => {
  context = await browser.newContext({viewport:{width:1440,height:900},acceptDownloads:true});
  await context.addInitScript(() => {try {if (!localStorage.getItem("caos.lang")) localStorage.setItem("caos.lang","en"); if (!localStorage.getItem("caos.theme")) localStorage.setItem("caos.theme","light");} catch { /* about:blank has no storage */ }});
  page = await context.newPage();
  expect((await context.request.get(origin+"/__qa/processing")).ok()).toBe(true);
  expect((await unsafe(context.request,"/api/auth/register",{email,password})).ok()).toBe(true);
  const {token} = await (await context.request.get(origin+"/__qa/mail/latest")).json();
  expect((await unsafe(context.request,"/api/auth/verify/verify",{token})).ok()).toBe(true);
});
test.afterAll(async () => {await context?.close();});

test("owner upload to flag result and verified export", async () => {
  await page.goto(origin+"/"); await page.getByRole("button",{name:"Projects & raw data",exact:true}).click();
  await page.getByLabel("Email",{exact:true}).fill(email); await page.getByLabel("Password",{exact:true}).fill(password); await page.getByRole("button",{name:"Sign in",exact:true}).click();
  await page.getByLabel("Project name",{exact:true}).fill("Five-station QC control"); await page.getByLabel("Description",{exact:true}).fill("Independent QA, not a scientific benchmark");
  await page.getByRole("button",{name:"Create project",exact:true}).click();
  await page.getByLabel("Local original file",{exact:true}).setInputFiles({name:"control.csv",mimeType:"text/csv",buffer:Buffer.from(csv())});
  await combo("Declared raw format").selectOption("gravity_csv");
  for (const [name,value] of [["Provider or acquisition owner","QA survey owner"],["Rights statement and permission basis","Private independent QA control"],["Required attribution","QA survey"],["EPSG code","32719"],["Horizontal datum (exact declared name)","WGS84"],["Vertical datum","survey benchmark"],["Acquisition epoch with UTC offset (ISO 8601)","2026-10-03T12:00:00Z"],["Station ID column","station"],["X column","x"],["Y column","y"],["Z column","z"],["Value column","g"],["Sigma column (required for flag QC)","sigma"]]) {
    if (name === "EPSG code") await combo("Coordinate reference").selectOption("epsg");
    await page.getByLabel(name,{exact:true}).fill(value);
  }
  await combo("Public rights decision (does not publish this upload)").selectOption("provider-link-only"); await page.getByRole("dialog").getByRole("checkbox").check();
  for (const [name,value] of [["Coordinate axis order","xy"],["Positive vertical direction","up"],["Horizontal coordinate unit","m"],["Vertical coordinate unit","m"],["Measurement unit","mGal"],["Component orientation/frame","local vertical down"]]) await combo(name).selectOption(value);
  await page.getByRole("button",{name:"Upload original bytes",exact:true}).click(); await expect(page.getByRole("heading",{name:"Owner upload receipt"})).toBeVisible();
  await page.getByRole("button",{name:"Open processing workbench"}).click();
  projectId = new URL(page.url()).searchParams.get("project")!;
  await page.getByRole("button",{name:"Validate station table"}).click(); await expect(page.getByTestId("processing-instrument")).toBeVisible();
  datasetId = await combo("Validated dataset").inputValue();
  await expect(page.getByTestId("station-readout")).toContainText("g 1 ± 0.1 mGal");
  await combo("API method verdict").selectOption("M01"); await expect(page.getByRole("button",{name:"Submit flag QC job"})).toBeDisabled();
  await combo("API method verdict").selectOption("gravity.station-outlier-flags/v1");
  await page.getByLabel("Robust-score threshold [1]",{exact:true}).fill("1");
  expect((await context.request.post(origin+"/__qa/worker/start")).ok()).toBe(true);
  await page.getByRole("button",{name:"Submit flag QC job"}).click(); await expect(page.getByTestId("job-status")).toHaveText("Succeeded");
  await expect(page.getByTestId("qc-summary")).toContainText("Flagged 2/5"); await expect(page.getByTestId("qc-summary")).toContainText("Submitted threshold 1");
  successJob = await combo("Processing job").inputValue();
  const actual = await (await context.request.get(origin+`/api/projects/${projectId}/jobs/${successJob}/result`)).json();
  expect(actual.observed_mgal).toEqual([1,2,3,4,100]); expect(actual.sigma_mgal).toEqual([.1,.1,.1,.1,.1]); expect(actual.outlier_flag).toEqual([true,false,false,false,true]); expect(actual).not.toHaveProperty("residual");
  const [download] = await Promise.all([page.waitForEvent("download"),page.getByRole("button",{name:"Verify & export processing ZIP"}).click()]);
  const zip = resolve(evidence,"actual-processing-export.zip"); await download.saveAs(zip);
  const verification = execFileSync(resolve("../.venv-api/Scripts/python.exe"),["-c","import sys,json; from pathlib import Path; from app.bundle import verify_bundle; print(json.dumps(verify_bundle(Path(sys.argv[1]).read_bytes())))",zip],{cwd:resolve(".."),encoding:"utf8"});
  expect(JSON.parse(verification)).toBeTruthy(); await expect(page.getByRole("status").filter({hasText:"Export member hashes"})).toBeVisible();
});

test("queued cancellation and poll recovery", async () => {
  // A real running worker can claim immediately; block its next claim with the
  // API's actual queued state by stopping it only in the loopback QA harness.
  expect((await context.request.post(origin+"/__qa/worker/stop")).ok()).toBe(true);
  await section("run"); await page.getByLabel("Robust-score threshold [1]",{exact:true}).fill("6");
  await page.getByRole("button",{name:"Submit flag QC job"}).click(); await expect(page.getByTestId("job-status")).toHaveText("Queued");
  await expect(page.getByTestId("qc-summary")).toHaveCount(0);
  await page.route(`**/api/projects/${projectId}/jobs`,route => route.request().method() === "GET" ? route.abort("failed") : route.continue());
  await expect(page.getByRole("button",{name:"Resume status check"})).toBeVisible();
  await page.unroute(`**/api/projects/${projectId}/jobs`);
  await page.getByRole("button",{name:"Resume status check"}).click();
  await page.getByRole("button",{name:"Cancel job",exact:true}).click(); await expect(page.getByTestId("job-status")).toHaveText("Cancelled");
  await expect(page.getByRole("button",{name:"Verify & export processing ZIP"})).toBeDisabled();
  expect((await context.request.post(origin+"/__qa/worker/start")).ok()).toBe(true);
});

test("invalid rows and failed processing remain non-success", async () => {
  const invalid = await additionalOriginal("invalid-sigma.csv",[1,2,3,4,100],0);
  const zeroMad = await additionalOriginal("zero-mad.csv",[1,1,1,1,1]);
  await section("data"); await page.getByRole("button",{name:"Refresh project data"}).click();
  await combo("Stored original").selectOption(invalid); await page.getByRole("button",{name:"Validate station table"}).click();
  await expect(page.getByRole("alert").filter({hasText:"dataset_uncertainty_invalid"})).toContainText("positive sigma");
  await combo("Stored original").selectOption(zeroMad); await page.getByRole("button",{name:"Validate station table"}).click();
  await expect(page.getByTestId("station-readout")).toContainText("g 1 ± 0.1");
  await page.getByRole("button",{name:"Submit flag QC job"}).click(); await expect(page.getByTestId("job-status")).toHaveText("Failed");
  await expect(page.getByRole("alert")).toContainText("degenerate_mad_scale"); await expect(page.getByTestId("qc-summary")).toHaveCount(0);
  await expect(page.getByRole("button",{name:"Verify & export processing ZIP"})).toBeDisabled();
  await combo("Validated dataset").selectOption(datasetId); await combo("Processing job").selectOption(successJob); await expect(page.getByTestId("qc-summary")).toBeVisible();
});

test("linked station controls and viewport fit", async () => {
  await combo("Selected station").selectOption("4"); await expect(page.getByTestId("station-readout")).toContainText("S5");
  const plan = page.getByRole("img",{name:"Station geometry",exact:true}); await plan.focus(); await plan.press("ArrowLeft"); await expect(page.getByTestId("station-readout")).toContainText("S4");
  const measurement = page.getByRole("img",{name:"Observed gravity and σ",exact:true});
  const rect = (await measurement.boundingBox())!;
  await page.mouse.move(rect.x+rect.width*.91,rect.y+rect.height*.5); await expect(page.getByTestId("station-readout")).toContainText("S5");
  const firstTicks = await measurement.locator("text").allTextContents();
  await page.mouse.move(rect.x+rect.width*.30,rect.y+rect.height*.25); await page.mouse.down(); await page.mouse.move(rect.x+rect.width*.85,rect.y+rect.height*.80); await page.mouse.up();
  expect(await measurement.locator("text").allTextContents()).not.toEqual(firstTicks);
  await combo("Drag action · Observed gravity and σ").selectOption("pan");
  const zoomedTicks = await measurement.locator("text").allTextContents();
  await page.mouse.move(rect.x+rect.width*.6,rect.y+rect.height*.5); await page.mouse.down(); await page.mouse.move(rect.x+rect.width*.7,rect.y+rect.height*.5); await page.mouse.up();
  expect(await measurement.locator("text").allTextContents()).not.toEqual(zoomedTicks);
  await measurement.press("Home"); expect(await measurement.locator("text").allTextContents()).toEqual(firstTicks);
  await page.getByRole("button",{name:"Zoom in · Station geometry",exact:true}).click(); await plan.press("Home");
  await combo("Measurement view").selectOption("scores"); await expect(page.getByRole("img",{name:"Robust QC scores",exact:true})).toBeVisible();
  await page.screenshot({path:resolve(evidence,"en-returned-scores.png")});
  await page.getByRole("button",{name:"Station table",exact:true}).click(); await expect(page.getByRole("table")).toContainText("100"); await page.getByRole("button",{name:"S5",exact:true}).click();
  await page.getByRole("button",{name:"Show plots",exact:true}).click();
  for (const lang of ["en","es"]) for (const theme of ["light","dark"]) for (const [width,height] of [[1280,800],[1600,900],[2560,1440],[390,844]]) {
    await page.setViewportSize({width,height}); await page.evaluate(({lang,theme}) => {localStorage.setItem("caos.lang",lang); localStorage.setItem("caos.theme",theme);}, {lang,theme});
    await page.reload(); await expect(page.getByTestId("processing-instrument")).toBeVisible();
    if (width <= 760) await page.getByRole("button",{name:lang === "es" ? "Controles de procesamiento" : "Processing controls",exact:true}).click();
    await combo(lang === "es" ? "Conjunto validado" : "Validated dataset").selectOption(datasetId);
    await combo(lang === "es" ? "Sección de controles" : "Control section").selectOption("history"); await combo(lang === "es" ? "Trabajo de procesamiento" : "Processing job").selectOption(successJob);
    if (width <= 760) await page.getByRole("button",{name:lang === "es" ? "Controles de procesamiento" : "Processing controls",exact:true}).click();
    await expect(page.getByTestId("qc-summary")).toBeVisible();
    await expect(page.locator("html")).toHaveAttribute("data-theme",theme);
    await expect(page.getByRole("img",{name:lang === "es" ? "Geometría de estaciones" : "Station geometry",exact:true})).toBeVisible();
    await page.screenshot({path:resolve(evidence,`${lang}-${theme}-${width}.png`)});
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth+2)).toBe(true);
    const navigation = page.getByRole("navigation",{name:"Inverse Earth Studio"}); await expect(navigation.getByRole("link")).toHaveCount(6);
    if (width > 760) expect(await page.evaluate(() => document.documentElement.scrollHeight <= innerHeight+2)).toBe(true);
    if (width <= 760) {
      const noOverlap = await page.locator(".processing-instrument").evaluate(element => {
        const charts = element.querySelector(".processing-charts")!.getBoundingClientRect(), note = element.querySelector(".plot-note")!.getBoundingClientRect();
        return note.top >= charts.bottom - 2;
      }); expect(noOverlap).toBe(true);
      const observations = page.getByRole("img",{name:lang === "es" ? "Gravedad observada y σ" : "Observed gravity and σ",exact:true});
      await observations.scrollIntoViewIfNeeded();
      const plotBounds = (await observations.boundingBox())!, mainBounds = (await page.locator(".processing-main").boundingBox())!;
      expect(plotBounds.y).toBeGreaterThanOrEqual(mainBounds.y-2); expect(plotBounds.y+plotBounds.height).toBeLessThanOrEqual(mainBounds.y+mainBounds.height+2);
      await page.screenshot({path:resolve(evidence,`${lang}-${theme}-${width}-observations.png`)});
    } else {
      const area = await page.getByTestId("processing-instrument").boundingBox();
      expect(area!.width*area!.height/(width*height)).toBeGreaterThan(.45);
    }
  }
  await page.setViewportSize({width:1440,height:900}); await page.evaluate(() => {localStorage.setItem("caos.lang","en");}); await page.reload();
  const touchContext = await context.browser()!.newContext({viewport:{width:390,height:844},hasTouch:true});
  await touchContext.addCookies(await context.cookies());
  const touchPage = await touchContext.newPage(); await touchPage.goto(origin+`/?project=${projectId}`);
  await touchPage.getByRole("button",{name:"Processing controls",exact:true}).click();
  await touchPage.getByRole("combobox",{name:"Validated dataset",exact:true}).selectOption(datasetId);
  await touchPage.getByRole("button",{name:"Processing controls",exact:true}).click();
  const touchPlot = touchPage.getByRole("img",{name:"Observed gravity and σ",exact:true}); await touchPlot.scrollIntoViewIfNeeded();
  const touchRect = (await touchPlot.boundingBox())!; await touchPage.touchscreen.tap(touchRect.x+touchRect.width*.91,touchRect.y+touchRect.height*.5);
  await expect(touchPage.getByTestId("station-readout")).toContainText("S5"); await touchContext.close();
});

test("direct project hydration and session boundary", async () => {
  await page.goto(origin+`/?project=${projectId}`); await expect(page.getByTestId("processing-instrument")).toBeVisible();
  await page.getByRole("navigation",{name:"Inverse Earth Studio"}).getByRole("link",{name:"Introduction",exact:true}).click();
  await expect(page).toHaveURL(/\/introduction/); await page.goBack(); await expect(page.getByTestId("processing-instrument")).toBeVisible();
  await unsafe(context.request,"/api/auth/cookie/logout"); await section("data"); await page.getByRole("button",{name:"Refresh project data"}).click();
  await expect(page.getByTestId("processing-instrument")).toHaveCount(0); await expect(page.getByText("Sign in through Projects to load this private project.")).toBeVisible();
  await login(); await page.getByRole("button",{name:"Retry project load"}).click(); await expect(page.getByTestId("processing-instrument")).toBeVisible();
  const guest = await context.browser()!.newContext(); const other = await guest.newPage(); await other.goto(origin+`/?project=${projectId}`); await expect(other.getByTestId("processing-instrument")).toHaveCount(0); await guest.close();
  await page.getByRole("button",{name:"Projects & raw data",exact:true}).click(); await combo("Project workspace section").selectOption("account"); await page.getByRole("button",{name:"Sign out",exact:true}).click();
  await expect(page.getByTestId("processing-instrument")).toHaveCount(0); expect(new URL(page.url()).searchParams.has("project")).toBe(false);
});
