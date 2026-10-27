import { createHash } from "node:crypto";
import { mkdirSync, readFileSync } from "node:fs";
import { join } from "node:path";
import { test, expect } from "@playwright/test";
import { courseQaPaths } from "./m01-course-output";
import { fileURLToPath } from "node:url";

const qa = courseQaPaths(process.env.GEOPHYSICS_VELOCITY_CALCULATOR_QA_OUTPUT,
  process.env.GEOPHYSICS_VELOCITY_CALCULATOR_QA_RUN ?? "run-01",
  fileURLToPath(new URL("../", import.meta.url)), "GEOPHYSICS_VELOCITY_CALCULATOR_QA_OUTPUT");

function requestBytes() {
  const f = (i: number) => i / 7;
  const left = Array.from({ length: 8 }, (_, i) => [0, (.08 + .84 * f(i)) * 800] as const);
  const right = Array.from({ length: 8 }, (_, i) => [800, (.1 + .8 * f(i)) * 800] as const);
  const top = Array.from({ length: 8 }, (_, i) => [(.08 + .84 * f(i)) * 800, 0] as const);
  const bottom = Array.from({ length: 8 }, (_, i) => [(.1 + .8 * f(i)) * 800, 800] as const);
  const rays = [...left.flatMap(([x, z]) => right.map(([xr, zr]) => [x, z, xr, zr])),
    ...top.flatMap(([x, z]) => bottom.map(([xr, zr]) => [x, z, xr, zr]))];
  const times = rays.map(([x0, z0, x1, z1], i) => {
    const dx = x1 - x0, dz = z1 - z0, ts = [0, 1];
    for (let k = 1; k < 16; k++) { const edge = k * 50; if (dx !== 0) ts.push((edge - x0) / dx); if (dz !== 0) ts.push((edge - z0) / dz); }
    const sorted = [...new Set(ts.filter(t => t >= 0 && t <= 1))].sort((a, b) => a - b), length = Math.hypot(dx, dz);
    let time = 0;
    for (let k = 0; k < sorted.length - 1; k++) { const mid = (sorted[k] + sorted[k + 1]) / 2, iz = Math.max(0, Math.min(15, Math.floor((z0 + mid * dz) / 50))); time += (sorted[k + 1] - sorted[k]) * length / (2000 + .35 * ((iz + .5) * 50)); }
    return time + .0004 * Math.sin(i * 1.7);
  });
  return Buffer.from(JSON.stringify({ schema: "geophysics.velocity-user-data/v1", id: "browser-parameter-control",
    source: { citation: "Authored numerical parity control", rights: "owner-permitted", scope: "synthetic-control" },
    frame: "local-x-z-down", units: { distance: "m", time: "s", velocity: "m/s" },
    ray_ids: rays.map((_, i) => `ray-${String(i).padStart(3, "0")}`), rays_m: rays,
    times_s: times, sigma_s: rays.map(() => .001), lambda: 25 }));
}

test("user changes λ, browser reruns the submitted acquisition and exports both input identities", async ({ browser }) => {
  mkdirSync(qa.evidence, { recursive: true });
  const errors: string[] = [], apiRequests: string[] = [];
  const source = requestBytes(), sourceHash = createHash("sha256").update(source).digest("hex");

  for (const [viewport, width, height] of [["desktop", 1440, 960], ["phone", 390, 844]] as const) {
    const context = await browser.newContext({ viewport: { width, height } });
    await context.addInitScript(() => {
      localStorage.setItem("caos.lang", "en");
      localStorage.setItem("caos.theme", "light");
    });
    const page = await context.newPage();
    page.on("pageerror", error => errors.push(error.message));
    page.on("request", request => { if (request.url().includes("/api/")) apiRequests.push(request.url()); });
    await page.goto("/?instrument=velocity-local");
    await expect(page.getByRole("heading", { name: "Calculate supplied first-arrival data" })).toBeVisible();
    await page.getByLabel("First-arrival request JSON").setInputFiles({
      name: "user-first-arrivals.json", mimeType: "application/json", buffer: source,
    });
    const lambda = page.getByRole("spinbutton", { name: "Regularization weight λ" });
    await expect(lambda).toHaveValue("25");
    const calculate = page.getByRole("button", { name: "Calculate locally in browser" });
    await calculate.click();
    await expect(page.locator("[data-testid=velocity-browser-calculator]").getByText(/WRMS/)).toBeVisible();
    await expect(page.locator("[data-testid=velocity-browser-calculator]")).toContainText("λ 25");
    await page.screenshot({ path: join(qa.evidence, `${viewport}-${width}-lambda-25.png`) });
    const [firstDownload] = await Promise.all([page.waitForEvent("download"),
      page.getByRole("button", { name: "Export browser result JSON" }).click()]);
    const firstPath = join(qa.evidence, `${viewport}-lambda-25.json`); await firstDownload.saveAs(firstPath);
    const first = JSON.parse(readFileSync(firstPath, "utf8"));

    await lambda.fill("1000");
    await calculate.click();
    await expect(page.locator("[data-testid=velocity-browser-calculator]")).toContainText("λ 1000");
    await page.screenshot({ path: join(qa.evidence, `${viewport}-${width}-lambda-1000.png`) });
    const [secondDownload] = await Promise.all([page.waitForEvent("download"),
      page.getByRole("button", { name: "Export browser result JSON" }).click()]);
    const secondPath = join(qa.evidence, `${viewport}-lambda-1000.json`); await secondDownload.saveAs(secondPath);
    const second = JSON.parse(readFileSync(secondPath, "utf8"));

    expect(first.provenance.source_file_sha256).toBe(sourceHash);
    expect(second.provenance.source_file_sha256).toBe(sourceHash);
    expect(first.provenance.effective_request_sha256).toBe(createHash("sha256").update(JSON.stringify(first.request)).digest("hex"));
    expect(second.provenance.effective_request_sha256).toBe(createHash("sha256").update(JSON.stringify(second.request)).digest("hex"));
    expect(first.request.lambda).toBe(25); expect(second.request.lambda).toBe(1000);
    expect(first.provenance.effective_request_sha256).not.toBe(second.provenance.effective_request_sha256);
    expect(first.velocity_m_s).not.toEqual(second.velocity_m_s);
    expect(first.predicted_s).not.toEqual(second.predicted_s);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
    expect(errors).toEqual([]); expect(apiRequests).toEqual([]);
    await context.close();
  }
});
