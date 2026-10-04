import { test, expect, type Locator, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";

const run = process.env.M01_COURSE_QA_RUN ?? "run-01";
if (!/^[a-z0-9-]+$/.test(run)) throw new Error("Invalid owned QA run name");
const evidence = `node_modules/.m01-course-qa/${run}/evidence`;
mkdirSync(evidence, { recursive: true });

async function pointer(page: Page, locator: Locator) {
  await locator.evaluate(node => node.scrollIntoView({ block: "center", inline: "nearest", behavior: "instant" }));
  const bounds = await locator.boundingBox();
  if (!bounds) throw new Error("Target has no rendered bounds");
  await page.mouse.move(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2, { steps: 5 });
  await page.mouse.down(); await page.mouse.up();
}

for (const lang of ["en", "es"] as const) for (const theme of ["light", "dark"] as const)
for (const device of ["desktop", "phone"] as const) {
  test(`M01 science, records and controls ${lang} ${theme} ${device}`, async ({ browser }) => {
    const context = await browser.newContext({
      viewport: device === "phone" ? { width: 390, height: 844 } : { width: 1600, height: 900 },
      reducedMotion: "reduce",
    });
    await context.addInitScript(({ lang, theme }) => {
      localStorage.setItem("caos.lang", lang); localStorage.setItem("caos.theme", theme);
    }, { lang, theme });
    const page = await context.newPage(), errors: string[] = [], requests: string[] = [];
    page.on("pageerror", error => errors.push(error.message));
    page.on("request", request => { if (request.url().includes("/data/m01-scientific-course/")) requests.push(request.url()); });
    await page.goto("/methodology");
    await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
    const course = page.locator("[data-m01-course]");
    await expect(course).toBeVisible();
    await expect(course).toContainText(lang === "es" ? "Magnitudes y unidades" : "Quantities and units");
    const selector = course.getByLabel(lang === "es" ? "Pregunta científica o control registrado" : "Scientific question or recorded control");
    for (let chapter = 1; chapter <= 6; chapter++) {
      await selector.selectOption(String(chapter));
      await expect(course.locator(".katex-error")).toHaveCount(0);
      await expect(course.locator(".katex").first()).toBeVisible();
      const image = course.locator("img.fig-svg");
      await expect(image).toHaveCount(1);
      await image.scrollIntoViewIfNeeded();
      await expect.poll(() => image.evaluate(node => (node as HTMLImageElement).complete && (node as HTMLImageElement).naturalWidth > 0)).toBe(true);
      const styling = await image.evaluate(node => {
        const source = decodeURIComponent((node as HTMLImageElement).src.split(",")[1]);
        const root = getComputedStyle(document.documentElement);
        return { palette: source.includes("--bg:" + root.getPropertyValue("--color-bg").trim()),
          font: source.includes("font:24px " + root.getPropertyValue("--font-sans").trim()),
          width: document.documentElement.scrollWidth, viewport: innerWidth };
      });
      expect(styling.palette).toBe(true); expect(styling.font).toBe(true);
      expect(styling.width).toBe(styling.viewport);
      await image.screenshot({ path: `${evidence}/${lang}-${theme}-${device}-q${chapter}-physics.png` });
      const reveal = course.getByRole("button", { name: lang === "es" ? "Revelar explicación" : "Reveal explanation", exact: true });
      await pointer(page, reveal);
      await expect(course.getByRole("button", { name: lang === "es" ? "Ocultar explicación" : "Hide explanation", exact: true })).toHaveAttribute("aria-expanded", "true");
      if ([1, 2, 3, 6].includes(chapter)) {
        const calculator = course.locator("[data-m01-explanation]");
        await pointer(page, calculator.getByRole("button", { name: lang === "es" ? "Aplicar" : "Apply", exact: true }));
        await expect(calculator.getByTestId("m01-explanatory-output")).toBeVisible();
        await calculator.screenshot({ path: `${evidence}/${lang}-${theme}-${device}-q${chapter}-calculation.png` });
        const first = calculator.getByRole("spinbutton").first();
        await first.fill("");
        await expect(calculator.getByTestId("m01-explanatory-output")).toHaveCount(0);
        await pointer(page, calculator.getByRole("button", { name: lang === "es" ? "Aplicar" : "Apply", exact: true }));
        await expect(calculator.getByRole("alert")).toBeVisible();
        await pointer(page, calculator.getByRole("button", { name: lang === "es" ? "Restablecer" : "Reset", exact: true }));
        await expect(calculator.getByRole("alert")).toHaveCount(0);
      }
    }
    expect(requests).toHaveLength(0);
    await selector.selectOption("records");
    const record = course.locator("[data-m01-recorded]");
    const scenario = record.getByLabel(lang === "es" ? "Registro real" : "Actual record", { exact: true });
    const identities: string[] = [];
    for (let i = 0; i < 3; i++) {
      if (i) await scenario.selectOption(`prism-case-${i}`);
      await expect(record.getByTestId("m01-selected-model")).toBeVisible();
      const model = await record.getByTestId("m01-selected-model").innerText();
      const fingerprint = await record.locator("p").filter({ hasText: lang === "es" ? "Identidades exactas" : "Exact request" }).innerText();
      identities.push(fingerprint);
      await expect(record).not.toContainText("NaN");
      // These labels wrap the select, so their text includes option labels.
      // Match the scientific prefix, not an exact truncated accessible name.
      const quantity = record.getByLabel(lang === "es" ? /^Magnitud/ : /^Quantity/);
      const height = record.getByLabel(lang === "es" ? /^Altura absoluta registrada/ : /^Recorded absolute height/);
      for (const field of ["field", "sigma", "residual"]) {
        await quantity.selectOption(field);
        if (field !== "residual") await height.selectOption("2");
        else await expect(height).toBeDisabled();
        await expect(record.getByTestId("m01-selected-model")).toHaveText(model);
        const sample = record.getByLabel(lang === "es" ? "Inspeccionar muestra (flechas o puntero)" : "Inspect sample (keyboard arrows or pointer)");
        // The preceding pointer-driven controls or screenshot scrolling can
        // inspect a map node. Establish the keyboard starting point explicitly.
        await page.mouse.move(0, 0);
        await sample.fill("0");
        await sample.focus(); await page.keyboard.press("ArrowUp");
        await expect(sample).toHaveValue("1");
        await expect(record.getByTestId("m01-map-value")).not.toContainText("undefined");
        const legend = record.getByTestId("m01-map-legend");
        expect(await legend.evaluate(node => parseFloat(getComputedStyle(node).fontSize))).toBeGreaterThanOrEqual(14);
        await expect(legend).not.toContainText("000000000000");
        const map = record.locator("svg.method-diagram").first();
        await map.scrollIntoViewIfNeeded();
        await map.screenshot({ path: `${evidence}/${lang}-${theme}-${device}-case${i}-${field}.png` });
        await legend.screenshot({ path: `${evidence}/${lang}-${theme}-${device}-case${i}-${field}-legend.png` });
        await record.locator("figure").screenshot({ path: `${evidence}/${lang}-${theme}-${device}-case${i}-${field}-figure.png` });
      }
    }
    expect(new Set(identities).size).toBe(3);
    expect(requests).toHaveLength(9);
    expect(requests.every(url => /\/(request|result|receipt)\.json$/.test(url))).toBe(true);
    await page.goto("/implementation");
    await expect(page.locator("[data-m01-course]")).toBeVisible();
    await expect(page.locator(".katex-error")).toHaveCount(0);
    expect(await page.evaluate(() => document.documentElement.scrollWidth === innerWidth)).toBe(true);
    expect(errors).toEqual([]);
    await context.close();
  });
}

test("corrupt recorded source fails closed without showing metrics", async ({ page }) => {
  await page.route("**/data/m01-scientific-course/prism-case-0/result.json", route => route.fulfill({ status: 200, body: "{}", contentType: "application/json" }));
  await page.goto("/methodology");
  const course = page.locator("[data-m01-course]");
  await course.getByLabel("Scientific question or recorded control").selectOption("records");
  await expect(course.getByRole("alert")).toContainText("integrity mismatch");
  await expect(course.getByTestId("m01-selected-model")).toHaveCount(0);
  await expect(course.locator("svg.method-diagram")).toHaveCount(0);
});
