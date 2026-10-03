import { test, expect, type Locator, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { mtSections } from "../src/data/online-mt-course";

// Deliberate pointer navigation, not a typed deep-link or locator.click teleport.
async function pointer(page: Page, locator: Locator) {
  // Center real targets so a sticky shell header cannot intercept the pointer.
  await locator.evaluate(node => node.scrollIntoView({ block: "center", inline: "nearest", behavior: "instant" }));
  const bounds = await locator.boundingBox();
  if (!bounds) throw new Error("Pointer target has no rendered bounds");
  await page.mouse.move(bounds.x + bounds.width / 2, bounds.y + bounds.height / 2, { steps: 5 });
  await page.mouse.down(); await page.mouse.up();
}
const evidence = "node_modules/.mt-course-qa/evidence";
mkdirSync(evidence, { recursive: true });

// Tall locator screenshots can contain off-viewport blank areas. Capture real
// viewport slices with overlap instead, so all prose/math is actually painted.
async function capture(page: Page, region: Locator, stem: string) {
  await page.evaluate(() => document.fonts.ready);
  const limits = await region.evaluate(node => {
    const box = node.getBoundingClientRect();
    let container = node.parentElement;
    while (container && !(container.scrollHeight > container.clientHeight && /auto|scroll/.test(getComputedStyle(container).overflowY))) container = container.parentElement;
    const offset = container ? container.scrollTop - container.getBoundingClientRect().top : scrollY;
    return { start: box.top + offset - 130, end: box.bottom + offset,
      height: container ? Math.min(innerHeight, container.clientHeight) : innerHeight,
      max: container ? container.scrollHeight - container.clientHeight : document.documentElement.scrollHeight - innerHeight };
  });
  let slice = 0;
  for (let y = Math.max(0, limits.start); ; y += limits.height * .65) {
    await region.evaluate((node, top) => {
      let container = node.parentElement;
      while (container && !(container.scrollHeight > container.clientHeight && /auto|scroll/.test(getComputedStyle(container).overflowY))) container = container.parentElement;
      (container || window).scrollTo({ top, behavior: "instant" });
    }, Math.min(y, limits.max));
    await page.screenshot({ path: `${evidence}/${stem}-viewport-${slice++}.png` });
    if (y + limits.height >= limits.end || y >= limits.max) break;
  }
}

for (const lang of ["en", "es"] as const) for (const theme of ["light", "dark"] as const)
for (const device of ["desktop", "phone"] as const) for (const motion of ["no-preference", "reduce"] as const) {
  test(`Introduction scope grid ${lang} ${theme} ${device} ${motion}`, async ({ browser }) => {
    const context = await browser.newContext({ viewport: device === "phone" ? { width: 390, height: 844 } : { width: 1440, height: 900 }, reducedMotion: motion });
    await context.addInitScript(({ lang, theme }) => { localStorage.setItem("caos.lang", lang); localStorage.setItem("caos.theme", theme); }, { lang, theme });
    const page = await context.newPage(), errors: string[] = [];
    page.on("pageerror", error => errors.push(error.message));
    page.on("console", msg => { if (msg.type() === "error") errors.push(msg.text()); });
    await page.goto("/");
    await pointer(page, page.locator('a[href$="/introduction"]').first());
    const scope = page.locator("[data-mt-introduction]");
    await expect(scope.getByRole("heading", { name: lang === "es" ? "Datos originales, procesamiento e inversión" : "Original data, processing and inversion", exact: true })).toBeVisible();
    await expect(scope).toContainText("truth=null");
    await expect(scope).toContainText(lang === "es" ? "No se afirma activación host" : "No host activation is asserted");
    await expect(scope.locator(".katex-error")).toHaveCount(0);
    const width = await page.evaluate(() => ({ actual: document.documentElement.scrollWidth, viewport: innerWidth }));
    expect(width.actual).toBe(width.viewport);
    await capture(page, scope, `${lang}-${theme}-${device}-${motion}-introduction`);
    expect(errors).toEqual([]);
    await context.close();
  });
  test(`course grid ${lang} ${theme} ${device} ${motion}`, async ({ browser }) => {
    const context = await browser.newContext({ viewport: device === "phone" ? { width: 390, height: 844 } : { width: 1440, height: 900 }, reducedMotion: motion });
    await context.addInitScript(({ lang, theme }) => { localStorage.setItem("caos.lang", lang); localStorage.setItem("caos.theme", theme); }, { lang, theme });
    const page = await context.newPage(), errors: string[] = [];
    page.on("pageerror", error => errors.push(error.message));
    page.on("console", msg => { if (msg.type() === "error") errors.push(msg.text()); });
    await page.goto("/");
    await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
    const i = lang === "es" ? 1 : 0;
    for (const view of ["theory", "implementation"] as const) {
      const route = view === "theory" ? "methodology" : "implementation";
      await pointer(page, page.locator(`a[href$="/${route}"]`).first());
      await expect(page).toHaveURL(new RegExp(`/${route}$`));
      await pointer(page, page.getByRole("tab", { name: lang === "es" ? "Magnetotelúrica" : "Magnetotellurics", exact: true }));
      for (const method of ["m05", "m06"] as const) {
        await pointer(page, page.getByRole("tab", { name: method === "m05" ? "M05 · EDI QC" : lang === "es" ? "M06 · Inversión 1D" : "M06 · 1D inverse", exact: true }));
        for (const section of mtSections.filter(s => s.method === method && s.view === view)) {
          await pointer(page, page.getByRole("tab", { name: section.label[i], exact: true }));
          const article = page.locator(`[data-mt-section="${section.id}"]`);
          await expect(article.getByRole("heading", { name: section.title[i], exact: true })).toBeVisible();
          await expect(article.locator(".katex-error")).toHaveCount(0);
          expect(await article.locator("a[href^='https://']").count()).toBeGreaterThan(3);
          const svg = article.locator("svg[data-mt-physics]");
          await svg.scrollIntoViewIfNeeded();
          const violations = await svg.evaluate(node => {
            const v = (node as SVGSVGElement).viewBox.baseVal;
            return [...node.querySelectorAll("text")].flatMap(text => {
              const box = text.getBBox();
              return box.x < v.x || box.y < v.y || box.x + box.width > v.x + v.width || box.y + box.height > v.y + v.height ? [text.textContent] : [];
            });
          });
          expect(violations, "Rendered SVG text must remain inside its viewBox").toEqual([]);
          await expect(svg).toBeInViewport({ ratio: 1 });
          const labelSize = await svg.locator("text").first().evaluate(node => {
            const svg = node.closest("svg")!;
            return parseFloat(getComputedStyle(node).fontSize) * svg.getBoundingClientRect().width / svg.viewBox.baseVal.width;
          });
          expect(labelSize, "Physics labels remain legible on phone").toBeGreaterThanOrEqual(14);
          const width = await page.evaluate(() => ({ actual: document.documentElement.scrollWidth, viewport: innerWidth }));
          expect(width.actual, "No document horizontal overflow").toBe(width.viewport);
          const stem = `${lang}-${theme}-${device}-${motion}-${view}-${section.id}`;
          await svg.screenshot({ path: `${evidence}/${stem}-physics.png` });
          await capture(page, article, stem);
          if (section.exercise) {
            const reveal = article.getByRole("button", { name: lang === "es" ? "Revelar explicación" : "Reveal explanation", exact: true });
            await pointer(page, reveal); await expect(article.getByTestId("mt-answer")).toBeVisible();
            const questions = article.getByLabel(lang === "es" ? "Pregunta de control" : "Control question");
            const count = await questions.locator("option").count();
            for (let index = 1; index < count; index++) {
              await pointer(page, questions); await page.keyboard.press("ArrowDown"); await page.keyboard.press("Enter");
              await expect(article.getByTestId("mt-answer")).toHaveCount(0);
              await pointer(page, reveal); await expect(article.getByTestId("mt-answer")).toBeVisible();
            }
            await article.getByTestId("mt-answer").scrollIntoViewIfNeeded();
            await page.screenshot({ path: `${evidence}/${stem}-exercise.png` });
            if (method === "m06") {
              const controls = article.getByLabel(lang === "es" ? "Control resuelto" : "Worked control");
              let previous = await article.getByTestId("mt-worked-model").innerText();
              for (let index = 1; index < 5; index++) {
                await pointer(page, controls); await page.keyboard.press("ArrowDown"); await page.keyboard.press("Enter");
                const current = await article.getByTestId("mt-worked-model").innerText();
                expect(current).not.toBe(previous); previous = current;
              }
            }
          }
        }
      }
      await pointer(page, page.getByRole("tab", { name: lang === "es" ? "Comparadores replay" : "Replay comparators", exact: true }));
      await expect(page.locator("[data-mt-course]")).toContainText(lang === "es" ? "No son tres métodos online" : "not three online");
      await pointer(page, page.locator('a[href="/"]').first());
    }
    expect(errors).toEqual([]);
    await context.close();
  });
}
