import { createHash } from "node:crypto";
import { expect, test } from "@playwright/test";

test("physical survey plots expose axes, units and a symmetric signed residual scale", async ({ page }) => {
  await page.goto("/app");
  await expect(page.locator(".earth-scene canvas")).toBeVisible({ timeout: 30_000 });
  await page.locator('select[data-control="case"]:visible').first().selectOption("FWI_LAYERED");
  await expect(page.locator(".wave-stage canvas").first()).toBeVisible({ timeout: 60_000 });
  await page.getByRole("tab", { name: "Data", exact: true }).click();

  const views = page.locator('[data-instrument="data-view"] figure.heatmap');
  await expect(views).toHaveCount(3);
  const observed = views.filter({ hasText: "Observed" });
  const predicted = views.filter({ hasText: "Predicted" });
  const residual = views.filter({ hasText: "Residual" });
  await expect(observed).toContainText("Receiver position · m");
  await expect(observed).toContainText("Time · s");
  await expect(observed).toContainText("relative amplitude");
  await expect(predicted).toContainText("relative amplitude");
  await expect(residual).toContainText("relative amplitude");

  const legend = residual.locator(".scale-legend span");
  await expect(legend).toHaveCount(2);
  const lower = Number(await legend.nth(0).innerText());
  const upper = Number((await legend.nth(1).innerText()).split(" ")[0]);
  expect(lower).toBeLessThan(0);
  expect(upper).toBeGreaterThan(0);
  expect(lower + upper).toBeCloseTo(0, 10);
});

test("angle-step controls alter genuine 3D geometry and are absent from the FWI section", async ({ page }) => {
  await page.goto("/app");
  await expect(page.locator(".earth-scene canvas")).toBeVisible({ timeout: 30_000 });
  await page.getByRole("button", { name: "Experiment controls", exact: true }).click();
  await page.getByText("View controls: threshold, cut and rotation", { exact: true }).click();
  const step = page.locator('input[type="range"][aria-label="Angle step"]');
  await expect(step).toBeVisible();
  const scene = page.locator(".earth-scene canvas");
  const before = createHash("sha256").update(await scene.screenshot()).digest("hex");
  await step.fill("30");
  await expect(step).toHaveValue("30");
  await page.getByRole("button", { name: "Rotate right", exact: true }).click();
  await expect.poll(async () => createHash("sha256").update(await scene.screenshot()).digest("hex"))
    .not.toBe(before);

  await page.locator('select[data-control="case"]:visible').first().selectOption("FWI_LAYERED");
  await expect(page.locator(".wave-stage canvas").first()).toBeVisible({ timeout: 60_000 });
  await expect(page.locator('input[type="range"][aria-label="Angle step"]')).toHaveCount(0);
  await expect(page.locator(".wave-stage")).toContainText("Distance · m");
  await expect(page.locator(".wave-stage")).toContainText("Depth · m");
});
