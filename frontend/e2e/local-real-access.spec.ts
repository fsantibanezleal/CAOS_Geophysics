import { test, expect, type BrowserContext, type Page } from "@playwright/test";
import { spawn, execFileSync, type ChildProcess } from "node:child_process";
import { createServer } from "node:net";
import { createHash, randomUUID } from "node:crypto";
import { existsSync, readFileSync, readdirSync, mkdirSync, writeFileSync } from "node:fs";
import { resolve, join } from "node:path";

// Opt-in actual HTTP integration, never route-intercepted or an operating-host gate.
const required = (name: string) => { const value = process.env[name]; if (!value) throw new Error(`Set ${name} to the trusted existing local review resource`); return resolve(value); };
let server: ChildProcess, origin: string, checkout: string, build: string, qaRoot: string;
let before: Record<string, string>, frontendBefore: Record<string, string>, ownerDbHash: string | null;
let ownerDb: string, backendRevision: string;
let harnessBefore: Record<string, string>;
const accounts = [0, 1].map(() => ({ email: `qa-${randomUUID()}@example.org`, password: randomUUID() + randomUUID() }));
const evidence = resolve(process.env.GEOPHYSICS_QA_EVIDENCE ?? "../data/experiments/local-account-access/real-http");
const sha = (path: string) => createHash("sha256").update(readFileSync(path)).digest("hex");
function inventory(root: string, relative = ""): Record<string, string> {
  return Object.fromEntries(readdirSync(join(root, relative), { withFileTypes: true }).flatMap(item => {
    const path = join(relative, item.name);
    return item.isDirectory() ? Object.entries(inventory(root, path)) : [[path.replaceAll("\\", "/"), sha(join(root, path))]];
  }).sort(([a], [b]) => a.localeCompare(b)));
}
async function unusedPort(): Promise<number> {
  const socket = createServer(); await new Promise<void>(resolve => socket.listen(0, "127.0.0.1", resolve));
  const address = socket.address(); if (!address || typeof address === "string") throw new Error("No loopback test port");
  await new Promise<void>((resolve, reject) => socket.close(error => error ? reject(error) : resolve())); return address.port;
}
test.beforeEach(async () => {
  test.setTimeout(60_000);
  checkout = required("GEOPHYSICS_REVIEW_CHECKOUT"); build = required("GEOPHYSICS_REVIEW_BUILD");
  const python = required("GEOPHYSICS_REVIEW_PYTHON"), port = await unusedPort(); origin = `http://127.0.0.1:${port}`;
  qaRoot = join(checkout, "data", "raw", `frontend-local-account-review-${randomUUID()}`);
  before = inventory(join(checkout, "app"));
  ownerDb = required("GEOPHYSICS_OPERATOR_DB_GUARD"); ownerDbHash = sha(ownerDb);
  backendRevision = process.env.GEOPHYSICS_REVIEW_BACKEND_REVISION ?? "";
  if (!/^[0-9a-f]{40}$/.test(backendRevision)) throw new Error("Supply the exact immutable backend source revision");
  for (const [path, actual] of Object.entries(before)) {
    const committed = execFileSync("git", ["show", `${backendRevision}:app/${path}`], { cwd: checkout, maxBuffer: 16 * 1024 * 1024 });
    expect(actual).toBe(createHash("sha256").update(committed).digest("hex"));
  }
  frontendBefore = inventory(build);
  harnessBefore = Object.fromEntries(["e2e/local-api-server.py", "e2e/local-real-access.spec.ts",
    "src/api/lifecycle.ts", "src/components/ProjectDrawer.tsx"].map(path => [path, sha(resolve(path))]));
  mkdirSync(evidence, { recursive: true });
  server = spawn(python, [resolve("e2e/local-api-server.py")], { cwd: checkout, windowsHide: true,
    env: { ...process.env, PYTHONDONTWRITEBYTECODE: "1", PYTHONPATH: checkout,
      GEOPHYSICS_REAL_QA_ROOT: qaRoot, GEOPHYSICS_REAL_QA_ORIGIN: origin,
      GEOPHYSICS_REAL_QA_PORT: String(port), GEOPHYSICS_REVIEW_BUILD: build }, stdio: ["pipe", "pipe", "pipe"] });
  server.stdin!.end(JSON.stringify({ accounts }) + "\n");
  server.stdout!.resume();
  let failure = ""; server.stderr!.on("data", bytes => { failure += String(bytes); });
  await expect.poll(async () => {
    if (server.exitCode !== null) throw new Error(`Real test server exited ${server.exitCode}: ${failure}`);
    try { const response = await fetch(origin + "/api/auth/config"); return response.ok; } catch { return false; }
  }, { timeout: 45_000 }).toBe(true);
  const actual = await (await fetch(origin + "/api/auth/config")).json();
  expect(actual).toEqual({ mode: "local", registration_enabled: false, mail_flows_enabled: false });
});
test.afterEach(async () => {
  if (server && server.exitCode === null) {
    const exited = new Promise<void>(done => server.once("exit", () => done()));
    server.kill(); await exited;
  }
  if (!checkout || !before) return;
  const after = inventory(join(checkout, "app"));
  const frontendAfter = inventory(build);
  const harnessAfter = Object.fromEntries(Object.keys(harnessBefore).map(path => [path, sha(resolve(path))]));
  const ownerDbAfter = existsSync(ownerDb) ? sha(ownerDb) : null;
  writeFileSync(join(evidence, `source-and-storage-${qaRoot.split(/[\\/]/).at(-1)}.json`), JSON.stringify({ schema: "caos.local-account-http-review.v1",
    backend_revision: backendRevision, source_kind: "immutable git archive; actual extracted file hashes below",
    backend_sha256_before: before, backend_sha256_after: after, frontend_index_sha256: sha(join(build, "index.html")),
    frontend_sha256_before: frontendBefore, frontend_sha256_after: frontendAfter,
    harness_and_frontend_source_sha256_before: harnessBefore, harness_and_frontend_source_sha256_after: harnessAfter,
    existing_owner_db_sha256_before: ownerDbHash, existing_owner_db_sha256_after: ownerDbAfter,
    source_unchanged: JSON.stringify(before) === JSON.stringify(after), owner_db_unchanged: ownerDbHash === ownerDbAfter,
    private_qa_root: qaRoot, transport: "actual HTTP loopback", cookie_secure: false,
    api_interception: false, smtp: false, workers_started: false, credentials_recorded: false }, null, 2));
  expect(after).toEqual(before); expect(frontendAfter).toEqual(frontendBefore);
  expect(harnessAfter).toEqual(harnessBefore); expect(ownerDbAfter).toBe(ownerDbHash);
});
async function session(context: BrowserContext, lang = "en", theme = "light") {
  await context.addInitScript(({ lang, theme }) => { localStorage.setItem("caos.lang", lang); localStorage.setItem("caos.theme", theme); }, { lang, theme });
  const page = await context.newPage(); await page.goto(origin + "/");
  await page.getByRole("button", { name: lang === "es" ? "Proyectos y datos originales" : "Projects & raw data", exact: true }).click(); return page;
}
async function login(page: Page, account: typeof accounts[number], es: boolean) {
  await page.getByLabel(es ? "Correo" : "Email", { exact: true }).fill(account.email);
  await page.getByLabel(es ? "Contraseña" : "Password", { exact: true }).fill(account.password);
  await page.getByLabel(es ? "Contraseña" : "Password", { exact: true }).press("Enter");
}
async function create(page: Page, name: string, es: boolean) {
  await page.getByRole("combobox", { name: es ? "Sección de proyectos" : "Project workspace section", exact: true }).selectOption("projects");
  await page.getByLabel(es ? "Nombre del proyecto" : "Project name", { exact: true }).fill(name);
  await page.getByRole("button", { name: es ? "Crear proyecto" : "Create project", exact: true }).click();
  await expect(page.getByRole("combobox", { name: es ? "Sección de proyectos" : "Project workspace section", exact: true })).toHaveValue("upload");
  await page.getByRole("combobox", { name: es ? "Sección de proyectos" : "Project workspace section", exact: true }).selectOption("projects");
}
async function logout(page: Page, es: boolean) {
  await page.getByRole("combobox", { name: es ? "Sección de proyectos" : "Project workspace section", exact: true }).selectOption("account");
  await page.getByRole("button", { name: es ? "Cerrar sesión" : "Sign out", exact: true }).click();
  await expect(page.getByLabel(es ? "Contraseña" : "Password", { exact: true })).toBeVisible();
}
async function csrf(context: BrowserContext) { return (await (await context.request.get(origin + "/api/auth/csrf")).json()).csrf_token as string; }

