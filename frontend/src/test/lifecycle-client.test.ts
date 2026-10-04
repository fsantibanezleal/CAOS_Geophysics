import { describe, expect, it, vi } from "vitest";
import fixture from "./fixtures/api-owner-raw-v1.json";
import { ApiClient, ApiHttpError } from "../api/client";
import { LifecycleApi } from "../api/lifecycle";
import { parseRawAsset } from "../api/contracts";
import { emptyUploadDraft, prepareUpload } from "../api/upload-metadata";

const project = { id: fixture.project_id, name: "My survey", description: "Raw acquisition", created_at: "2026-09-27T12:00:00Z", updated_at: "2026-09-27T12:00:00Z" };
const account = { id: fixture.owner_id, email: "owner@example.org", is_active: true, is_verified: true, is_superuser: false };
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });

describe("authenticated same-origin lifecycle client", () => {
  it("uses the API's registration, emailed verification and reset routes without storing credentials", async () => {
    const calls: Array<[string, RequestInit]> = [];
    const fetcher = vi.fn(async (url: URL, options: RequestInit) => {
      calls.push([url.pathname, options]);
      if (url.pathname === "/api/auth/config") return json({ mode: "email", registration_enabled: true, mail_flows_enabled: true });
      if (url.pathname === "/api/auth/csrf") return json({ csrf_token: "csrf-1" });
      if (url.pathname === "/api/auth/register") return json({ ...account, is_verified: false }, 201);
      if (url.pathname === "/api/auth/verify/verify") return json(account);
      return new Response(null, { status: 202 });
    }) as unknown as typeof fetch;
    const client = new LifecycleApi(new ApiClient("https://geophysics.example.org", fetcher));
    expect((await client.register(account.email, "long secure password")).is_verified).toBe(false);
    await client.requestVerification(account.email);
    expect((await client.verify("mailed-token")).is_verified).toBe(true);
    await client.forgotPassword(account.email);
    await client.resetPassword("reset-token", "another long secure password");
    expect(calls.filter(([path]) => path !== "/api/auth/csrf" && path !== "/api/auth/config").map(([path]) => path)).toEqual([
      "/api/auth/register", "/api/auth/verify/request-token", "/api/auth/verify/verify",
      "/api/auth/reset-password/forgot-password", "/api/auth/reset-password/reset-password",
    ]);
    for (const [, options] of calls.filter(([path]) => path !== "/api/auth/csrf" && path !== "/api/auth/config")) {
      expect(options.credentials).toBe("same-origin");
      expect(new Headers(options.headers).get("X-CSRF-Token")).toBe("csrf-1");
    }
  });

  it("uses CSRF cookie transport, URL-encoded login and owner-scoped endpoints", async () => {
    const calls: Array<[string, RequestInit]> = [];
    const fetcher = vi.fn(async (url: URL, options: RequestInit) => {
      calls.push([url.pathname, options]);
      if (url.pathname === "/api/auth/config") return json({ mode: "local", registration_enabled: false, mail_flows_enabled: false });
      if (url.pathname === "/api/auth/csrf") return json({ csrf_token: "csrf-1" });
      if (url.pathname === "/api/auth/me") return json(account);
      if (url.pathname === "/api/auth/cookie/login" || url.pathname === "/api/auth/cookie/logout") return new Response(null, { status: 204 });
      if (url.pathname === "/api/projects" && options.method === "POST") return json(project, 201);
      if (url.pathname === "/api/projects") return json({ projects: [project] });
      if (url.pathname.endsWith("/assets") && options.method === "POST") return json(fixture, 201);
      if (url.pathname.endsWith("/assets")) return json({ assets: [fixture] });
      if (url.pathname.endsWith("/download")) return new Response("station,x,y,z,g\nS1,0,0,100,9.81\nS2,10,0,100,9.80\n", { headers: { "Content-Type": "text/csv" } });
      if (url.pathname.endsWith("/export")) return new Response(new Uint8Array([80, 75]), { headers: { "Content-Type": "application/zip" } });
      if (url.pathname.endsWith("/assets/" + fixture.asset_id)) return json(fixture);
      if (options.method === "DELETE") return json({ deleted: true, project_id: project.id, receipt_id: "55555555-5555-4555-8555-555555555555", backup_erasure_status: "not_attempted", external_backup_status: "pending_reconciliation" });
      throw new Error(`unhandled ${url.pathname}`);
    }) as unknown as typeof fetch;
    const client = new LifecycleApi(new ApiClient("https://geophysics.example.org", fetcher));
    expect(await client.probe()).toEqual(account);
    expect(await client.login(account.email, "long secure password")).toEqual(account);
    expect(await client.createProject(project.name, project.description)).toEqual(project);
    expect(await client.projects()).toEqual([project]);
    const draft = { ...emptyUploadDraft(), format: "gravity_csv" as const, mime: "text/csv", provider: "User upload", rightsStatement: "Private storage permission granted.", rightsDecision: "mirror" as const, privateStorageAttested: true, attribution: "Survey", coordinateReference: "epsg" as const, epsg: "32719", axisOrder: "xy" as const, horizontalDatum: "WGS84", verticalDatum: "survey benchmark", verticalPositive: "up" as const, horizontalUnit: "m" as const, verticalUnit: "m" as const, measurementUnit: "mGal", epochUtc: "2026-09-27T12:00:00Z", componentFrame: "local vertical down", geometry: { station_id_column: "station", x_column: "x", y_column: "y", z_column: "z", value_column: "g" } };
    const file = new File(["station,x,y,z,g\nS1,0,0,100,9.81\nS2,10,0,100,9.80\n"], "stations.csv", { type: "text/csv" });
    expect((await client.upload(project.id, file, prepareUpload(file, draft, []))).validation_status).toBe("raw_metadata_checked");
    expect(await client.assets(project.id)).toHaveLength(1);
    expect((await client.receipt(project.id, fixture.asset_id)).source.citation).toBeNull();
    expect((await client.download(project.id, parseRawAsset(fixture))).size).toBe(49);
    expect((await client.exportProject(project.id)).size).toBe(2);
    expect((await client.deleteProject(project.id)).backup_erasure_status).toBe("not_attempted");
    await client.logout();
    const login = calls.find(([path]) => path === "/api/auth/cookie/login")![1];
    expect(login.body).toBeInstanceOf(URLSearchParams);
    expect(String(login.body)).toContain("username=owner%40example.org");
    expect(new Headers(login.headers).get("X-CSRF-Token")).toBe("csrf-1");
    const upload = calls.find(([path, options]) => path.endsWith("/assets") && options.method === "POST")![1];
    expect(upload.body).toBe(file);
    expect(upload.credentials).toBe("same-origin");
    expect(upload.redirect).toBe("error");
    const metadata = JSON.parse(new Headers(upload.headers).get("X-Asset-Metadata")!);
    expect(metadata.source).toMatchObject({ expected_bytes: 49, expected_sha256: fixture.sha256, private_storage_permission: "attested" });
    expect(JSON.stringify(metadata)).not.toContain("storage_key");
  });

  it("preserves API validation fields and refuses a non-owner download path", async () => {
    const errorFetch = vi.fn(async (url: URL) => url.pathname === "/api/auth/csrf" ? json({ csrf_token: "csrf-1" }) : json({ code: "physical_metadata_invalid", message: "Invalid", fields: ["physical.geometry.x_column"] }, 422)) as unknown as typeof fetch;
    const client = new LifecycleApi(new ApiClient("https://geophysics.example.org", errorFetch));
    await expect(client.createProject("Survey", "")).rejects.toMatchObject({ status: 422, code: "physical_metadata_invalid", fields: ["physical.geometry.x_column"] } satisfies Partial<ApiHttpError>);
    await expect(client.download(project.id, { ...fixture, project_id: "other" } as never)).rejects.toThrow("selected project");
  });
});
