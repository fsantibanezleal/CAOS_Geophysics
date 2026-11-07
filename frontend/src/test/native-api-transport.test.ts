import { describe, expect, it, vi } from "vitest";
import { ApiClient } from "../api/client";

const origin = "https://example.invalid";
function client(body: Uint8Array, headers: Record<string, string> = {}) {
  const transport = vi.fn<typeof fetch>(async () => new Response(new Uint8Array(body).buffer, { headers }));
  return { api: new ApiClient(origin, transport), transport };
}

describe("bounded private native transport", () => {
  it("preserves every byte and exact declared size", async () => {
    const { api, transport } = client(new Uint8Array([0, 255, 13, 10]), { "Content-Length": "4" });
    expect(await api.requestBoundedBytes("/api/projects/example/export", 4)).toEqual(new Uint8Array([0, 255, 13, 10]));
    expect(transport.mock.calls[0][1]).toMatchObject({ credentials: "same-origin", redirect: "error", cache: "no-store" });
  });
  it.each([0, -1, 1.5, 268435457, Infinity])("refuses invalid cap %s before fetch", async cap => {
    const { api, transport } = client(new Uint8Array([1]));
    await expect(api.requestBoundedBytes("/api/projects/example/export", cap)).rejects.toThrow("cap");
    expect(transport).not.toHaveBeenCalled();
  });
  it.each(["5", "bad", "-1"])("refuses declared length %s", async length => {
    const { api } = client(new Uint8Array([1, 2]), { "Content-Length": length });
    await expect(api.requestBoundedBytes("/api/projects/example/export", 4)).rejects.toThrow("declared byte cap");
  });
  it("refuses undeclared streamed overflow", async () => {
    const { api } = client(new Uint8Array([1, 2, 3]));
    await expect(api.requestBoundedBytes("/api/projects/example/export", 2)).rejects.toThrow("byte cap");
  });
  it("refuses declared size drift", async () => {
    const { api } = client(new Uint8Array([1, 2]), { "Content-Length": "3" });
    await expect(api.requestBoundedBytes("/api/projects/example/export", 3)).rejects.toThrow("size drift");
  });
  it("does not fetch after prior cancellation", async () => {
    const { api, transport } = client(new Uint8Array([1]));
    const controller = new AbortController(); controller.abort();
    await expect(api.requestBoundedBytes("/api/projects/example/export", 4, { signal: controller.signal })).rejects.toThrow();
    expect(transport).not.toHaveBeenCalled();
  });
});
