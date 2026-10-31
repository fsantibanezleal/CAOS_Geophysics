import { expect, test, type Locator, type Page, type TestInfo } from "@playwright/test";
import { mkdir } from "node:fs/promises";
import { dirname } from "node:path";

const routes = [
  { id: "app", path: "/app", en: "App", es: "App" },
  { id: "introduction", path: "/introduction", en: "Introduction", es: "Introducción" },
  { id: "methodology", path: "/methodology", en: "Methodology", es: "Metodología" },
  { id: "implementation", path: "/implementation", en: "Implementation", es: "Implementación" },
  { id: "experiments", path: "/experiments", en: "Experiments", es: "Experimentos" },
  { id: "benchmark", path: "/benchmark", en: "Benchmark", es: "Benchmark" },
] as const;

type MatrixMode = {
  lang: "en" | "es";
  theme: "light" | "dark";
  device: "desktop" | "phone";
  motion: "no-preference" | "reduce";
};

async function pointerClick(page: Page, locator: Locator) {
  await locator.evaluate(node => node.scrollIntoView({ block: "center", inline: "nearest", behavior: "instant" }));
  const nav = await locator.evaluate(node => {
    const element = node.closest<HTMLElement>("nav");
    if (!element) return null;
    const box = element.getBoundingClientRect();
    const target = node.getBoundingClientRect();
    return { left: box.left, right: box.right, top: box.top, bottom: box.bottom,
      targetLeft: target.left, targetRight: target.right, width: element.clientWidth };
  });
  if (nav && (nav.targetLeft < nav.left - 1 || nav.targetRight > nav.right + 1)) {
    for (let attempt = 0; attempt < 5; attempt++) {
      const current = await locator.evaluate(node => {
        const element = node.closest<HTMLElement>("nav")!;
        const box = element.getBoundingClientRect();
        const target = node.getBoundingClientRect();
        return { left: box.left, right: box.right, top: box.top, bottom: box.bottom,
          targetLeft: target.left, targetRight: target.right, width: element.clientWidth };
      });
      if (current.targetLeft >= current.left - 1 && current.targetRight <= current.right + 1) break;
      await page.mouse.move((current.left + current.right) / 2, (current.top + current.bottom) / 2);
      await page.mouse.wheel(current.targetRight > current.right ? current.width : -current.width, 0);
      await page.waitForTimeout(100);
    }
    const final = await locator.evaluate(node => {
      const element = node.closest<HTMLElement>("nav")!;
      const box = element.getBoundingClientRect();
      const target = node.getBoundingClientRect();
      return { left: box.left, right: box.right, targetLeft: target.left, targetRight: target.right };
    });
    expect(final.targetLeft, "route link left edge must be visible inside the shell navigation").toBeGreaterThanOrEqual(final.left - 1);
    expect(final.targetRight, "route link right edge must be visible inside the shell navigation").toBeLessThanOrEqual(final.right + 1);
  }
  const bounds = await locator.boundingBox();
  expect(bounds, "pointer target must have painted bounds").not.toBeNull();
  const box = bounds!;
  await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 4 });
  await page.mouse.down();
  await page.mouse.up();
}

async function fit(page: Page, mode: MatrixMode, route: string) {
  await expect(page.locator("main")).toBeVisible();
  await expect(page.locator("main")).not.toContainText(/Loading geophysics view|Cargando la vista geofísica/i);
  await expect.poll(async () => (await page.locator("main").innerText()).trim().length).toBeGreaterThan(100);
  // Main text can be supplied by the shell while the selected experiment is
  // still fetching its numerical artifact. Do not screenshot a blank/loading
  // workbench as if it were a visually accepted route.
  await expect(page.locator("main [data-state='loading']"), `${route}: all scientific views must finish loading`)
    .toHaveCount(0);
  const layout = await page.evaluate(() => {
    const main = document.querySelector("main");
    if (!main) throw new Error("The route has no main landmark.");
    const box = main.getBoundingClientRect();
    return {
      documentWidth: document.documentElement.scrollWidth,
      viewportWidth: window.innerWidth,
      mainLeft: box.left,
      mainRight: box.right,
      mainWidth: box.width,
      mainScrollWidth: main.scrollWidth,
      mainClientWidth: main.clientWidth,
      pageErrors: document.querySelectorAll(".katex-error").length,
      motionReduced: window.matchMedia("(prefers-reduced-motion: reduce)").matches,
      theme: document.documentElement.dataset.theme,
      viewportHeight: window.innerHeight,
    };
  });
  expect(layout.documentWidth, `${mode.lang}/${mode.theme}/${mode.device}/${mode.motion}/${route}: document must not overflow horizontally`)
    .toBeLessThanOrEqual(layout.viewportWidth);
  expect(layout.mainLeft, `${route}: main landmark must start inside the viewport`).toBeGreaterThanOrEqual(-1);
  expect(layout.mainRight, `${route}: main landmark must fit the viewport`).toBeLessThanOrEqual(layout.viewportWidth + 1);
  expect(layout.mainWidth).toBeGreaterThan(0);
  expect(layout.pageErrors, `${route}: KaTeX must render without errors`).toBe(0);
  expect(layout.motionReduced).toBe(mode.motion === "reduce");
  expect(layout.theme).toBe(mode.theme);
}

