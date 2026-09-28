import { test, expect } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

const origin = process.env.GEOPHYSICS_LEGACY_URL ?? "http://127.0.0.1:8766";
const evidence = resolve("../data/raw/qa-browser-screenshots");
mkdirSync(evidence, { recursive: true });

for (const lang of ["en", "es"] as const) {
  test(`legacy static build keeps six guest routes and no account affordance · ${lang}`, async ({ browser }) => {
    const context = await browser.newContext({ viewport: { width: 390, height: 844 } });
    await context.addInitScript(language => localStorage.setItem("caos.lang", language), lang);
    const page = await context.newPage();
    await page.goto(origin + "/");
    await expect(page.getByRole("combobox", { name: lang === "es" ? "Caso geológico" : "Geological case" })).toBeVisible();
    await expect(page.getByRole("tab", { name: lang === "es" ? "Modelo" : "Model" })).toBeVisible();
    await expect(page.getByRole("button", { name: lang === "es" ? "Proyectos y datos originales" : "Projects & raw data" })).toHaveCount(0);
    const navigation = page.getByRole("navigation", { name: "Inverse Earth Studio" });
    await expect(navigation.getByRole("link")).toHaveCount(6);
    await page.screenshot({ path: resolve(evidence, `legacy-${lang}-phone.png`), fullPage: false });
    await context.close();
  });
}
