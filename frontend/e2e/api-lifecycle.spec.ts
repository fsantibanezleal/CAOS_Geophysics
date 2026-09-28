import { test, expect, type Browser, type APIRequestContext } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";

const origin = process.env.GEOPHYSICS_QA_URL ?? "http://127.0.0.1:8765";
const evidence = resolve("../data/raw/qa-browser-screenshots");
mkdirSync(evidence, { recursive: true });
test.describe.configure({ mode: "serial" });
test.setTimeout(120_000);

async function open(browser: Browser, lang: "en" | "es", phone: boolean) {
  const context = await browser.newContext({ viewport: phone ? { width: 390, height: 844 } : { width: 1440, height: 900 }, acceptDownloads: true });
  await context.addInitScript(language => localStorage.setItem("caos.lang", language), lang);
  const page = await context.newPage();
  await page.goto(origin + "/");
  await page.getByRole("button", { name: lang === "es" ? "Proyectos y datos originales" : "Projects & raw data" }).click();
  await expect(page.getByRole("dialog")).toBeVisible();
  await expect(page.getByRole("combobox", { name: lang === "es" ? "Acción de cuenta" : "Account action", exact: true })).toBeVisible();
  await page.screenshot({ path: resolve(evidence, `${lang}-${phone ? "phone" : "desktop"}-guest.png`), fullPage: false });
  const fits = await page.getByRole("dialog").evaluate(node => node.scrollWidth <= node.clientWidth + 2);
  expect(fits).toBe(true);
  return { context, page };
}

async function token(request: APIRequestContext): Promise<string> {
  const response = await request.get(origin + "/__qa/mail/latest");
  expect(response.ok()).toBe(true);
  const payload = await response.json();
  expect(payload.token).toBeTruthy();
  return payload.token;
}

