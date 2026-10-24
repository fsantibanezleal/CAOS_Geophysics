import { test, expect, type BrowserContext, type Page } from "@playwright/test";
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { randomUUID } from "node:crypto";

// Real built UI with intercepted protocol responses. NOT live API/host evidence.
const origin = process.env.GEOPHYSICS_QA_URL ?? "http://127.0.0.1:8899";
const evidence = resolve(process.env.GEOPHYSICS_QA_EVIDENCE ?? "../data/experiments/local-account-access/browser");
mkdirSync(evidence, { recursive: true });
const config = { mode: "local", registration_enabled: false, mail_flows_enabled: false };
const ids = ["22222222-2222-4222-8222-222222222222", "33333333-3333-4333-8333-333333333333"];
const user = { id: "11111111-1111-4111-8111-111111111111", email: "first@example.invalid", is_active: true, is_verified: false, is_superuser: false };
async function protocol(context: BrowserContext) {
  const state = { account: null as typeof user | null, badLogin: false, expireAssets: false, profile: config as unknown, unavailable: false, holdConfig: null as Promise<void> | null, deletionStatus: "not_configured" as "not_configured" | "pending_reconciliation", deleted: [] as string[], calls: [] as Array<{ path: string; method: string }> };
  await context.route("**/api/**", async route => {
    const request = route.request(), path = new URL(request.url()).pathname;
    state.calls.push({ path, method: request.method() });
    const json = (body: unknown, status = 200) => route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
    if (path === "/api/auth/config") { const snapshot = state.profile; if (state.holdConfig) await state.holdConfig; return json(snapshot, state.unavailable ? 503 : 200); }
    if (path === "/api/auth/csrf") return json({ csrf_token: "intercepted-csrf" });
    if (path === "/api/auth/me") return state.account ? json(state.account) : json({ detail: "Unauthorized" }, 401);
    if (path === "/api/auth/cookie/login") {
      if (state.badLogin) return json({ detail: "LOGIN_BAD_CREDENTIALS" }, 400);
      const email = new URLSearchParams(request.postData() ?? "").get("username")!;
      state.account = { ...user, email }; return route.fulfill({ status: 204 });
    }
    if (path === "/api/auth/cookie/logout") { state.account = null; return route.fulfill({ status: 204 }); }
    if (!state.account) return json({ detail: "Unauthorized" }, 401);
    if (path === "/api/projects") return json({ projects: ids.map((id, index) => ({ id, name: `${state.account!.email.startsWith("second") ? "Second owner" : "First owner"} survey ${index + 1}`, description: "Intercepted private project", created_at: "2026-10-03T12:00:00Z", updated_at: "2026-10-03T12:00:00Z" })).filter(project => !state.deleted.includes(project.id)) });
    if (request.method() === "DELETE" && ids.some(id => path === `/api/projects/${id}`)) {
      const id = path.split("/").at(-1)!; state.deleted.push(id);
      return json({ deleted: true, project_id: id, receipt_id: "44444444-4444-4444-8444-444444444444", backup_erasure_status: "not_attempted", external_backup_status: state.deletionStatus });
    }
    if (path.endsWith("/assets")) return state.expireAssets ? json({ detail: "Unauthorized" }, 401) : json({ assets: [] });
    throw new Error(`Unexpected intercepted endpoint ${request.method()} ${path}`);
  });
  return state;
}
async function open(page: Page, es = false) {
  await page.goto(origin + "/");
  await page.getByRole("button", { name: es ? "Proyectos y datos originales" : "Projects & raw data", exact: true }).click();
  await expect(page.getByRole("button", { name: es ? "Iniciar sesión" : "Sign in", exact: true })).toBeVisible();
}
async function login(page: Page, es = false, email = user.email) {
  await page.getByLabel(es ? "Correo" : "Email", { exact: true }).fill(email);
  // Random, transient test input, never an operator credential or receipt field.
  await page.getByLabel(es ? "Contraseña" : "Password", { exact: true }).fill(randomUUID());
  await page.getByLabel(es ? "Contraseña" : "Password", { exact: true }).press("Enter");
}

