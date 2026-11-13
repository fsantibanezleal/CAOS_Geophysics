import { test, expect, type BrowserContext, type Page } from "@playwright/test";
import { spawn, execFileSync, type ChildProcess } from "node:child_process";
import { createServer } from "node:net";
import { createHash, randomUUID } from "node:crypto";
import { readFileSync, readdirSync, mkdirSync, writeFileSync } from "node:fs";
import { resolve, join } from "node:path";
import { unzipSync, zipSync } from "fflate";
import { fixture } from "../src/test/fixtures/processing";
import { parseMtResult, type MtResult } from "../src/api/mt-contracts";

// Opt-in actual CPU API/worker review. No route interception or operating-host claim.
test.describe.configure({ mode: "serial", timeout: 240_000 });
// Ordinary Playwright against the owned local server; no native controller gate.
test.use({ headless: false });
test.setTimeout(240_000);
const required = (key: string) => {
  if (!process.env[key]) throw new Error(`Supply trusted existing ${key}`);
  return resolve(process.env[key]!);
};
const checkout = required("GEOPHYSICS_REVIEW_CHECKOUT"), python = required("GEOPHYSICS_REVIEW_PYTHON");
const build = required("GEOPHYSICS_REVIEW_BUILD"), evidence = required("GEOPHYSICS_QA_EVIDENCE");
const ownerDb = required("GEOPHYSICS_OPERATOR_DB_GUARD");
const revision = process.env.GEOPHYSICS_REVIEW_BACKEND_REVISION!;
if (!/^[0-9a-f]{40}$/.test(revision)) throw new Error("Exact backend revision required");
const account = { email: `qa-${randomUUID()}@example.org`, password: randomUUID() + randomUUID() };
let server: ChildProcess, origin: string, context: BrowserContext, page: Page, project: string, qaRoot: string;
let before: Record<string, string>, frontendBefore: Record<string, string>, ownerBefore: string;
let harnessBefore: Record<string, string>;
let browserVersion = "";
let gravityDataset: string, gravityJob: string, gravityResult: unknown, gravityData: unknown;
let mtDataset: string, qcJob: string, inverseJob: string, qc: MtResult, inverse: MtResult;
const results: { name: string; status: string | undefined }[] = [], errors: string[] = [];
const started = new Date().toISOString();
let serverDiagnostics = "";
const sha = (path: string) => createHash("sha256").update(readFileSync(path)).digest("hex");
const shaBytes = (bytes: Uint8Array) => createHash("sha256").update(bytes).digest("hex");
function inventory(root: string, relative = ""): Record<string, string> {
  return Object.fromEntries(readdirSync(join(root, relative), { withFileTypes: true }).flatMap(item => {
    const path = join(relative, item.name);
    return item.isDirectory() ? Object.entries(inventory(root, path)) : [[path.replaceAll("\\", "/"), sha(join(root, path))]];
  }).sort(([a], [b]) => a.localeCompare(b)));
}
function sources() {
  return { ...Object.fromEntries(Object.entries(inventory(join(checkout, "app"))).map(([p, h]) => ["app/" + p, h])),
    ...Object.fromEntries(["edi.py", "electromagnetics.py"].map(p => ["data-pipeline/" + p, sha(join(checkout, "data-pipeline", p))])),
    "data/fixtures/edi/halfspace-100-native.edi": sha(join(checkout, "data/fixtures/edi/halfspace-100-native.edi")) };
}
async function port() {
  const socket = createServer(); await new Promise<void>(done => socket.listen(0, "127.0.0.1", done));
  const address = socket.address(); if (!address || typeof address === "string") throw new Error("No test port");
  await new Promise<void>((done, reject) => socket.close(e => e ? reject(e) : done())); return address.port;
}
async function post(path: string, data?: unknown, form?: Record<string, string>) {
  const token = (await (await context.request.get(origin + "/api/auth/csrf")).json()).csrf_token;
  return context.request.post(origin + path, { headers: { Origin: origin, "X-CSRF-Token": token }, ...(form ? { form } : { data }) });
}
async function json(path: string) {
  const response = await context.request.get(origin + path); expect(response.ok(), await response.text()).toBe(true); return response.json();
}
async function job(dataset: string, method: string, parameters: unknown) {
  const admission = await post(`/api/projects/${project}/jobs`, { dataset_id: dataset, method_id: method, parameters });
  expect(admission.status(), await admission.text()).toBe(202); const id = (await admission.json()).job_id;
  await expect.poll(async () => (await json(`/api/projects/${project}/jobs/${id}`)).state,
    { timeout: 180_000, intervals: [250, 500, 1000] }).toBe("succeeded");
  return id as string;
}
async function upload(buffer: Buffer, name: string, physical: unknown) {
  const token = (await json("/api/auth/csrf")).csrf_token;
  const metadata = { filename: name, format: name.endsWith(".edi") ? "edi" : "gravity_csv",
    mime: name.endsWith(".edi") ? "text/plain" : "text/csv", physical,
    source: { provider: "Independent private QA control", rights_statement: "Private QA only, not a field dataset",
      rights_decision: "provider-link-only", private_storage_permission: "attested", attribution: "QA",
      expected_bytes: buffer.length, expected_sha256: shaBytes(buffer) } };
  const response = await context.request.post(origin + `/api/projects/${project}/assets`, {
    headers: { Origin: origin, "X-CSRF-Token": token, "Content-Type": metadata.mime, "X-Asset-Metadata": JSON.stringify(metadata) }, data: buffer });
  expect(response.status(), await response.text()).toBe(201);
  const validated = await post(`/api/projects/${project}/datasets`, { asset_id: (await response.json()).asset_id });
  expect(validated.status(), await validated.text()).toBe(201); return (await validated.json()).dataset_id as string;
}
const combo = (name: string) => page.getByRole("combobox", { name, exact: true });
async function open(mt: boolean, dataset: string, id: string, es = false, width = 1600) {
  await page.goto(origin + `/?project=${project}${mt ? "&instrument=mt" : ""}`);
  if (width === 390) await page.getByRole("button", { name: mt
    ? es ? "Controles de procesamiento MT" : "MT processing controls"
    : es ? "Controles de procesamiento" : "Processing controls", exact: true }).click();
  await combo(mt ? es ? "Conjunto EDI validado" : "Validated EDI dataset" : es ? "Conjunto validado" : "Validated dataset").selectOption(dataset);
  await combo(es ? "Sección de controles" : "Control section").selectOption("history");
  await combo(mt ? es ? "Trabajo MT" : "MT job" : es ? "Trabajo de procesamiento" : "Processing job").selectOption(id);
  await expect(page.getByTestId(mt ? "mt-instrument" : "processing-instrument")).toBeVisible({ timeout: 20_000 });
}
async function download(button: string, label: string) {
  await expect(page.getByRole("button", { name: button, exact: true })).toBeEnabled({ timeout: 20_000 });
  const [file] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: button, exact: true }).click()]);
  const path = join(evidence, label); await file.saveAs(path); return path;
}
test.beforeAll(async ({ browser }) => {
  browserVersion = browser.version();
  mkdirSync(evidence, { recursive: true }); before = sources(); ownerBefore = sha(ownerDb); frontendBefore = inventory(build);
  harnessBefore = Object.fromEntries(["e2e/scientific-result-views.spec.ts", "e2e/scientific-result-server.py",
    ...["ProjectProcessingWorkbench", "MtProjectWorkbench", "GravityStationInstrument", "MtScientificInstrument", "RecordedMtStates", "ResultBundleInput", "result-view-data"].map(p => `src/components/${p}.${p === "result-view-data" ? "ts" : "tsx"}`)]
    .map(p => [p, sha(resolve(p))]));
  for (const [path, digest] of Object.entries(before)) {
    expect(shaBytes(execFileSync("git", ["show", `${revision}:${path}`], { maxBuffer: 16 * 1048576 }))).toBe(digest);
  }
  const testPort = await port(); origin = `http://127.0.0.1:${testPort}`;
  // Explicit new private C:/E: scratch parent; never source-drive build copies.
  qaRoot = join(required("GEOPHYSICS_QA_STORAGE_PARENT"), "srv-" + randomUUID());
  server = spawn(python, ["-B", resolve("e2e/scientific-result-server.py")], { cwd: checkout, windowsHide: true,
    env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1", PYTHONPATH: checkout,
      GEOPHYSICS_REAL_QA_ROOT: qaRoot, GEOPHYSICS_REAL_QA_ORIGIN: origin,
      GEOPHYSICS_REAL_QA_PORT: String(testPort), GEOPHYSICS_REVIEW_BUILD: build,
      GEOPHYSICS_QA_STORAGE_PARENT: required("GEOPHYSICS_QA_STORAGE_PARENT") }, stdio: ["pipe", "pipe", "pipe"] });
  server.stdin!.end(JSON.stringify({ accounts: [account] }) + "\n"); server.stdout!.resume();
  server.stderr!.on("data", bytes => { serverDiagnostics += String(bytes); });
  await expect.poll(async () => {
    if (server.exitCode !== null) throw new Error(`Local review helper exited ${server.exitCode}: ${serverDiagnostics}`);
    try { return (await fetch(origin + "/api/auth/config")).ok; } catch { return false; }
  }, { timeout: 45_000 }).toBe(true);
  context = await browser.newContext({ acceptDownloads: true, viewport: { width: 1600, height: 900 }, hasTouch: true });
  await context.addInitScript(() => { if (!localStorage.getItem("caos.lang")) localStorage.setItem("caos.lang", "en"); if (!localStorage.getItem("caos.theme")) localStorage.setItem("caos.theme", "light"); });
  page = await context.newPage(); page.on("pageerror", e => errors.push(e.message));
  expect(await json("/api/auth/config")).toEqual({ mode: "local", registration_enabled: false, mail_flows_enabled: false });
  expect((await post("/api/auth/cookie/login", undefined, { username: account.email, password: account.password })).status()).toBe(204);
  const created = await post("/api/projects", { name: "Actual result opening controls", description: "Private CPU QA, not field validation" });
  expect(created.status()).toBe(201); project = (await created.json()).id;
});
test.afterEach(async ({}, info) => { results.push({ name: info.title, status: info.status }); });
test.afterAll(async () => {
  await context?.close();
  if (server?.pid && server.exitCode === null) {
    // Stop only our recorded child process tree; retain QA files and receipts.
    execFileSync(python, ["-B", "-c", "import sys,psutil\ntry:\n p=psutil.Process(int(sys.argv[1])); c=p.children(recursive=True)\n for x in c:\n  try: x.terminate()\n  except psutil.NoSuchProcess: pass\n psutil.wait_procs(c,timeout=5)\n p.terminate(); p.wait(timeout=10)\nexcept psutil.NoSuchProcess: pass", String(server.pid)]);
  }
  if (!before) return;
  writeFileSync(join(evidence, "server-diagnostics.txt"), serverDiagnostics);
  const after = sources(), frontendAfter = inventory(build), ownerAfter = sha(ownerDb);
  const harnessAfter = Object.fromEntries(Object.keys(harnessBefore ?? {}).map(p => [p, sha(resolve(p))]));
  writeFileSync(join(evidence, "source-storage-and-outcomes.json"), JSON.stringify({
    schema: "geophysics.scientific-result-http-review/v1", started_utc: started, completed_utc: new Date().toISOString(),
    backend_revision: revision, source_before: before, source_after: after, source_unchanged: JSON.stringify(before) === JSON.stringify(after),
    build_before: frontendBefore, build_after: frontendAfter, harness_before: harnessBefore, harness_after: harnessAfter,
    operator_db_before: ownerBefore, operator_db_after: ownerAfter, qa_root: qaRoot, tests: results, browser_errors: errors,
    browser_version: browserVersion, visibility_profile: process.env.GEOPHYSICS_VISIBILITY_PROFILE ?? "headless",
    actual_http: true, api_interception: false, mt_enabled_in_private_cpu_qa_only: true, host_or_field_acceptance: false,
    credentials_recorded: false, cleanup: "Owned processes only; source, QA DB and receipts retained" }, null, 2));
  expect(after).toEqual(before); expect(frontendAfter).toEqual(frontendBefore);
  if (harnessBefore) expect(harnessAfter).toEqual(harnessBefore);
  expect(ownerAfter).toBe(ownerBefore); expect(errors).toEqual([]);
});

