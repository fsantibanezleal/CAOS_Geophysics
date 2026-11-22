import { describe, expect, it, vi } from "vitest";
import { ApiClient, ApiHttpError } from "../api/client";
import { parseSourceRecord } from "../api/contracts";

const source = {
  schema_version: "geophysics.source-record-view/v1", source_id: "src", version: 1, provider: "USGS", location: { kind: "upload", filename: "source.edi" },
  doi: null, citation: null, retrieved_at: "2026-09-27T00:00:00Z", rights_statement: "Linked only",
  rights_decision: "provider-link-only", private_storage_permission: "attested", declared_format: "edi", expected_bytes: 100,
  sha256: "a".repeat(64), attribution: "USGS",
};
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { "Content-Type": "application/json" } });

describe("same-origin API transport", () => {
  it("retains producer JSON lexical bytes and cancels oversized streams", async () => {
    const raw = '{"value":1.0,"small":1e-09}', signal = new AbortController().signal;
    const fetcher = vi.fn(async () => new Response(raw, {headers:{"content-type":"application/json"}}));
    const client = new ApiClient("https://geophysics.example.org", fetcher);
    expect(new TextDecoder().decode(await client.requestJsonBytes("/api/jobs/result", 100, signal))).toBe(raw);
    expect((fetcher.mock.calls as unknown as [string, RequestInit][])[0][1]).toMatchObject({signal,credentials:"same-origin",redirect:"error",cache:"no-store"});
    const cancel = vi.fn(), stream = new ReadableStream<Uint8Array>({start(controller){controller.enqueue(new Uint8Array(101));},cancel});
    const bounded = new ApiClient("https://geophysics.example.org", async () => new Response(stream,{headers:{"content-type":"application/json"}}));
    await expect(bounded.requestJsonBytes("/api/jobs/result",100)).rejects.toThrow("byte bound"); expect(cancel).toHaveBeenCalledOnce();
    await expect(client.requestJsonBytes("/api/jobs/result",0)).rejects.toThrow("bound");
    await expect(new ApiClient("https://geophysics.example.org",async()=>new Response("{}",{headers:{"content-type":"text/html"}})).requestJsonBytes("/api/jobs/result",100)).rejects.toThrow("non-JSON");
  });
  it("same_origin_transport_and_errors", async () => {
    const transport = vi.fn(async () => json(source)) as unknown as typeof fetch;
    const client = new ApiClient("https://geophysics.example.org", transport);
    const signal = new AbortController().signal;
    expect((await client.requestJson("/api/sources/src", parseSourceRecord, { signal })).source_id).toBe("src");
    const [url, options] = vi.mocked(transport).mock.calls[0];
    expect(String(url)).toBe("https://geophysics.example.org/api/sources/src");
    expect(options).toMatchObject({ credentials: "same-origin", redirect: "error", method: "GET", signal });
    for (const path of ["https://evil.example/api/sources", "//evil.example/api/sources", "/api/../secrets", "/data/v2/catalog.json"])
      await expect(client.requestJson(path, parseSourceRecord)).rejects.toThrow("same-origin /api/");
    expect(vi.mocked(transport)).toHaveBeenCalledTimes(1);
    await client.requestJson("/api/sources", parseSourceRecord, { query: new URLSearchParams({ search: "Clear Lake" }) });
    expect(String(vi.mocked(transport).mock.calls[1][0])).toBe("https://geophysics.example.org/api/sources?search=Clear+Lake");
    const failure = vi.fn(async () => json({ code: "ineligible", message: "Dataset has no MT tensor" }, 422)) as unknown as typeof fetch;
    await expect(new ApiClient("https://geophysics.example.org", failure).requestJson("/api/jobs/1", parseSourceRecord))
      .rejects.toMatchObject({ status: 422, code: "ineligible", message: "Dataset has no MT tensor" } satisfies Partial<ApiHttpError>);
    const html = vi.fn(async () => new Response("<html></html>", { headers: { "Content-Type": "text/html" } })) as unknown as typeof fetch;
    await expect(new ApiClient("https://geophysics.example.org", html).requestJson("/api/sources", parseSourceRecord))
      .rejects.toThrow("non-JSON success");
    const invalid = vi.fn(async () => json({ ...source, sha256: "invalid" })) as unknown as typeof fetch;
    await expect(new ApiClient("https://geophysics.example.org", invalid).requestJson("/api/sources/src", parseSourceRecord))
      .rejects.toThrow("SHA-256");
  });

  it("unsafe_request_requires_csrf", async () => {
    const transport = vi.fn(async () => json(source)) as unknown as typeof fetch;
    const client = new ApiClient("https://geophysics.example.org", transport);
    await expect(client.requestJson("/api/sources", parseSourceRecord, { method: "POST", body: source })).rejects.toThrow("CSRF token required");
    expect(vi.mocked(transport)).not.toHaveBeenCalled();
    await client.requestJson("/api/sources", parseSourceRecord, { method: "POST", body: source, csrfToken: "token-1" });
    const options = vi.mocked(transport).mock.calls[0][1];
    expect(options).toMatchObject({ method: "POST", credentials: "same-origin", body: JSON.stringify(source) });
    expect(new Headers(options?.headers).get("X-CSRF-Token")).toBe("token-1");
  });
});