for (const { lang, phone } of [{ lang: "en" as const, phone: false }, { lang: "es" as const, phone: true }]) {
  test(`real API account, raw receipt and deletion · ${lang} ${phone ? "phone" : "desktop"}`, async ({ browser, request }) => {
    const { context, page } = await open(browser, lang, phone);
    const es = lang === "es";
    const email = `qa-${lang}-${phone ? "phone" : "desktop"}@example.org`;
    const password = "correct horse battery staple";
    const projectName = `QA ${lang} survey`;
    await page.getByRole("combobox", { name: es ? "Acción de cuenta" : "Account action", exact: true }).selectOption("register");
    await page.getByRole("textbox", { name: es ? "Correo" : "Email", exact: true }).fill(email);
    await page.getByLabel(es ? "Contraseña" : "Password", { exact: true }).fill(password);
    await page.getByRole("button", { name: es ? "Registrarse" : "Register" }).click();
    await expect(page.getByLabel(es ? "Código enviado por correo" : "Email token", { exact: true })).toBeVisible();
    await page.getByLabel(es ? "Código enviado por correo" : "Email token", { exact: true }).fill(await token(request));
    await page.getByRole("button", { name: es ? "Verificar cuenta" : "Verify account" }).click();
    await expect(page.getByRole("button", { name: es ? "Iniciar sesión" : "Sign in" })).toBeVisible();
    await page.getByRole("textbox", { name: es ? "Correo" : "Email", exact: true }).fill(email);
    await page.getByLabel(es ? "Contraseña" : "Password", { exact: true }).fill(password);
    await page.getByRole("button", { name: es ? "Iniciar sesión" : "Sign in" }).click();
    await expect(page.getByText(email)).toBeVisible();
    await page.getByLabel(es ? "Nombre del proyecto" : "Project name", { exact: true }).fill(projectName);
    await page.getByLabel(es ? "Descripción" : "Description", { exact: true }).fill("Test original bytes");
    await page.getByRole("button", { name: es ? "Crear proyecto" : "Create project" }).click();
    await expect(page.getByLabel(es ? "Archivo original local" : "Local original file", { exact: true })).toBeVisible();
    await page.screenshot({ path: resolve(evidence, `${lang}-${phone ? "phone" : "desktop"}-upload.png`), fullPage: false });
    await page.getByLabel(es ? "Archivo original local" : "Local original file", { exact: true }).setInputFiles({ name: "stations.csv", mimeType: "text/csv", buffer: Buffer.from("station,x,y,z,g\nS1,0,0,100,9.81\nS2,10,0,100,9.80\n") });
    await page.getByRole("combobox", { name: es ? "Formato original declarado" : "Declared raw format", exact: true }).selectOption("gravity_csv");
    await page.getByLabel(es ? "Proveedor o titular de adquisición" : "Provider or acquisition owner", { exact: true }).fill("QA survey owner");
    await page.getByLabel(es ? "Declaración de derechos y fundamento del permiso" : "Rights statement and permission basis", { exact: true }).fill("I have permission to store this original privately.");
    await page.getByRole("combobox", { name: es ? "Decisión de derechos públicos (no publica esta carga)" : "Public rights decision (does not publish this upload)", exact: true }).selectOption("provider-link-only");
    await page.getByLabel(es ? "Atribución requerida" : "Required attribution", { exact: true }).fill("QA survey");
    await page.getByRole("dialog").getByRole("checkbox").check();
    await page.getByRole("combobox", { name: es ? "Referencia de coordenadas" : "Coordinate reference", exact: true }).selectOption("epsg");
    await page.getByLabel(es ? "Código EPSG" : "EPSG code", { exact: true }).fill("32719");
    await page.getByRole("combobox", { name: es ? "Orden de ejes" : "Coordinate axis order", exact: true }).selectOption("xy");
    await page.getByLabel(es ? "Datum horizontal (nombre declarado exacto)" : "Horizontal datum (exact declared name)", { exact: true }).fill("unresolved datum");
    await page.getByLabel(es ? "Datum vertical" : "Vertical datum", { exact: true }).fill("survey benchmark");
    await page.getByRole("combobox", { name: es ? "Dirección vertical positiva" : "Positive vertical direction", exact: true }).selectOption("up");
    await page.getByRole("combobox", { name: es ? "Unidad horizontal" : "Horizontal coordinate unit", exact: true }).selectOption("m");
    await page.getByRole("combobox", { name: es ? "Unidad vertical" : "Vertical coordinate unit", exact: true }).selectOption("m");
    await page.getByRole("combobox", { name: es ? "Unidad de medición" : "Measurement unit", exact: true }).selectOption("mGal");
    await page.getByLabel(es ? "Época de adquisición con zona UTC (ISO 8601)" : "Acquisition epoch with UTC offset (ISO 8601)", { exact: true }).fill("2026-09-27T12:00:00Z");
    await page.getByRole("combobox", { name: es ? "Orientación/marco de componentes" : "Component orientation/frame", exact: true }).selectOption("local vertical down");
    for (const [en, spanish, value] of [["Station ID column", "Columna de estación", "station"], ["X column", "Columna X", "x"], ["Y column", "Columna Y", "y"], ["Z column", "Columna Z", "z"], ["Value column", "Columna de valor", "g"]])
      await page.getByLabel(es ? spanish : en, { exact: true }).fill(value);
    await page.getByRole("button", { name: es ? "Cargar bytes originales" : "Upload original bytes" }).click();
    await expect(page.getByRole("dialog").getByRole("alert")).toContainText("physical.horizontal_datum");
    await page.screenshot({ path: resolve(evidence, `${lang}-${phone ? "phone" : "desktop"}-validation.png`), fullPage: false });
    await page.getByLabel(es ? "Datum horizontal (nombre declarado exacto)" : "Horizontal datum (exact declared name)", { exact: true }).fill("WGS84");
    await page.getByRole("button", { name: es ? "Cargar bytes originales" : "Upload original bytes" }).click();
    await expect(page.getByRole("heading", { name: es ? "Recibo de carga del titular" : "Owner upload receipt" })).toBeVisible();
    await expect(page.getByText(es ? "Metadatos originales revisados; control científico no realizado" : "Raw metadata checked; scientific QC not performed")).toBeVisible();
    await page.screenshot({ path: resolve(evidence, `${lang}-${phone ? "phone" : "desktop"}-receipt.png`), fullPage: false });
    const [rawDownload] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: es ? "Descargar original verificado" : "Download verified original" }).click()]);
    expect(rawDownload.suggestedFilename()).toBe("stations.csv");
    await page.getByRole("combobox", { name: es ? "Sección de proyectos" : "Project workspace section", exact: true }).selectOption("projects");
    const [zipDownload] = await Promise.all([page.waitForEvent("download"), page.getByRole("button", { name: es ? "Exportar ZIP" : "Export ZIP" }).click()]);
    expect(zipDownload.suggestedFilename()).toMatch(/^project-.*\.zip$/);
    await page.getByLabel(es ? `Escriba el nombre exacto para confirmar: ${projectName}` : `Type the exact project name to confirm: ${projectName}`, { exact: true }).fill(projectName);
    await page.getByRole("button", { name: es ? "Eliminar proyecto y solicitar recibo" : "Delete project and request receipt" }).click();
    await expect(page.getByText(es ? "No se intentó borrar respaldos; conciliación de respaldos externos pendiente." : "Backup erasure not attempted; external backup reconciliation pending.")).toBeVisible();
    await page.screenshot({ path: resolve(evidence, `${lang}-${phone ? "phone" : "desktop"}-deletion.png`), fullPage: false });
    await page.getByRole("combobox", { name: es ? "Sección de proyectos" : "Project workspace section", exact: true }).selectOption("account");
    await page.getByRole("button", { name: es ? "Cerrar sesión" : "Sign out" }).click();
    await expect(page.getByRole("combobox", { name: es ? "Acción de cuenta" : "Account action", exact: true })).toBeVisible();
    if (!es) {
      await page.getByRole("combobox", { name: "Account action", exact: true }).selectOption("recover");
      await page.getByRole("textbox", { name: "Email", exact: true }).fill(email);
      await page.getByRole("button", { name: "Send reset token" }).click();
      await expect(page.getByText("If the account exists, a reset token was emailed.")).toBeVisible();
      await page.getByRole("textbox", { name: "Email token", exact: true }).fill(await token(request));
      await page.getByLabel("New password (12+ characters)", { exact: true }).fill("another long secure password");
      await page.getByRole("button", { name: "Change password" }).click();
      await expect(page.getByText("Password changed. Sign in again.")).toBeVisible();
    }
    await context.close();
  });
}

test("cross-size guest EN phone and ES desktop keep curated App readable", async ({ browser }) => {
  for (const [lang, phone] of [["en", true], ["es", false]] as const) {
    const { context, page } = await open(browser, lang, phone);
    const launcher = page.getByRole("button", { name: lang === "es" ? "Proyectos y datos originales" : "Projects & raw data" });
    await page.getByRole("button", { name: lang === "es" ? "Cerrar proyectos" : "Close projects" }).click();
    await expect(page.getByRole("dialog")).toHaveCount(0);
    await expect(launcher).toBeFocused();
    await expect(page.getByRole("combobox", { name: lang === "es" ? "Caso geológico" : "Geological case" })).toBeVisible();
    await context.close();
  }
});