test("actual flag / M05 / M06 CPU worker results and original verified exports", async () => {
  const f = fixture();
  gravityDataset = await upload(Buffer.from("station,x,y,z,g,sigma\nA,500000,6200000,100,-1.25,0.1\nB,500010,6200010,101,2.375,0.2\nC,500020,6200000,102,3.125,0.15\nD,500030,6200010,103,4.0625,0.3\nE,500040,6200000,104,100.5,0.125\n"), "signed-survey.csv", f.dataset.physical_metadata);
  gravityJob = await job(gravityDataset, "gravity.station-outlier-flags/v1", { threshold: 6 });
  gravityResult = await json(`/api/projects/${project}/jobs/${gravityJob}/result`);
  gravityData = await json(`/api/projects/${project}/datasets/${gravityDataset}`);
  mtDataset = await upload(readFileSync(join(checkout, "data/fixtures/edi/halfspace-100-native.edi")), "halfspace-100-native.edi", {
    coordinate_reference: "local", local_crs: "source EDI station coordinates", axis_order: "xy", horizontal_datum: "source EDI frame",
    vertical_datum: "source EDI elevation", vertical_positive: "up", horizontal_unit: "m", vertical_unit: "m",
    measurement_unit: "mV/km/nT", epoch_utc: "2026-09-28T00:00:00Z", component_frame: "instrument axes",
    geometry: { station_id: "HALFSPACE_100_NATIVE", frequency_count: 24, tensor_components: ["Zxx", "Zxy", "Zyx", "Zyy"], rotation_degrees: 0, rotation_reference: "unspecified", sign_convention: "+", variance_convention: "complex" } });
  qcJob = await job(mtDataset, "mt.edi-full-tensor-qc/v1", {});
  qc = parseMtResult(await json(`/api/projects/${project}/jobs/${qcJob}/result`)); expect(qc.inverse).toBeNull();
  inverseJob = await job(mtDataset, "mt.edi-fixed-thickness-trf/v1", { qc_job_id: qcJob, thickness_m: [], initial_ohm_m: [40], beta: 0.001, bootstrap_samples: 20, seed: 71401 });
  inverse = parseMtResult(await json(`/api/projects/${project}/jobs/${inverseJob}/result`));
  expect(inverse.truth).toBeNull(); expect(inverse.inverse!.methods["mt-lm"].frames.length).toBeGreaterThan(2);
  // Persist actual computations even if a later UI control fails.
  writeFileSync(join(evidence, "actual-results.json"), JSON.stringify({ gravityResult, gravityData, qc, inverse }, null, 2));
  for (const [mt, dataset, id, label] of [[false, gravityDataset, gravityJob, "gravity"], [true, mtDataset, qcJob, "m05"], [true, mtDataset, inverseJob, "m06"]] as const) {
    await open(mt, dataset, id);
    const path = await download(mt ? "Verify & export MT ZIP" : "Verify & export processing ZIP", label + ".zip");
    const verification = execFileSync(python, ["-B", "-c", "import sys,json; from pathlib import Path; from app.bundle import verify_bundle; print(json.dumps(verify_bundle(Path(sys.argv[1]).read_bytes())))", path], { cwd: checkout, env: { ...process.env, PYTHONPATH: checkout, PYTHONDONTWRITEBYTECODE: "1" }, encoding: "utf8" });
    writeFileSync(join(evidence, label + "-bundle-verified.json"), verification);
    expect(JSON.parse(verification)).toBeTruthy();
  }
  writeFileSync(join(evidence, "actual-results.json"), JSON.stringify({ gravityResult, gravityData, qc, inverse }, null, 2));
});

