import { expect, test, type Locator, type Page } from "@playwright/test";
import { mkdirSync, readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative } from "node:path";
import { unzipSync } from "fflate";
import { createHash } from "node:crypto";

const fixture = process.env.GEOPHYSICS_JOINT_OUTPUT_FIXTURE, url = process.env.GEOPHYSICS_JOINT_INSPECTION_URL;
const evidence = process.env.GEOPHYSICS_BROWSER_EVIDENCE_ROOT;
const maximum = process.env.GEOPHYSICS_JOINT_MAX_OUTPUT_FIXTURE, aborted = process.env.GEOPHYSICS_JOINT_ABORT_FIXTURE;
const durableAbort = process.env.GEOPHYSICS_JOINT_DURABLE_ABORT_FIXTURE;
async function pointer(page: Page, target: Locator) {
  await target.evaluate(n => n.scrollIntoView({ block: "center", inline: "nearest", behavior: "instant" }));
  const box = await target.boundingBox(); if (!box) throw new Error("No pointer target");
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 5 }); await page.mouse.down(); await page.mouse.up();
}
for (const lang of ["en", "es"] as const) for (const theme of ["light", "dark"] as const) for (const phone of [false, true]) {
  test(`actual supplied result inspection ${lang} ${theme} ${phone ? "phone" : "desktop"}`, async ({ browser }) => {
    test.skip(!fixture || !url || !evidence, "Explicit external actual workflow, inspection URL and evidence root required; no fixture means no browser acceptance");
    test.setTimeout(120_000); mkdirSync(evidence!, { recursive: true });
    const context = await browser.newContext({ viewport: phone ? { width: 390, height: 844 } : { width: 1600, height: 900 }, reducedMotion: "reduce", acceptDownloads: true });
    await context.addInitScript(({ lang, theme }) => { localStorage.setItem("caos.lang", lang); localStorage.setItem("caos.theme", theme); }, { lang, theme });
    const page = await context.newPage(), errors: string[] = [], external: string[] = [], writes: string[] = [];
    page.on("pageerror", e => errors.push(e.message)); page.on("console", m => { if (m.type() === "error") errors.push(m.text()); });
    page.on("request", r => { if (new URL(r.url()).origin !== new URL(url!).origin) external.push(r.url()); if (r.method() !== "GET") writes.push(r.url()); });
    await page.goto(`${url}${url!.includes("?") ? "&" : "?"}lang=${lang}&theme=${theme}`);
    const tool = page.getByTestId("joint-result-workbench"), importLabel = lang === "en" ? "Import local workflow output directory" : "Importar directorio local de resultados";
    await expect(tool).toBeVisible(); await tool.getByLabel(importLabel, { exact: true }).setInputFiles(fixture!);
    await expect(tool.getByTestId("joint-response-readout")).toBeVisible({ timeout: 30_000 });
    await expect(tool.getByTestId("joint-workflow-boundary")).toContainText(lang === "en" ? "scientific gates remain separate" : "criterios científicos permanecen separados");
    const view = tool.getByLabel(lang === "en" ? "Joint scientific view" : "Vista científica conjunta", { exact: true });
    const stem = `${lang}-${theme}-${phone ? "phone" : "desktop"}`;
    for (const m of ["gravity", "magnetic"]) for (const partition of ["training", "validation", "sealed"]) {
      await tool.getByLabel(lang === "en" ? "Survey response" : "Respuesta de levantamiento", { exact: true }).selectOption(m);
      await tool.getByLabel(lang === "en" ? "Frozen partition" : "Partición congelada", { exact: true }).selectOption(partition);
      await expect(tool.getByTestId("joint-response-readout")).toContainText(m === "gravity" ? "mGal" : "nT");
      await tool.getByLabel(lang === "en" ? "Original receiver row" : "Fila receptora original", { exact: true }).selectOption("1");
      await expect(tool.getByTestId("joint-response-readout")).toBeVisible();
      await tool.getByLabel(lang === "en" ? "Signed residual coordinates" : "Coordenadas residuales con signo", { exact: true }).selectOption("white");
      await page.screenshot({ path: join(evidence!, `${stem}-${m}-${partition}.png`) });
    }
    await view.selectOption("model");
    for (const plane of ["xy", "xz", "yz"]) { await tool.getByLabel(lang === "en" ? "Physical section plane" : "Plano de sección física", { exact: true }).selectOption(plane);
      await tool.getByLabel(lang === "en" ? "Fixed mesh slice" : "Corte fijo de malla", { exact: true }).selectOption("1");
      const prism = tool.locator("rect[data-cell]").first(); await pointer(page, prism); await expect(tool.getByTestId("joint-cell-readout")).toContainText("kg/m³");
      await page.screenshot({ path: join(evidence!, `${stem}-${plane}.png`) }); }
    await view.selectOption("optimization"); const attempts = tool.getByLabel(lang === "en" ? "Actual optimization attempt" : "Intento de optimización real", { exact: true });
    await attempts.selectOption("0"); await expect(tool.getByTestId("joint-attempt-status")).toContainText("nonconverged");
    await tool.getByLabel(lang === "en" ? "Recorded accepted state" : "Estado aceptado registrado", { exact: true }).selectOption("1");
    await page.screenshot({ path: join(evidence!, `${stem}-retained-nonconverged.png`) });
    await attempts.selectOption("25"); await page.screenshot({ path: join(evidence!, `${stem}-joint-state.png`) });
    await view.selectOption("comparison"); await expect(tool.getByTestId("joint-selection-reason")).toContainText("validated_coupled_selection");
    await page.screenshot({ path: join(evidence!, `${stem}-selection.png`) });
    const sidecarPromise = page.waitForEvent("download"); await pointer(page, tool.getByRole("button", { name: lang === "en" ? "Export selected exact inspection JSON" : "Exportar inspección exacta seleccionada JSON", exact: true }));
    const sidecar = await sidecarPromise, sidecarPath = join(evidence!, `${stem}-inspection.json`); await sidecar.saveAs(sidecarPath);
    const parsed = JSON.parse(readFileSync(sidecarPath, "utf8")); expect(parsed.offline_scientific_replay_performed).toBe(false); expect(parsed.inverse_executed_in_browser).toBe(false);
    expect(parsed.scientific_acceptance_verified).toBe(false); expect(parsed.selected_attempt_state.stage).toBe(25); expect(parsed.selected_attempt_state.historical_prediction).toBeNull();
    const zipPromise = page.waitForEvent("download"); await pointer(page, tool.getByRole("button", { name: lang === "en" ? "Export original private archive (includes observations)" : "Exportar archivo privado original (incluye observaciones)", exact: true }));
    const zipPath = join(evidence!, `${stem}-original.zip`); await (await zipPromise).saveAs(zipPath);
    const archive = unzipSync(new Uint8Array(readFileSync(zipPath))), originals: Record<string, Buffer> = {};
    function visit(dir: string) { for (const name of readdirSync(dir)) { const path = join(dir, name);
      if (statSync(path).isDirectory()) visit(path); else originals[relative(fixture!, path).replaceAll("\\", "/")] = readFileSync(path); } }
    visit(fixture!); expect(Object.keys(archive).sort()).toEqual(Object.keys(originals).sort());
    for (const [path, original] of Object.entries(originals)) {
      expect(Buffer.from(archive[path]).equals(original), path).toBe(true);
      expect(parsed.original_file_sha256[path]).toBe(createHash("sha256").update(original).digest("hex"));
    }
    await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBe(true);
    await pointer(page, tool.getByRole("button", { name: lang === "en" ? "Clear private result" : "Borrar resultado privado", exact: true }));
    await expect(tool.getByTestId("joint-response-readout")).toHaveCount(0);
    expect(errors).toEqual([]); expect(external).toEqual([]); expect(writes).toEqual([]); await context.close();
  });
}
test("actual maximum-count and abort browser boundaries", async ({ browser }) => {
  test.skip(!maximum || !aborted || !url || !evidence, "External actual maximum/abort workflow fixtures required; no inferred memory acceptance");
  test.setTimeout(120_000); const context = await browser.newContext({ viewport: { width: 1600, height: 900 } }), page = await context.newPage();
  await page.goto(`${url}?lang=en&theme=light`); const tool = page.getByTestId("joint-result-workbench"), picker = tool.getByLabel("Import local workflow output directory", { exact: true });
  const cdp = await context.newCDPSession(page); await cdp.send("Performance.enable");
  const before = Date.now(); await picker.setInputFiles(maximum!); await expect(tool.getByTestId("joint-response-readout")).toBeVisible({ timeout: 30_000 });
  const importMilliseconds = Date.now() - before; await tool.getByLabel("Joint scientific view", { exact: true }).selectOption("model");
  await expect(tool.getByTestId("joint-cell-readout")).toContainText("ρ 0 kg/m³");
  const metrics = await cdp.send("Performance.getMetrics"); expect(metrics.metrics.find(v => v.name === "JSHeapUsedSize")?.value).toBeGreaterThan(0);
  // Observed JS heap is not whole-browser RSS, an upper bound or maximum history.
  const record = { schema: "joint-browser-observation-1", import_milliseconds: importMilliseconds, cdp_metrics: metrics.metrics, maximum_history_qualified: false, whole_browser_rss_measured: false };
  await page.screenshot({ path: join(evidence!, "maximum-count-browser.png") });
  await picker.setInputFiles(aborted!); await expect(tool.getByTestId("joint-workflow-boundary")).toContainText("workflow failed");
  await expect(tool.getByTestId("joint-attempt-status")).toContainText("not replay-verified");
  await expect(tool.getByTestId("joint-response-readout")).toHaveCount(0); await expect(tool.getByTestId("joint-cell-readout")).toHaveCount(0);
  await page.screenshot({ path: join(evidence!, "abort-browser.png") });
  await test.info().attach("measured-browser-boundaries", { body: JSON.stringify(record), contentType: "application/json" });
  if (durableAbort) {
    await picker.setInputFiles(durableAbort); await expect(tool.getByTestId("joint-workflow-boundary")).toContainText("workflow failed");
    await expect(tool.getByLabel("Actual optimization attempt", { exact: true }).locator("option")).toHaveCount(26);
    await expect(tool.getByTestId("joint-response-readout")).toHaveCount(0); await expect(tool.getByTestId("joint-cell-readout")).toHaveCount(0);
    await page.screenshot({ path: join(evidence!, "durable-freeze-abort-browser.png") });
  } else test.info().annotations.push({ type: "unqualified", description: "Actual durable-freeze abort fixture absent; this additional boundary not accepted" });
  await context.close();
});
