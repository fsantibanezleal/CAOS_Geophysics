import { describe, expect, it, vi } from "vitest";
import { readFileWithBusyRetry } from "../../scripts/vendor/caos-app-shell-gate-0.19.1/gate/serve.mjs";

describe("static gate artifact reads", () => {
  it("retries transient Windows EBUSY reads with bounded backoff", async () => {
    let calls = 0;
    const pause = vi.fn(async () => {});
    const value = await readFileWithBusyRetry("artifact.json", {
      pause,
      read: async () => {
        calls += 1;
        if (calls < 4) throw Object.assign(new Error("sharing violation"), { code: "EBUSY" });
        return Buffer.from("{}");
      },
    });

    expect(value.toString()).toBe("{}");
    expect(calls).toBe(4);
    expect(pause.mock.calls).toEqual([[25], [50], [75]]);
  });

  it("does not retry permanent read errors", async () => {
    const read = vi.fn(async () => { throw Object.assign(new Error("missing"), { code: "ENOENT" }); });
    await expect(readFileWithBusyRetry("missing.json", { read })).rejects.toMatchObject({ code: "ENOENT" });
    expect(read).toHaveBeenCalledTimes(1);
  });

  it("returns the original EBUSY after the retry budget", async () => {
    const error = Object.assign(new Error("still busy"), { code: "EBUSY" });
    const read = vi.fn(async () => { throw error; });
    await expect(readFileWithBusyRetry("locked.json", { read, pause: async () => {} })).rejects.toBe(error);
    expect(read).toHaveBeenCalledTimes(4);
  });
});