test("saved original / foreign / tampered results never write API or replace verified selection", async () => {
  await open(true, mtDataset, inverseJob); await combo("Control section").selectOption("open");
  const writes: string[] = [], listener = (request: { method(): string; url(): string }) => { if (request.method() !== "GET" && request.url().includes("/api/")) writes.push(request.url()); };
  page.on("request", listener);
  const file = page.getByLabel("Open saved ZIP for selected job", { exact: true });
  await file.setInputFiles(join(evidence, "m06.zip"));
  await expect(page.getByRole("status").filter({ hasText: "Saved ZIP verified" })).toBeVisible();
  const original = unzipSync(readFileSync(join(evidence, "m06.zip")));
  const modified = JSON.parse(new TextDecoder().decode(original["result.json"])); modified.engine_sha256 = "d".repeat(64);
  original["result.json"] = new TextEncoder().encode(JSON.stringify(modified));
  await file.setInputFiles({ name: "tampered.zip", mimeType: "application/zip", buffer: Buffer.from(zipSync(original, { level: 0 })) });
  await expect(page.getByRole("alert")).toContainText("Saved file rejected");
  await file.setInputFiles(join(evidence, "m05.zip"));
  await expect(page.getByRole("alert")).toContainText("Saved file rejected");
  await expect(page.getByTestId("mt-frequency-readout")).toContainText(String(inverse.frequency_hz[0]));
  await file.setInputFiles({ name: "too-large.zip", mimeType: "application/zip", buffer: Buffer.alloc(17 * 1048576 + 1) });
  await expect(page.getByRole("alert")).toContainText("17-MiB");
  page.off("request", listener); expect(writes).toEqual([]);
  await open(false, gravityDataset, gravityJob); await combo("Control section").selectOption("open");
  await page.getByLabel("Open saved ZIP for selected job", { exact: true }).setInputFiles(join(evidence, "gravity.zip"));
  await expect(page.getByRole("status").filter({ hasText: "Saved ZIP verified" })).toBeVisible();
});