export async function fit_and_pointer_navigation(page: Page, info: TestInfo, mode: MatrixMode) {
  const browserErrors: string[] = [];
  page.on("pageerror", error => browserErrors.push(error.message));
  page.on("console", message => {
    if (message.type() === "error") browserErrors.push(message.text());
  });
  await page.goto("/", { waitUntil: "domcontentloaded" });
  await expect(page.getByRole("heading", { name: /Geophysical inverse problems|Problemas inversos geofísicos/i }))
    .toBeVisible();
  await fit(page, mode, "/");
  await page.goto("/app", { waitUntil: "domcontentloaded" });
  await fit(page, mode, "/app");

  for (const route of routes) {
    const label = route[mode.lang];
    const navigation = page.getByRole("navigation", { name: "Inverse Earth Studio" });
    const link = navigation.getByRole("link", { name: label, exact: true });
    await expect(link).toHaveAccessibleName(label);
    await pointerClick(page, link);
    await expect.poll(() => new URL(page.url()).pathname).toBe(route.path);
    await fit(page, mode, route.path);
    const screenshot = info.outputPath(`${mode.lang}-${mode.theme}-${mode.device}-${mode.motion}-${route.id}.png`);
    await mkdir(dirname(screenshot), { recursive: true });
    await page.screenshot({ path: screenshot, animations: "disabled" });
  }

  const architecture = page.getByRole("button", { name: /architecture|arquitectura/i });
  await expect(architecture).toBeVisible();
  await pointerClick(page, architecture);
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  const tabs = dialog.getByRole("tab");
  await expect(tabs).toHaveCount(5);
  for (let index = 0; index < 5; index++) {
    const tab = tabs.nth(index);
    await tab.evaluate(node => node.scrollIntoView({ block: "center", inline: "nearest", behavior: "instant" }));
    const bounds = await tab.boundingBox();
    expect(bounds, "architecture tab must have painted bounds").not.toBeNull();
    const box = bounds!;
    const viewport = page.viewportSize()!;
    expect(box.x).toBeGreaterThanOrEqual(-1);
    expect(box.x + box.width).toBeLessThanOrEqual(viewport.width + 1);
    expect(box.y).toBeGreaterThanOrEqual(-1);
    expect(box.y + box.height).toBeLessThanOrEqual(viewport.height + 1);
    await page.mouse.move(box.x + box.width / 2, box.y + box.height / 2, { steps: 3 });
    await page.mouse.down();
    await page.mouse.up();
    await expect(tab).toHaveAttribute("aria-selected", "true");
    await expect(dialog.getByRole("tabpanel")).toBeVisible();
  }
  const dialogBounds = await dialog.boundingBox();
  expect(dialogBounds, "architecture dialog must have painted bounds").not.toBeNull();
  expect(dialogBounds!.x).toBeGreaterThanOrEqual(-1);
  expect(dialogBounds!.x + dialogBounds!.width).toBeLessThanOrEqual(mode.device === "phone" ? 391 : 1441);
  expect(dialogBounds!.y).toBeGreaterThanOrEqual(-1);
  expect(dialogBounds!.y + dialogBounds!.height).toBeLessThanOrEqual((await page.evaluate(() => window.innerHeight)) + 1);
  await page.screenshot({
    path: info.outputPath(`${mode.lang}-${mode.theme}-${mode.device}-${mode.motion}-architecture.png`),
    animations: "disabled",
  });
  await page.keyboard.press("Escape");
  await expect(dialog).toBeHidden();
  expect(browserErrors, `${mode.lang}/${mode.theme}/${mode.device}/${mode.motion}: browser errors`).toEqual([]);
}

const sizes = {
  desktop: { width: 1440, height: 900 },
  phone: { width: 390, height: 844 },
} as const;

for (const lang of ["en", "es"] as const) {
  for (const theme of ["light", "dark"] as const) {
    for (const device of ["desktop", "phone"] as const) {
      for (const motion of ["no-preference", "reduce"] as const) {
        const mode: MatrixMode = { lang, theme, device, motion };
        test(`fit_and_pointer_navigation ${lang} ${theme} ${device} ${motion}`, async ({ browser }, info) => {
          const context = await browser.newContext({ viewport: sizes[device], reducedMotion: motion });
          await context.addInitScript(({ language, selectedTheme }) => {
            if (location.protocol === "http:" || location.protocol === "https:") {
              localStorage.setItem("caos.lang", language);
              localStorage.setItem("caos.theme", selectedTheme);
            }
          }, { language: lang, selectedTheme: theme });
          const page = await context.newPage();
          try {
            await fit_and_pointer_navigation(page, info, mode);
          } finally {
            await context.close();
          }
        });
      }
    }
  }
}
