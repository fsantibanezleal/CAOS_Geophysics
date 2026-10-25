import { expect, test } from "@playwright/test";
import { createHash } from "node:crypto";

test("lazy 3D workbench renders before the scientific acceptance gate measures it", async ({ page }) => {
  const pageErrors: string[] = [];
  page.on("pageerror", (error) => pageErrors.push(error.message));
  await page.goto("/");

  const scene = page.locator(".earth-scene[role=img]");
  await expect(scene).toBeVisible({ timeout: 30_000 });
  const canvas = scene.locator("canvas");
  await expect(canvas).toBeVisible({ timeout: 30_000 });
  await expect.poll(() => canvas.evaluate((element) => element.width)).toBeGreaterThan(1);
  await expect(page.locator('[data-state="loading"]')).toHaveCount(0);
  await expect.poll(async () => Number(await scene.getAttribute("data-visible-cells"))).toBeGreaterThan(0);
  expect(pageErrors).toEqual([]);
});

test("methodology links to the bilingual M01-M13 repository wiki", async ({ page }) => {
  await page.goto("/methodology");
  const link = page.getByRole("link", { name: "Open the bilingual methods wiki" });
  await expect(link).toBeVisible();
  await expect(link).toHaveAttribute(
    "href",
    "https://github.com/fsantibanezleal/CAOS_Geophysics/blob/main/docs/wiki/README.md",
  );
});

test("survey markers follow recorded station spacing and distinct cases render distinct fields", async ({ page }, testInfo) => {
  await page.goto("/");
  const scene = page.locator(".earth-scene");
  const canvas = scene.locator("canvas");
  await expect(canvas).toBeVisible({ timeout: 30_000 });
  await expect(scene).toHaveAttribute("data-survey-glyph-diameter-m", /\d+/);
  const firstDiameter = Number(await scene.getAttribute("data-survey-glyph-diameter-m"));
  expect(firstDiameter).toBeGreaterThan(0);
  expect(firstDiameter).toBeCloseTo(29.03225, 2);
  const gravityImage = await canvas.screenshot({ path: testInfo.outputPath("gravity-intrusion-canvas.png") });
  const gravityDigest = createHash("sha256").update(gravityImage).digest("hex");
  await page.locator(".earth-view").screenshot({ path: testInfo.outputPath("gravity-intrusion-workbench.png") });

  await page.locator('select[aria-label="Case selector"]').selectOption("MAGNETIC_DYKE");
  await expect(scene.locator(".scene-label strong")).toHaveText("Dipping dyke swarm");
  await expect.poll(async () => createHash("sha256").update(await canvas.screenshot()).digest("hex")).not.toBe(gravityDigest);
  const magneticImage = await canvas.screenshot({ path: testInfo.outputPath("magnetic-dyke-canvas.png") });
  await page.locator(".earth-view").screenshot({ path: testInfo.outputPath("magnetic-dyke-workbench.png") });
  expect(createHash("sha256").update(magneticImage).digest("hex")).not.toBe(gravityDigest);
});