test("stale local byte read is discarded after selecting a different successful job", async () => {
  await open(true, mtDataset, inverseJob); await combo("Control section").selectOption("open");
  // Delay only the local File read. Real APIs and physics remain untouched.
  await page.evaluate(() => {
    const original = File.prototype.arrayBuffer;
    const target = window as unknown as { resumeLocalRead: () => void };
    File.prototype.arrayBuffer = function() { const file = this; File.prototype.arrayBuffer = original; return new Promise<ArrayBuffer>(done => { target.resumeLocalRead = () => { void original.call(file).then(done); }; }); };
  });
  await page.getByLabel("Open saved ZIP for selected job", { exact: true }).setInputFiles(join(evidence, "m06.zip"));
  await expect(page.getByRole("status").filter({ hasText: "Verifying original" })).toBeVisible();
  await combo("Control section").selectOption("history"); await combo("MT job").selectOption(qcJob);
  await expect(combo("Scientific view").locator("option")).toHaveCount(2);
  await page.evaluate(() => (window as unknown as { resumeLocalRead: () => void }).resumeLocalRead());
  await expect(combo("Scientific view").locator("option")).toHaveCount(2);
  await page.getByText("Exact selected response / residual values", { exact: true }).click();
  const saved = JSON.parse(readFileSync(await download("Export exact inspection JSON", "stale-after-switch.json"), "utf8"));
  expect(saved.result).toEqual(qc); expect(saved.result.inverse).toBeNull();
});

