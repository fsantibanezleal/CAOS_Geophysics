import { createHash } from "node:crypto";
import { expect, test } from "@playwright/test";

test.describe.configure({ timeout: 90_000 });

const caseSelect = (page: import("@playwright/test").Page) =>
  page.locator('select[data-control="case"]:visible').first();

async function stateKeys(page: import("@playwright/test").Page) {
  return page.locator('[data-instrument="data-view"] [data-state-key]').evaluateAll(elements =>
    elements.map(element => ({
      key: element.getAttribute("data-state-key"),
      stale: element.getAttribute("data-stale"),
    })),
  );
}

async function firstChartPixels(page: import("@playwright/test").Page) {
  return page.locator('[data-instrument="data-view"] [data-state-key] canvas').first().evaluate(canvas => {
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Linked data chart has no 2D context");
    const bytes = context.getImageData(0, 0, canvas.width, canvas.height).data;
    let hash = 2166136261;
    for (const value of bytes) hash = Math.imul(hash ^ value, 16777619);
    return `${canvas.width}x${canvas.height}:${hash >>> 0}`;
  });
}

test("selected case and experiment reload their linked final-result views", async ({ page }) => {
  const pageErrors: string[] = [];
  page.on("pageerror", error => pageErrors.push(error.message));
  await page.goto("/app");
  await expect(page.locator(".earth-scene canvas")).toBeVisible({ timeout: 30_000 });
  await expect(caseSelect(page)).toHaveValue("GRAVITY_INTRUSION");

  await page.getByRole("tab", { name: "Data", exact: true }).click();
  const gravityKeys = await stateKeys(page);
  expect(gravityKeys.length).toBeGreaterThan(0);
  expect(gravityKeys.every(item => item.stale === "0")).toBe(true);
  await expect(page.locator('[data-instrument="data-view"]')).toContainText("Observed");
  await expect(page.locator('[data-instrument="data-view"]')).toContainText("Predicted");
  const gravityPlot = await firstChartPixels(page);

  await caseSelect(page).selectOption("MAGNETIC_DYKE");
  await expect(page.locator(".scene-label strong")).toHaveText("Dipping dyke swarm");
  await page.getByRole("tab", { name: "Data", exact: true }).click();
  const magneticKeys = await stateKeys(page);
  expect(magneticKeys.length).toBeGreaterThan(0);
  expect(magneticKeys.every(item => item.stale === "0")).toBe(true);
  expect(magneticKeys.map(item => item.key)).not.toEqual(gravityKeys.map(item => item.key));
  expect(await firstChartPixels(page)).not.toBe(gravityPlot);

  await page.getByRole("button", { name: "Experiment controls", exact: true }).click();
  const experiment = page.getByLabel("Experiment", { exact: true });
  const magneticPlot = await firstChartPixels(page);
  await experiment.selectOption("noise");
  await expect(experiment).toHaveValue("noise");
  await expect(page.locator('[data-instrument="data-view"]')).toHaveAttribute("data-state", "available");
  const noisyKeys = await stateKeys(page);
  expect(noisyKeys.length).toBeGreaterThan(0);
  expect(noisyKeys.every(item => item.stale === "0")).toBe(true);
  expect(noisyKeys.map(item => item.key)).not.toEqual(magneticKeys.map(item => item.key));
  expect(await firstChartPixels(page)).not.toBe(magneticPlot);

  await page.getByRole("tab", { name: "Inversion", exact: true }).click();
  await expect(page.locator('[data-instrument="inversion-view"]')).toHaveAttribute("data-state", "available");
  expect(pageErrors).toEqual([]);
});

test("changing the FWI source updates every linked data and residual view", async ({ page }) => {
  const pageErrors: string[] = [];
  page.on("pageerror", error => pageErrors.push(error.message));
  await page.goto("/app");
  await expect(page.locator(".earth-scene canvas")).toBeVisible({ timeout: 30_000 });
  await caseSelect(page).selectOption("FWI_LAYERED");
  await expect(page.locator(".wave-stage canvas").first()).toBeVisible({ timeout: 60_000 });
  await page.getByRole("tab", { name: "Data", exact: true }).click();

  const source = page.locator('select[data-control="source-position"]');
  await expect(source).toBeVisible();
  await expect(source.locator("option")).toHaveCount(3);
  const beforeKeys = await stateKeys(page);
  expect(beforeKeys.length).toBeGreaterThan(0);
  expect(beforeKeys.every(item => item.stale === "0")).toBe(true);
  const residual = page.locator('[data-instrument="data-view"] figure.heatmap').filter({ hasText: "Residual" });
  await expect(residual).toHaveCount(1);
  await expect(residual).toContainText("Receiver position · m");
  await expect(residual).toContainText("Time · s");
  const beforePixels = createHash("sha256").update(await residual.locator("canvas").screenshot()).digest("hex");

  await source.selectOption("0");
  const afterKeys = await stateKeys(page);
  expect(afterKeys.length).toBe(beforeKeys.length);
  expect(afterKeys.every(item => item.stale === "0")).toBe(true);
  expect(afterKeys.map(item => item.key)).not.toEqual(beforeKeys.map(item => item.key));
  await expect(source).toHaveValue("0");
  await expect.poll(async () => createHash("sha256").update(await residual.locator("canvas").screenshot()).digest("hex"))
    .not.toBe(beforePixels);
  await expect(residual).toContainText("relative amplitude");
  expect(pageErrors).toEqual([]);
});
