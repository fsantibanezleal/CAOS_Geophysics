import { test, expect } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { courseQaPaths } from "./m01-course-output";
import { magneticLessons } from "../src/data/magnetic-survey-course";
const output = courseQaPaths(process.env.MAGNETIC_THEORY_QA_OUTPUT,
  process.env.MAGNETIC_THEORY_QA_RUN ?? "run-01", fileURLToPath(new URL("../../", import.meta.url)), "MAGNETIC_THEORY_QA_OUTPUT");
mkdirSync(output.evidence, { recursive: true });
for (const route of ["methodology", "implementation"]) for (const lang of ["en", "es"] as const)
for (const theme of ["light", "dark"]) for (const width of [390, 1600]) {
  test(`${route} magnetic chapters ${lang} ${theme} ${width}`, async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width, height: width === 390 ? 844 : 900 }, reducedMotion: "reduce" });
    await context.addInitScript(({ lang, theme }) => {
      localStorage.setItem("caos.lang", lang); localStorage.setItem("caos.theme", theme);
    }, { lang, theme });
    const page = await context.newPage(), errors: string[] = [], writes: string[] = [];
    page.on("pageerror", error => errors.push(error.message));
    page.on("request", request => { if (request.method() !== "GET" && request.url().includes("/api/")) writes.push(request.url()); });
    try {
      await page.goto(`/${route}`);
      await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
      await page.getByRole("tab", { name: lang === "es" ? "Levantamientos magnéticos" : "Magnetic surveys", exact: true }).click();
      const course = page.locator("[data-magnetic-theory]");
      await expect(course).toBeVisible();
      const selector = course.getByLabel(lang === "es" ? "Capítulo magnético" : "Magnetic chapter");
      await selector.focus(); await selector.press("End"); await selector.press("Enter");
      await expect(selector).toHaveValue("8");
      for (let chapter = 0; chapter < magneticLessons.length; chapter++) {
        await selector.selectOption(String(chapter));
        await expect(course).toHaveAttribute("data-lesson", magneticLessons[chapter].id);
        await expect(course.locator(".katex-error")).toHaveCount(0);
        await expect(course.locator(".katex")).toHaveCount(2);
        const disclosure = course.locator("details"), summary = disclosure.locator("summary");
        await expect(disclosure).not.toHaveAttribute("open", "");
        await summary.scrollIntoViewIfNeeded(); await summary.focus(); await summary.press("Enter");
        await expect(disclosure).toHaveAttribute("open", "");
        await expect(disclosure.locator("p")).toBeVisible();
        await summary.press("Enter"); await expect(disclosure).not.toHaveAttribute("open", "");
        await expect(course.locator('a[href^="https://raw.githubusercontent.com/"]').first()).toBeVisible();
        expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1)).toBe(true);
        await course.locator("h3").first().scrollIntoViewIfNeeded();
        await page.screenshot({ path: `${output.evidence}/${route}-${lang}-${theme}-${width}-${magneticLessons[chapter].id}.png` });
      }
      expect(errors).toEqual([]); expect(writes).toEqual([]);
    } finally { await context.close(); }
  });
}
