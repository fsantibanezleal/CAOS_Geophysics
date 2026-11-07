import { describe, expect, it } from "vitest";
import { ApiClient } from "../api/client";
import { LifecycleApi, accountCanUseServer, parseAuthConfig } from "../api/lifecycle";

const local = { mode: "local", registration_enabled: false, mail_flows_enabled: false };
const email = { mode: "email", registration_enabled: true, mail_flows_enabled: true };
const account = { id: "11111111-1111-4111-8111-111111111111", email: "fixture@example.invalid", is_active: true, is_verified: false, is_superuser: false };
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });
function harness(config: unknown = local, user: unknown = account, status = 200) {
  const calls: Array<[string, RequestInit]> = [];
  const transport = (async (url: URL, options: RequestInit) => {
    calls.push([url.pathname, options]);
    if (url.pathname === "/api/auth/config") return json(config);
    if (url.pathname === "/api/auth/csrf") return json({ csrf_token: "fixture-csrf" });
    if (url.pathname === "/api/auth/me") return json(user, status);
    return new Response(null, { status: 204 });
  }) as unknown as typeof fetch;
  return { api: new LifecycleApi(new ApiClient("https://fixture.example.invalid", transport)), calls };
}

describe("explicit local account access (transport stubs, not live API)", () => {
  it("parses and freezes exactly the three public profile keys", () => {
    expect(parseAuthConfig(local)).toEqual(local);
    expect(Object.isFrozen(parseAuthConfig(local))).toBe(true);
    expect(parseAuthConfig(email)).toEqual(email);
    expect(parseAuthConfig({ ...email, registration_enabled: false })).toEqual({ ...email, registration_enabled: false });
  });
  it.each([null, [], {}, { ...local, mode: "unknown" }, { ...local, registration_enabled: true }, { ...local, mail_flows_enabled: true }, { ...local, mail_flows_enabled: "false" }, { ...local, extra: false }, { mode: "local", registration_enabled: false }, { ...email, mail_flows_enabled: false }])("rejects malformed/contradictory profile %j", value => {
    expect(() => parseAuthConfig(value)).toThrow();
  });
  it("permits an active unverified local account without rewriting flags", async () => {
    const { api, calls } = harness();
    expect(await api.session()).toEqual({ config: local, account });
    expect(await api.probe()).toEqual(account);
    expect(calls.slice(0, 3).map(([path]) => path)).toEqual(["/api/auth/config", "/api/auth/csrf", "/api/auth/me"]);
    expect(account.is_verified).toBe(false);
  });
  it.each([false, true])("requires active state even when verified=%s", verified => {
    expect(accountCanUseServer(parseAuthConfig(local), { ...account, is_active: false, is_verified: verified })).toBe(false);
    expect(accountCanUseServer(parseAuthConfig(email), { ...account, is_verified: verified })).toBe(verified);
  });
  it.each([401, 200])("returns a paired signed-out snapshot for anonymous/inactive response %s", async status => {
    const { api } = harness(local, { ...account, is_active: false }, status);
    expect((await api.session()).account).toBeNull();
  });
  it("propagates service failures rather than treating them as anonymous", async () => {
    await expect(harness(local, {}, 503).api.session()).rejects.toMatchObject({ status: 503 });
    const { api, calls } = harness({ ...local, mode: "bad" });
    await expect(api.probe()).rejects.toThrow();
    expect(calls.map(([path]) => path)).toEqual(["/api/auth/config"]);
  });
  it("freshly checks profile before form login, retains same-origin CSRF and false verification", async () => {
    const { api, calls } = harness();
    expect(await api.login(account.email, "transient fixture value")).toEqual(account);
    expect(calls.map(([path]) => path)).toEqual(["/api/auth/config", "/api/auth/csrf", "/api/auth/cookie/login", "/api/auth/me"]);
    const request = calls[2][1];
    expect(request.body).toBeInstanceOf(URLSearchParams);
    expect(request.credentials).toBe("same-origin");
    expect(new Headers(request.headers).get("X-CSRF-Token")).toBe("fixture-csrf");
  });
  it.each([local, email])("rejects login results unauthorized for profile %j", async config => {
    await expect(harness(config, { ...account, is_active: false }).api.login(account.email, "fixture")).rejects.toMatchObject({ status: 401 });
  });
  it.each(["register", "requestVerification", "verify", "forgotPassword", "resetPassword"] as const)("blocks local %s before CSRF or unsafe request", async method => {
    const { api, calls } = harness();
    const action = method === "register" || method === "resetPassword" ? api[method]("fixture", "fixture") : api[method]("fixture");
    await expect(action).rejects.toThrow("disabled");
    expect(calls.map(([path]) => path)).toEqual(["/api/auth/config"]);
  });
  it("blocks explicitly disabled email registration/mail and keeps logout independent of profile discovery", async () => {
    const { api, calls } = harness({ mode: "email", registration_enabled: false, mail_flows_enabled: false });
    await expect(api.register("fixture", "fixture")).rejects.toThrow("disabled");
    await expect(api.verify("fixture")).rejects.toThrow("disabled");
    await api.logout();
    expect(calls.slice(-2).map(([path]) => path)).toEqual(["/api/auth/csrf", "/api/auth/cookie/logout"]);
  });
  it.each(["not_configured", "pending_reconciliation"] as const)("retains the exact recognized deletion state %s", async state => {
    const deletion = { deleted: true, project_id: account.id, receipt_id: "22222222-2222-4222-8222-222222222222", backup_erasure_status: "not_attempted", external_backup_status: state };
    const transport = (async (url: URL) => json(url.pathname === "/api/auth/csrf" ? { csrf_token: "fixture-csrf" } : deletion)) as unknown as typeof fetch;
    expect(await new LifecycleApi(new ApiClient("https://fixture.example.invalid", transport)).deleteProject(account.id)).toEqual(deletion);
  });
  it.each(["erased", "unknown", null])("rejects unrecognized deletion state %j rather than inventing backup erasure", async state => {
    const transport = (async (url: URL) => json(url.pathname === "/api/auth/csrf" ? { csrf_token: "fixture-csrf" } : { deleted: true, project_id: account.id, receipt_id: "22222222-2222-4222-8222-222222222222", backup_erasure_status: "not_attempted", external_backup_status: state })) as unknown as typeof fetch;
    await expect(new LifecycleApi(new ApiClient("https://fixture.example.invalid", transport)).deleteProject(account.id)).rejects.toThrow("backup state");
  });
});
