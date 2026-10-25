import { test, expect } from "@playwright/test";
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";

const root = resolve("..");
const assetRoot = resolve(root, "data/derived/phase/browser-assets/stead");

test("M13 runs a hash-verified held-out STEAD trace in-browser and exports valid model scores", async ({ page }) => {
  test.setTimeout(120_000);
  await page.addInitScript(() => localStorage.setItem("caos.lang", "en"));

  const manifest = JSON.parse(await readFile(resolve(assetRoot, "manifest.json"), "utf8"));
  const modelHash = manifest.model.sha256 as string;
  const validIndex = manifest.records.findIndex((record: { status: string }) => record.status === "qc-valid");
  const record = manifest.records[validIndex];
  expect(validIndex).toBeGreaterThanOrEqual(0);

  const apiRequests: string[] = [];
  page.on("request", request => {
    if (new URL(request.url()).pathname.startsWith("/api/")) apiRequests.push(request.url());
  });
  await page.goto("/benchmark#phase-picker");
  await page.getByRole("button", { name: "Load reviewed STEAD assets", exact: true }).click();
  const selector = page.getByRole("combobox", { name: "STEAD trace", exact: true });
  await expect(selector.locator("option")).toHaveCount(manifest.records.length);
  await expect(page.getByText(new RegExp(`SHA-256 ${modelHash}`))).toBeVisible();
  await expect(page.getByText(new RegExp(`${record.trace_id}.*qc-valid`))).toBeVisible();
  const benchmark = page.locator(".phase-benchmark table");
  await expect(benchmark).toContainText("M08");
  await expect(benchmark).toContainText("M13");
  await expect(page.getByText(/6,000 selected STEAD test traces/)).toBeVisible();

  // The retained QC failure is inspectable but cannot be sent to the model.
  const rejectedIndex = manifest.records.findIndex((item: { status: string }) => item.status === "qc-rejected");
  expect(rejectedIndex).toBeGreaterThanOrEqual(0);
  await selector.selectOption(String(rejectedIndex));
  await expect(page.getByRole("button", { name: "Run browser inference", exact: true })).toBeDisabled();
  await expect(page.getByRole("status")).toContainText("QC rejected");

  await selector.selectOption(String(validIndex));
  await page.getByRole("button", { name: "Run browser inference", exact: true }).click();
  await expect(page.getByRole("button", { name: "Export N/P/S scores (.f32)", exact: true })).toBeEnabled({ timeout: 60_000 });
  await expect(page.getByRole("img", { name: "Three measured E N Z components" })).toBeVisible();
  await expect(page.getByRole("img", { name: "Browser-computed N P S scores" })).toBeVisible();

  const downloadPromise = page.waitForEvent("download");
  await page.getByRole("button", { name: "Export N/P/S scores (.f32)", exact: true }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe(`${record.trace_id}-browser-probabilities.f32`);
  const bytes = await readFile((await download.path())!);
  expect(bytes.byteLength).toBe(3 * 6000 * Float32Array.BYTES_PER_ELEMENT);
  const values = new Float32Array(bytes.buffer, bytes.byteOffset, bytes.byteLength / Float32Array.BYTES_PER_ELEMENT);
  for (let i = 0; i < 6000; i++) {
    const n = values[i], p = values[6000 + i], s = values[12000 + i];
    expect(Number.isFinite(n) && Number.isFinite(p) && Number.isFinite(s)).toBe(true);
    expect(n).toBeGreaterThanOrEqual(0); expect(n).toBeLessThanOrEqual(1);
    expect(p).toBeGreaterThanOrEqual(0); expect(p).toBeLessThanOrEqual(1);
    expect(s).toBeGreaterThanOrEqual(0); expect(s).toBeLessThanOrEqual(1);
    expect(Math.abs(n + p + s - 1)).toBeLessThanOrEqual(0.001);
  }
  expect(apiRequests).toEqual([]);
});
