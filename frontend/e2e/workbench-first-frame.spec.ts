import { expect, test } from "@playwright/test";

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
