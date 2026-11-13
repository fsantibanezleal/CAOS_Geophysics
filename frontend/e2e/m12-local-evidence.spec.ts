import { test, expect } from "@playwright/test";

const root = "E:/_worktrees/CAOS_Geophysics-data/experiments/m12-residual-v3-20261027";

test("Benchmark inspects the exact local M12 receipt and preserves its failed result", async ({ page }) => {
  const pageErrors: string[] = [];
  const requests: string[] = [];
  page.on("pageerror", error => pageErrors.push(error.message));
  page.on("request", request => requests.push(request.url()));
  await page.goto("/benchmark");
  await expect(page.getByRole("heading", { name: /M12 residual v3\.1/ })).toBeVisible();

  await page.getByLabel("receipt.json", { exact: true }).setInputFiles(`${root}/receipt.json`);
  await page.getByLabel("local-evidence-manifest.json", { exact: true }).setInputFiles(`${root}/local-evidence-manifest.json`);
  await page.getByLabel("m12-residual-v3.1.npz", { exact: true }).setInputFiles(`${root}/m12-residual-v3.1.npz`);
  await page.getByRole("button", { name: "Inspect local evidence" }).click();

  await expect(page.getByText(/Scientific outcome: FAILED; held-out comparator/)).toBeVisible();
  await expect(page.getByText(/Velocity ratio 1\.0436829910482/)).toBeVisible();
  await expect(page.getByText(/1\.39609388087989/)).toBeVisible();
  await expect(page.getByText(/0f7a8fc43a078ab4/)).toBeVisible();
  await expect(page.locator("canvas").first()).toBeVisible();
  const evidence = page.locator("section[aria-labelledby='m12-evidence-title']");
  await evidence.screenshot({ path: "node_modules/.m12-qa/benchmark-m12-desktop.png" });
  await page.setViewportSize({ width: 390, height: 844 });
  await evidence.screenshot({ path: "node_modules/.m12-qa/benchmark-m12-phone.png" });
  expect(pageErrors).toEqual([]);
  expect(requests.filter(url => /api\//i.test(url))).toEqual([]);
});