test("exact linked signed values / literal state exports and playback controls", async () => {
  await open(true, mtDataset, inverseJob);
  const response = page.getByRole("group", { name: "Observed and predicted response", exact: true });
  await response.focus(); await response.press("End"); await expect(combo("Selected frequency")).toHaveValue("23");
  const rect = (await response.boundingBox())!;
  await page.mouse.move(rect.x + rect.width * .4, rect.y + rect.height * .5);
  const pointed = Number(await combo("Selected frequency").inputValue());
  await expect(page.getByTestId("mt-frequency-readout")).toContainText(String(inverse.frequency_hz[pointed]));
  await page.getByText("Exact selected response / residual values", { exact: true }).click();
  await combo("Selected frequency").selectOption("4");
  const snapshot = JSON.parse(readFileSync(await download("Export exact inspection JSON", "m06-inspection.json"), "utf8"));
  expect(snapshot.result).toEqual(inverse); expect(snapshot.selected.index).toBe(4); expect(snapshot.selected.partition).toBe("heldout");
  for (const c of ["xy", "yx"] as const) {
    const obs = inverse.screen.observed[c], pred = inverse.inverse!.methods["mt-lm"].predicted;
    expect(snapshot.selected.components[c].residual.real).toBe(obs.real[4] - pred.real[4]);
    expect(snapshot.selected.components[c].standardized_residual.imag).toBe((obs.imag[4] - pred.imag[4]) / obs.sigma_real_imag_ohm[4]);
    await expect(page.getByTestId("mt-exact-values")).toContainText(String(obs.real[4]));
  }
  await combo("Scientific view").selectOption("solver");
  const range = page.getByLabel("Recorded evaluation index [1]", { exact: true }), m = inverse.inverse!.methods["mt-lm"], last = m.frames.length - 1;
  await page.getByRole("button", { name: "Next recorded state", exact: true }).click(); await expect(range).toHaveValue("1");
  await page.getByRole("button", { name: "Play recorded states", exact: true }).click();
  await expect.poll(() => range.inputValue()).not.toBe("1");
  await page.getByRole("button", { name: "Pause recorded states", exact: true }).click();
  const paused = await range.inputValue(); await page.waitForTimeout(650); await expect(range).toHaveValue(paused);
  await range.focus(); await range.press("End"); await expect(range).toHaveValue(String(last));
  const state = JSON.parse(readFileSync(await download("Export recorded state JSON", "recorded-final.json"), "utf8"));
  expect(state.state).toEqual(m.states[last]); expect(state.model_ohm_m).toEqual(m.frames[last]); expect(state.objective).toBe(m.history[last]); expect(state.historical_prediction).toBeNull();
  await expect(page.getByRole("button", { name: "Play recorded states", exact: true })).toBeDisabled();
  await page.getByRole("button", { name: "Reset recorded state", exact: true }).click(); await expect(range).toHaveValue("0");
  await range.press("End"); await range.press("ArrowLeft"); await expect(range).toHaveValue(String(last - 1));
  await page.getByRole("button", { name: "Play recorded states", exact: true }).click(); await expect(range).toHaveValue(String(last));
  await page.waitForTimeout(650); await expect(range).toHaveValue(String(last)); // no looping
  await page.getByRole("button", { name: "Reset recorded state", exact: true }).click();
  await page.getByRole("button", { name: "Play recorded states", exact: true }).click();
  const objective = page.getByRole("group", { name: "Objective per recorded residual evaluation", exact: true });
  await objective.focus(); await objective.press("Home"); await expect(range).toHaveValue("0");
  await expect(page.getByRole("button", { name: "Play recorded states", exact: true })).toHaveAttribute("aria-pressed", "false");
  await page.waitForTimeout(650); await expect(range).toHaveValue("0");
  await page.getByRole("button", { name: "Play recorded states", exact: true }).click();
  await page.emulateMedia({ reducedMotion: "reduce" }); await expect(page.getByRole("button", { name: "Play recorded states", exact: true })).toBeDisabled();
  await range.focus(); await range.press("Home"); await range.press("ArrowRight"); await expect(range).toHaveValue("1");
  await page.emulateMedia({ reducedMotion: "no-preference" });
  await page.getByRole("button", { name: "Play recorded states", exact: true }).click();
  await combo("Scientific view").selectOption("response"); await combo("Scientific view").selectOption("solver"); await expect(range).toHaveValue("0");
  await open(false, gravityDataset, gravityJob);
  const gravity = JSON.parse(readFileSync(await download("Export exact inspection JSON", "gravity-inspection.json"), "utf8"));
  expect(gravity.dataset).toEqual(gravityData); expect(gravity.result).toEqual(gravityResult);
  expect(gravity.prediction).toBeNull(); expect(gravity.residual).toBeNull(); expect(gravity.model).toBeNull();
});