for (const lang of ["en", "es"] as const) for (const theme of ["light", "dark"] as const) for (const device of ["desktop", "phone"] as const) {
  test(`local login-only real UI ${lang} ${theme} ${device}`, async ({ browser }) => {
    const context = await browser.newContext({ viewport: device === "phone" ? { width: 390, height: 844 } : { width: 1440, height: 900 } });
    await context.addInitScript(({ lang, theme }) => { localStorage.setItem("caos.lang", lang); localStorage.setItem("caos.theme", theme); }, { lang, theme });
    const state = await protocol(context), page = await context.newPage(), es = lang === "es", errors: string[] = [];
    page.on("pageerror", error => errors.push(error.message));
    await open(page, es);
    const dialog = page.getByRole("dialog");
    await expect(page.locator("html")).toHaveAttribute("data-theme", theme);
    await expect(dialog).toContainText(es ? "administradas por el operador" : "managed by the operator");
    await expect(dialog.getByRole("combobox")).toHaveCount(0);
    await expect(dialog.getByText(/Register|Registrarse|Verify email|Verificar correo|reset token|restablecimiento|forgot/i)).toHaveCount(0);
    await expect(dialog.getByRole("button", { name: /Create project|Crear proyecto|Upload original|Cargar original|Submit.*job/ })).toHaveCount(0);
    expect(await dialog.evaluate(node => node.contains(document.activeElement))).toBe(true);
    expect(await dialog.evaluate(node => node.scrollWidth <= node.clientWidth + 1)).toBe(true);
    await page.screenshot({ path: resolve(evidence, `${lang}-${theme}-${device}-guest.png`) });
    await page.keyboard.press("Escape"); await expect(dialog).toHaveCount(0);
    await expect(page.getByRole("button", { name: es ? "Proyectos y datos originales" : "Projects & raw data", exact: true })).toBeFocused();
    await page.getByRole("button", { name: es ? "Proyectos y datos originales" : "Projects & raw data", exact: true }).click();
    await expect(page.getByLabel(es ? "Correo" : "Email", { exact: true })).toBeVisible();
    await login(page, es);
    await expect(dialog).toContainText(es ? "cuenta local autenticada" : "authenticated local account");
    await expect(dialog).not.toContainText(es ? "titular verificado" : "verified owner");
    const selected = page.getByRole("combobox", { name: es ? "Proyecto seleccionado" : "Selected project", exact: true });
    await expect(selected.locator("option")).toHaveCount(2); await selected.selectOption(ids[1]); await expect(selected).toHaveValue(ids[1]);
    expect(await dialog.evaluate(node => node.scrollWidth <= node.clientWidth + 1)).toBe(true);
    await page.screenshot({ path: resolve(evidence, `${lang}-${theme}-${device}-owner.png`) });
    await page.getByRole("button", { name: es ? "Agregar original" : "Add original", exact: true }).click();
    await expect(page.getByRole("button", { name: es ? "Cargar bytes originales" : "Upload original bytes", exact: true })).toBeDisabled();
    await page.getByRole("combobox", { name: es ? "Sección de proyectos" : "Project workspace section", exact: true }).selectOption("account");
    await page.getByRole("button", { name: es ? "Cerrar sesión" : "Sign out", exact: true }).click();
    await expect(page.getByLabel(es ? "Contraseña" : "Password", { exact: true })).toHaveValue("");
    await expect(dialog).not.toContainText("First owner survey");
    expect(state.calls.filter(call => /register|verify|reset-password/.test(call.path))).toEqual([]);
    expect(await page.evaluate(() => Object.keys(localStorage).filter(key => /password|token|session|credential/i.test(key)))).toEqual([]);
    expect(errors).toEqual([]); await context.close();
  });
}

test("invalid login clears secret; plural account switch and expiry clear private state", async ({ browser }) => {
  const context = await browser.newContext(); const state = await protocol(context), page = await context.newPage();
  await context.addInitScript(() => localStorage.setItem("caos.lang", "en"));
  await open(page); state.badLogin = true; await login(page);
  await expect(page.getByRole("alert")).toContainText("account is unavailable");
  await expect(page.getByLabel("Password", { exact: true })).toHaveValue("");
  await expect(page.getByLabel("Email", { exact: true })).toHaveValue(user.email);
  state.badLogin = false; await login(page);
  await page.getByRole("combobox", { name: "Project workspace section", exact: true }).selectOption("account");
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await login(page, false, "second@example.invalid");
  await expect(page.getByRole("combobox", { name: "Selected project", exact: true })).toContainText("Second owner survey");
  await expect(page.getByRole("dialog")).not.toContainText("First owner survey");
  state.expireAssets = true;
  await page.getByRole("combobox", { name: "Selected project", exact: true }).selectOption(ids[1]);
  await expect(page.getByRole("alert")).toContainText("Session expired");
  await expect(page.getByLabel("Password", { exact: true })).toBeVisible();
  await expect(page.getByRole("button", { name: "Create project", exact: true })).toHaveCount(0);
  await context.close();
});