test("real anonymous public routes and API project/upload/job refusal; no mail endpoints", async ({ browser }) => {
  const context = await browser.newContext(), page = await context.newPage();
  await context.addInitScript(() => localStorage.setItem("caos.lang", "en"));
  for (const route of ["/", "/introduction", "/methodology", "/implementation", "/experiments", "/benchmark"]) {
    await page.goto(origin + route); await expect(page.locator("main")).toBeVisible();
    await expect(page.getByRole("navigation", { name: "Inverse Earth Studio" }).getByRole("link")).toHaveCount(6);
  }
  const token = await csrf(context), headers = { Origin: origin, "X-CSRF-Token": token };
  const id = randomUUID();
  expect((await context.request.get(origin + "/api/auth/me")).status()).toBe(401);
  expect((await context.request.post(origin + "/api/projects", { headers, data: { name: "Guest forbidden" } })).status()).toBe(401);
  expect((await context.request.post(origin + `/api/projects/${id}/assets`, { headers, data: "private bytes" })).status()).toBe(401);
  expect((await context.request.post(origin + `/api/projects/${id}/jobs`, { headers, data: { method_id: "gravity.station-outlier-flags/v1", dataset_id: randomUUID(), parameters: { threshold: 6 } } })).status()).toBe(401);
  for (const path of ["register", "verify/request-token", "reset-password/forgot-password"]) expect((await context.request.post(origin + `/api/auth/${path}`, { headers, data: {} })).status()).toBe(404);
  await context.close();
});

