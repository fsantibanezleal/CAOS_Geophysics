import { expect, test } from "@playwright/test";

test("FWI playback displays distinct recorded wave and inversion states with physical time", async ({ page }) => {
  const pageErrors: string[] = [];
  page.on("pageerror", error => pageErrors.push(error.message));
  await page.goto("/app");
  await expect(page.locator(".earth-scene canvas")).toBeVisible({ timeout: 30_000 });
  await page.locator('select[data-control="case"]:visible').first().selectOption("FWI_LAYERED");
  await expect(page.locator(".wave-stage canvas").first()).toBeVisible({ timeout: 60_000 });

  await page.getByRole("button", { name: "Experiment controls", exact: true }).click();
  await page.getByRole("button", { name: "Replay", exact: true }).click();
  await page.getByLabel("Animation process", { exact: true }).selectOption("wave");
  const slider = page.getByLabel("Replay frame", { exact: true });
  const raster = page.locator(".wave-stage canvas").first();
  await expect(slider).toHaveAttribute("max", "66");
  await expect(slider).toHaveValue("0");
  const firstFrame = await raster.evaluate(canvas => {
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Wavefield canvas has no 2D context");
    const bytes = context.getImageData(0, 0, canvas.width, canvas.height).data;
    let hash = 2166136261;
    for (const value of bytes) hash = Math.imul(hash ^ value, 16777619);
    return hash >>> 0;
  });
  await slider.fill("16");
  await expect(page.locator(".wave-clock strong")).toContainText("0.384");
  const recordedWave = await raster.evaluate(canvas => {
    const context = canvas.getContext("2d");
    if (!context) throw new Error("Wavefield canvas has no 2D context");
    const bytes = context.getImageData(0, 0, canvas.width, canvas.height).data;
    let hash = 2166136261;
    for (const value of bytes) hash = Math.imul(hash ^ value, 16777619);
    return hash >>> 0;
  });
  expect(recordedWave).not.toBe(firstFrame);
  await expect(page.locator(".wave-clock strong small")).toHaveText("s");

  await page.getByRole("button", { name: "Play", exact: true }).click();
  await expect.poll(() => slider.inputValue()).not.toBe("16");
  await page.getByRole("button", { name: "Pause", exact: true }).click();
  const pausedFrame = await slider.inputValue();
  await page.waitForTimeout(400);
  await expect(slider).toHaveValue(pausedFrame);

  await page.getByLabel("Animation process", { exact: true }).selectOption("inverse");
  await expect(slider).toHaveAttribute("max", "31");
  await slider.fill("7");
  await expect(page.locator(".wave-clock strong small")).toHaveText("update");
  await expect(page.locator(".wave-clock strong")).toContainText(/\d+/);
  await expect(page.getByText(/Data predictions and evaluation remain at the selected final model/)).toBeVisible();
  expect(pageErrors).toEqual([]);
});