test("anonymous browser MT forward calculator remains interactive without an API request", async ({ browser }) => {
  const context = await browser.newContext(); const state = await protocol(context), page = await context.newPage();
  await context.addInitScript(() => localStorage.setItem("caos.lang", "en"));
  await page.goto(origin + "/experiments");
  await page.getByRole("tab", { name: "MT forward and EDI evidence", exact: true }).click();
  await expect(page.getByRole("heading", { name: "Layered-earth MT forward response", exact: true })).toBeVisible();
  const layer = page.getByRole("slider", { name: "Layer 1 Ω m", exact: true });
  await layer.fill("3");
  await expect(layer).toHaveValue("3");
  await expect(page.getByRole("button", { name: "Download model + response", exact: true })).toBeEnabled();
  expect(state.calls).toEqual([]);
  await context.close();
});

test("unknown/unavailable profiles fail private closed without blocking six public routes or replay", async ({ browser }) => {
  const context = await browser.newContext(); const state = await protocol(context), page = await context.newPage();
  await context.addInitScript(() => localStorage.setItem("caos.lang", "en"));
  for (const route of ["/", "/introduction", "/methodology", "/implementation", "/experiments", "/benchmark"]) {
    await page.goto(origin + route); await expect(page.locator("main")).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Inverse Earth Studio" }).getByRole("link")).toHaveCount(6);
  }
  expect(state.calls).toEqual([]);
  await page.goto(origin + "/");
  await expect(page.getByRole("tab", { name: "Model", exact: true })).toBeVisible();
  await page.getByRole("button", { name: "Replay", exact: true }).click();
  await expect(page.getByRole("button", { name: /Export run/ })).toBeEnabled();
  state.profile = { ...config, mode: "unrecognized" };
  await page.getByRole("button", { name: "Projects & raw data", exact: true }).click();
  await expect(page.getByRole("button", { name: "Retry service check" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Sign in", exact: true })).toHaveCount(0);
  state.unavailable = true; state.profile = config;
  await page.getByRole("button", { name: "Retry service check" }).click();
  await expect(page.getByRole("alert")).toContainText("503");
  await page.keyboard.press("Escape");
  await expect(page.getByRole("button", { name: /Export run/ })).toBeEnabled();
  expect(state.calls.every(call => call.path === "/api/auth/config" && call.method === "GET")).toBe(true);
  await context.close();
});

test("direct private project and MT URLs deny guests before project/upload/server-job requests", async ({ browser }) => {
  const context = await browser.newContext(); const state = await protocol(context), page = await context.newPage();
  await context.addInitScript(() => localStorage.setItem("caos.lang", "en"));
  for (const suffix of ["", "&instrument=mt"]) {
    await page.goto(origin + `/?project=${ids[0]}${suffix}`);
    await expect(page.locator(".load-state")).toContainText(suffix ? "Sign in through Projects or retry the unavailable project service." : "Sign in through Projects to load this private project.");
    await expect(page.getByRole("button", { name: /Submit.*job|Validate station table|Upload original bytes/ })).toHaveCount(0);
  }
  expect(state.calls.some(call => call.path.startsWith("/api/projects") || call.method !== "GET")).toBe(false);
  await context.close();
});

test("anonymous reviewed M13 model performs actual browser inference without any API call", async ({ browser }) => {
  test.setTimeout(120_000);
  const context = await browser.newContext(); const state = await protocol(context), page = await context.newPage();
  await context.addInitScript(() => localStorage.setItem("caos.lang", "en"));
  await page.goto(origin + "/benchmark#phase-picker");
  await page.getByRole("button", { name: "Load reviewed STEAD assets", exact: true }).click();
  const inference = page.getByRole("button", { name: "Run browser inference", exact: true });
  await expect(inference).toBeEnabled({ timeout: 60_000 });
  await inference.click();
  await expect(page.getByRole("button", { name: "Export N/P/S scores (.f32)", exact: true })).toBeEnabled({ timeout: 60_000 });
  expect(state.calls).toEqual([]);
  await context.close();
});

test("closing a pending probe prevents late owner restoration on a reopened guest drawer", async ({ browser }) => {
  const context = await browser.newContext(); const state = await protocol(context), page = await context.newPage();
  await context.addInitScript(() => localStorage.setItem("caos.lang", "en"));
  let release!: () => void; state.holdConfig = new Promise<void>(resolve => { release = resolve; });
  await page.goto(origin + "/"); await page.getByRole("button", { name: "Projects & raw data", exact: true }).click();
  await expect.poll(() => state.calls.some(call => call.path === "/api/auth/config")).toBe(true);
  await page.keyboard.press("Escape"); state.holdConfig = null;
  await page.getByRole("button", { name: "Projects & raw data", exact: true }).click();
  await expect(page.getByLabel("Password", { exact: true })).toBeVisible(); release();
  await expect(page.getByRole("button", { name: "Create project", exact: true })).toHaveCount(0);
  await expect(page.getByLabel("Password", { exact: true })).toHaveValue("");
  await context.close();
});

test("inactive account receives no private controls; explicit email flags alone reveal compatibility actions", async ({ browser }) => {
  const context = await browser.newContext(); const state = await protocol(context), page = await context.newPage();
  await context.addInitScript(() => localStorage.setItem("caos.lang", "en"));
  state.account = { ...user, is_active: false };
  await open(page);
  await expect(page.getByRole("button", { name: "Create project", exact: true })).toHaveCount(0);
  expect(state.calls.some(call => call.path.startsWith("/api/projects"))).toBe(false);
  await page.keyboard.press("Escape"); state.account = null;
  state.profile = { mode: "email", registration_enabled: true, mail_flows_enabled: true };
  await page.getByRole("button", { name: "Projects & raw data", exact: true }).click();
  const actions = page.getByRole("combobox", { name: "Account action", exact: true });
  await expect(actions.locator("option")).toHaveCount(5);
  await page.keyboard.press("Escape");
  state.profile = { mode: "email", registration_enabled: false, mail_flows_enabled: false };
  await page.getByRole("button", { name: "Projects & raw data", exact: true }).click();
  await expect(page.getByRole("button", { name: "Sign in", exact: true })).toBeVisible();
  await expect(actions).toHaveCount(0);
  expect(state.calls.some(call => call.method !== "GET")).toBe(false);
  await context.close();
});

for (const lang of ["en", "es"] as const) for (const status of ["not_configured", "pending_reconciliation"] as const) {
  test(`exact deletion wire state ${status} ${lang}, no invented external backup`, async ({ browser }) => {
    const context = await browser.newContext(); const state = await protocol(context), page = await context.newPage(), es = lang === "es";
    await context.addInitScript(language => localStorage.setItem("caos.lang", language), lang);
    state.deletionStatus = status;
    state.account = { ...user, is_verified: status === "pending_reconciliation" };
    if (status === "pending_reconciliation") state.profile = { mode: "email", registration_enabled: true, mail_flows_enabled: true };
    await page.goto(origin + "/");
    await page.getByRole("button", { name: es ? "Proyectos y datos originales" : "Projects & raw data", exact: true }).click();
    await page.getByRole("textbox", { name: es ? /Escriba el nombre exacto para confirmar/ : /Type the exact project name to confirm/ }).fill("First owner survey 1");
    await page.getByRole("button", { name: es ? "Eliminar proyecto y solicitar recibo" : "Delete project and request receipt", exact: true }).click();
    await expect(page.getByRole("dialog")).toContainText(status === "not_configured" ? es ? "No hay respaldos externos configurados" : "External backups are not configured" : es ? "esto no demuestra que exista un respaldo externo" : "this is not evidence that an external backup exists");
    await expect(page.getByRole("combobox", { name: es ? "Proyecto seleccionado" : "Selected project", exact: true }).locator("option")).toHaveCount(1);
    await context.close();
  });
}
