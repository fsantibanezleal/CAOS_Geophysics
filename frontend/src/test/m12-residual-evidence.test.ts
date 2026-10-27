import { createHash } from "node:crypto";
import { describe, expect, it } from "vitest";
import { admitM12Evidence } from "../components/M12ResidualEvidence";

const counts = { train: 1200, validation: 160, id_test: 160, family_only: 80, acquisition_only: 80, joint_ood: 160 };
const cohort = (count: number, velocity = 1.04, oracle = 1.39) => ({
  count, learned_velocity_rmse_m_s: 120, classical_velocity_rmse_m_s: 115,
  learned_oracle_rmse_ms: 1.4, classical_oracle_rmse_ms: 1.1,
  learned_to_classical_velocity_ratio: velocity, learned_to_classical_oracle_ratio: oracle,
});
function receipt() {
  return {
    schema: "caos-geophysics.m12-residual/v3.1", protocol: "m12-learned-residual/v3.1", status: "failed-held-out-comparator",
    selected_epoch: 2, epochs_run: 3,
    history: [0.8, 0.4, 0.3, 0.5].map((v, epoch) => ({ epoch, validation_velocity_rmse_m_s: v })),
    counts: { ...counts }, cpu_cuda_parity: { status: "pass", max_abs_m_s: 0.12, p99_abs_m_s: 0.04, mean_abs_m_s: 0.01 },
    cohorts: Object.fromEntries(Object.entries(counts).filter(([name]) => name !== "train").map(([name, n]) => [name, cohort(n)])),
    limitations: ["synthetic generator; not field geological validation"],
  };
}
const bytes = (s: string) => new TextEncoder().encode(s);
const hash = (b: Uint8Array) => createHash("sha256").update(b).digest("hex");
async function bundle(mutator?: (r: ReturnType<typeof receipt>) => void, opts: { badHash?: boolean; badSize?: boolean; badManifest?: boolean } = {}) {
  const r = receipt(), checkpoint = bytes("npz-checkpoint-bytes");
  Object.assign(r, { checkpoint: "m12-residual-v3.1.npz", checkpoint_sha256: hash(checkpoint) });
  mutator?.(r);
  const receiptBytes = bytes(JSON.stringify(r));
  const manifest = {
    schema: opts.badManifest ? "wrong" : "caos-geophysics.local-experiment-manifest/v1",
    protocol: "m12-learned-residual/v3.1",
    files: {
      "receipt.json": { bytes: receiptBytes.length + Number(!!opts.badSize), sha256: hash(receiptBytes) },
      "m12-residual-v3.1.npz": { bytes: checkpoint.length, sha256: opts.badHash ? "0".repeat(64) : hash(checkpoint) },
    },
  };
  return {
    "receipt.json": new File([receiptBytes], "receipt.json", { type: "application/json" }),
    "local-evidence-manifest.json": new File([bytes(JSON.stringify(manifest))], "local-evidence-manifest.json", { type: "application/json" }),
    "m12-residual-v3.1.npz": new File([checkpoint], "m12-residual-v3.1.npz"),
  };
}

describe("M12 residual v3.1 local evidence admission", () => {
  it("admits matching local receipt, manifest and checkpoint and preserves negative scientific status", async () => {
    const result = await admitM12Evidence(await bundle());
    expect(result.receipt.status).toBe("failed-held-out-comparator");
    expect(result.receipt.cohorts.joint_ood).toMatchObject({ count: 160, learned_to_classical_velocity_ratio: 1.04, learned_to_classical_oracle_ratio: 1.39 });
    expect(result.checkpointBytes).toBe(new TextEncoder().encode("npz-checkpoint-bytes").length);
    expect(result.checkpointSha256).toBe(hash(bytes("npz-checkpoint-bytes")));
  });
  it("rejects receipt hash and byte-length mismatches", async () => {
    await expect(admitM12Evidence(await bundle(undefined, { badHash: true }))).rejects.toThrow(/SHA-256/);
    await expect(admitM12Evidence(await bundle(undefined, { badSize: true }))).rejects.toThrow(/byte length/);
  });
  it("rejects malformed manifest, optimistic status, and inconsistent claimed failure", async () => {
    await expect(admitM12Evidence(await bundle(undefined, { badManifest: true }))).rejects.toThrow(/manifest schema/);
    await expect(admitM12Evidence(await bundle(r => { r.status = "supported-within-bounded-synthetic-protocol"; }))).rejects.toThrow(/optimistic or unknown status/);
    await expect(admitM12Evidence(await bundle(r => { r.cohorts.joint_ood.learned_to_classical_velocity_ratio = 0.9; r.cohorts.joint_ood.learned_to_classical_oracle_ratio = 0.8; }))).rejects.toThrow(/inconsistent/);
  });
  it("rejects non-finite metrics, wrong cohort counts, and invalid training history", async () => {
    await expect(admitM12Evidence(await bundle(r => { r.cohorts.joint_ood.learned_to_classical_velocity_ratio = Number.NaN; }))).rejects.toThrow(/non-finite/);
    await expect(admitM12Evidence(await bundle(r => { r.counts.joint_ood = 159; }))).rejects.toThrow(/cohort counts/);
    await expect(admitM12Evidence(await bundle(r => { r.history[1].epoch = 7; r.counts = { ...counts }; }))).rejects.toThrow(/Training history/);
    await expect(admitM12Evidence(await bundle(r => { r.selected_epoch = 1; }))).rejects.toThrow(/minimum recorded/);
  });
  it("fails clearly for missing, mislabeled, or unreadable local files", async () => {
    const files = await bundle();
    const { "receipt.json": _receipt, ...missing } = files;
    await expect(admitM12Evidence(missing)).rejects.toThrow(/Select receipt.json/);
    const wrong = { ...files, "receipt.json": new File(["{}"], "renamed.json") };
    await expect(admitM12Evidence(wrong)).rejects.toThrow(/exact filename/);
    const unreadableFile = files["receipt.json"];
    Object.defineProperty(unreadableFile, "arrayBuffer", { value: () => Promise.reject(new Error("unavailable")) });
    const unreadable = { ...files, "receipt.json": unreadableFile };
    await expect(admitM12Evidence(unreadable)).rejects.toThrow(/unavailable/i);
  });
});