test("EN / ES themes and four viewport sizes preserve seven MT views and gravity", async () => {
  test.setTimeout(240_000);
  for (const lang of ["en", "es"]) for (const theme of ["light", "dark"]) for (const [width, height] of [[1280,800], [1600,900], [2560,1440], [390,844]]) {
    const es = lang === "es"; await page.setViewportSize({ width, height });
    await page.evaluate(({ lang, theme }) => { localStorage.setItem("caos.lang", lang); localStorage.setItem("caos.theme", theme); }, { lang, theme });
    await open(true, mtDataset, inverseJob, es, width);
    if (width === 390) await page.getByRole("button", { name: es ? "Controles de procesamiento MT" : "MT processing controls", exact: true }).click();
    for (const view of ["response", "tensor", "residual", "model", "protocol", "uncertainty", "solver"]) {
      await combo(es ? "Vista científica" : "Scientific view").selectOption(view);
      await expect(page.getByTestId("mt-frequency-readout")).toBeVisible();
      const main = page.locator(".processing-main"); await main.evaluate(el => { el.scrollTop = 0; });
      expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
      for (const graph of await main.locator('svg[role="group"]').all()) {
        await graph.scrollIntoViewIfNeeded(); await graph.focus(); await graph.press("End");
        expect(await graph.getAttribute("data-selected-index")).not.toBeNull();
        const rect = (await graph.boundingBox())!; expect(rect.width).toBeGreaterThan(0); expect(rect.x).toBeGreaterThanOrEqual(-1); expect(rect.x + rect.width).toBeLessThanOrEqual(width + 1);
      }
      await page.screenshot({ path: join(evidence, `${lang}-${theme}-${width}-${view}.png`) });
    }
    await page.getByText(es ? "Valores exactos de respuesta / residuo seleccionado" : "Exact selected response / residual values", { exact: true }).click();
    await expect(page.getByTestId("mt-exact-values")).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    for (const cell of await page.getByTestId("mt-exact-values").locator("td").all()) expect(await cell.evaluate(el => getComputedStyle(el).whiteSpace)).toBe("nowrap");
    await page.screenshot({ path: join(evidence, `${lang}-${theme}-${width}-exact.png`) });
    await open(false, gravityDataset, gravityJob, es, width);
    if (width === 390) await page.getByRole("button", { name: es ? "Controles de procesamiento" : "Processing controls", exact: true }).click();
    await page.getByRole("button", { name: es ? "Exportar inspección exacta JSON" : "Export exact inspection JSON", exact: true }).scrollIntoViewIfNeeded();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    await page.screenshot({ path: join(evidence, `${lang}-${theme}-${width}-gravity.png`) });
  }
});