for (const lang of ["en", "es"] as const) for (const theme of ["light", "dark"] as const) for (const device of ["desktop", "phone"] as const) {
  test(`actual local accounts and plural ownership ${lang} ${theme} ${device}`, async ({ browser }) => {
    const context = await browser.newContext({ viewport: device === "phone" ? { width: 390, height: 844 } : { width: 1440, height: 900 } });
    const es = lang === "es", page = await session(context, lang, theme), prefix = `${lang}-${theme}-${device}`;
    await login(page, { ...accounts[0], password: randomUUID() }, es);
    await expect(page.getByRole("alert")).toContainText(es ? "cuenta no está disponible" : "account is unavailable");
    await expect(page.getByLabel(es ? "Contraseña" : "Password", { exact: true })).toHaveValue("");
    await login(page, accounts[0], es);
    await expect(page.getByRole("dialog")).toContainText(es ? "cuenta local autenticada" : "authenticated local account");
    const actualAccount = await (await context.request.get(origin + "/api/auth/me")).json(); expect(actualAccount.is_verified).toBe(false); expect(actualAccount.is_active).toBe(true);
    const cookie = (await context.cookies()).find(item => item.name === "geophysics_session");
    expect(cookie ? { httpOnly: cookie.httpOnly, sameSite: cookie.sameSite, secure: cookie.secure } : null).toEqual({ httpOnly: true, sameSite: "Strict", secure: false });
    await create(page, prefix + " A one", es); await create(page, prefix + " A two", es);
    const selected = page.getByRole("combobox", { name: es ? "Proyecto seleccionado" : "Selected project", exact: true });
    await expect(selected.locator("option")).toHaveCount(2);
    const aProjects = (await (await context.request.get(origin + "/api/projects")).json()).projects as Array<{ id: string; name: string }>;
    await selected.selectOption(aProjects[0].id); expect(await selected.inputValue()).toBe(aProjects[0].id);
    await page.screenshot({ path: join(evidence, `${prefix}-real-owner.png`) });
    await logout(page, es); expect((await context.request.get(origin + "/api/auth/me")).status()).toBe(401);
    await login(page, accounts[1], es);
    await expect(page.getByRole("button", { name: es ? "Crear proyecto" : "Create project", exact: true })).toBeVisible();
    await expect(selected).toHaveCount(0);
    expect((await context.request.get(origin + `/api/projects/${aProjects[0].id}/assets`)).status()).toBe(404);
    await create(page, prefix + " B only", es);
    await expect(selected.locator("option")).toHaveCount(1);
    const bId = await selected.inputValue();
    await page.getByRole("textbox", { name: es ? /Escriba el nombre exacto para confirmar/ : /Type the exact project name to confirm/ }).fill(prefix + " B only");
    const deletion = page.waitForResponse(response => response.url() === origin + `/api/projects/${bId}` && response.request().method() === "DELETE");
    await page.getByRole("button", { name: es ? "Eliminar proyecto y solicitar recibo" : "Delete project and request receipt", exact: true }).click();
    expect((await (await deletion).json()).external_backup_status).toBe("not_configured");
    await expect(page.getByRole("dialog")).toContainText(es ? "No hay respaldos externos configurados" : "External backups are not configured");
    await logout(page, es); await login(page, accounts[0], es);
    await expect(selected.locator("option")).toHaveCount(2);
    // Exact-ID cleanup of only this test's owned empty projects. Keep the private DB.
    const headers = { Origin: origin, "X-CSRF-Token": await csrf(context) };
    for (const project of aProjects) expect((await context.request.delete(origin + `/api/projects/${project.id}`, { headers })).status()).toBe(200);
    await logout(page, es);
    expect((await context.request.get(origin + "/api/auth/me")).status()).toBe(401);
    // Seven real login/logout attempts above. Keep the backend's ten/600s
    // limiter unchanged; independent per-control DBs prevent matrix cross-talk.
    const authHeaders = { Origin: origin, "X-CSRF-Token": await csrf(context) };
    for (let i = 0; i < 3; i++) expect((await context.request.post(origin + "/api/auth/cookie/login", {
      headers: authHeaders, form: { username: accounts[0].email, password: randomUUID() },
    })).status()).toBe(400);
    const limited = await context.request.post(origin + "/api/auth/cookie/login", {
      headers: authHeaders, form: { username: accounts[0].email, password: randomUUID() },
    });
    expect(limited.status()).toBe(429); expect(Number(limited.headers()["retry-after"])).toBeGreaterThan(0);
    await context.close();
  });
}
