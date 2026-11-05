import { expect, test } from "@playwright/test";

const modes = [
  { lang: "en", theme: "light", device: "desktop", width: 1440, height: 960 },
  { lang: "en", theme: "dark", device: "phone", width: 390, height: 844 },
  { lang: "es", theme: "light", device: "phone", width: 390, height: 844 },
  { lang: "es", theme: "dark", device: "desktop", width: 1440, height: 960 },
] as const;

for (const mode of modes) {
  test(`Long Valley field workflow ${mode.lang}/${mode.theme}/${mode.device}`, async ({ page }, info) => {
    const errors: string[] = [];
    page.on("pageerror", error => errors.push(error.message));
    await page.setViewportSize({ width: mode.width, height: mode.height });
    await page.addInitScript(({ language, selectedTheme }) => {
      localStorage.setItem("caos.lang", language);
      localStorage.setItem("caos.theme", selectedTheme);
    }, { language: mode.lang, selectedTheme: mode.theme });
    await page.goto("/experiments");
    await page.getByRole("tab", { name: mode.lang === "es" ? "¿Qué evidencia muestra cada método?" : "What evidence does each method show?" }).click();
    const tab = mode.lang === "es" ? "Registro de campo Long Valley" : "Long Valley field record";
    await page.getByRole("tab", { name: tab }).click();
    const title = mode.lang === "es"
      ? /Long Valley · observaciones gravimétricas repetidas por estación/
      : /Long Valley · repeated-station gravity observations/;
    await expect(page.getByRole("heading", { name: title })).toBeVisible();
    await expect(page.getByText("37 / 37", { exact: true })).toBeVisible();
    await expect(page.locator(".lv-network-map circle")).toHaveCount(37);
    await page.getByRole("button", { name: /12DOR75:/ }).click();
    await expect(page.getByText(/Station 12DOR75|Estación 12DOR75/)).toBeVisible();

    const summary = mode.lang === "es"
      ? "Inspeccionar valores emparejados e incertidumbre propagada"
      : "Inspect paired station values and propagated uncertainty";
    await page.getByText(summary, { exact: true }).click();
    const stationRow = page.locator(".lv-record tbody tr").filter({ hasText: "12DOR75" });
    await expect(stationRow).toBeVisible();
    await page.getByLabel(mode.lang === "es" ? "Ocupación anterior A" : "Earlier occupation A").selectOption("1982-09");
    await expect(page.locator(".lv-network-map circle")).toHaveCount(23);
    await expect(page.getByText("23 / 37", { exact: true })).toBeVisible();
    await expect(page.getByText(mode.lang === "es" ? /La lectura archivada de 1JD1952/ : /The archived 1JD1952 reading/)).toBeVisible();
    await page.screenshot({ path: info.outputPath(`${mode.lang}-${mode.theme}-${mode.device}-qc-default.png`), fullPage: true, animations: "disabled" });
    await page.getByRole("checkbox").check();
    await expect(page.locator(".lv-network-map circle")).toHaveCount(24);
    await expect(page.getByText("24 / 37", { exact: true })).toBeVisible();
    await expect(page.getByText(mode.lang === "es" ? "Sospechoso · sin resolver" : "Suspect · unresolved")).toBeVisible();
    await page.getByRole("button", { name: "1JD1952", exact: true }).click();
    await expect(page.getByText(/Station 1JD1952|Estación 1JD1952/)).toBeVisible();
    await expect(page.locator(".lv-history-chart title").filter({ hasText: "suspect source observation" })).toHaveCount(1);
    await page.screenshot({ path: info.outputPath(`${mode.lang}-${mode.theme}-${mode.device}-qc-included.png`), fullPage: true, animations: "disabled" });

    const layout = await page.evaluate(() => ({ width: innerWidth, scroll: document.documentElement.scrollWidth }));
    expect(layout.scroll, `${mode.lang}/${mode.device}: page must not overflow horizontally`).toBeLessThanOrEqual(layout.width + 1);
    expect(errors, `${mode.lang}/${mode.theme}/${mode.device}: browser errors`).toEqual([]);
  });
}
