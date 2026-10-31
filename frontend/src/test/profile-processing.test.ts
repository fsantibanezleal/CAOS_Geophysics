import { describe, expect, it } from "vitest";
import { readFileSync } from "node:fs";
import { join } from "node:path";
import { zipSync, unzipSync } from "fflate";
import { readProtectedProfile, verifyProfileBundle } from "../api/profile-processing";
import { parseProjectDatasetReceipt,parseProjectProcessingJob,isProfileReceipt,isProfileJob } from "../api/processing-contracts";

// These opt-in tests consume actual persisted native-worker receipts. No
// fabricated inverse, resampled cell model or replacement provider original.
describe("actual protected native profile browser contracts", () => {
  for (const key of ["GEOPHYSICS_PROFILE_JOB_ERT", "GEOPHYSICS_PROFILE_JOB_TRAVELTIME"]) {
    it.skipIf(!process.env[key])(`binds original worker bytes and every export field: ${key}`,async()=>{
      const root = process.env[key]!, bindings = JSON.parse(readFileSync(join(root,"bindings.json"),"utf8"));
      const receipt = parseProjectDatasetReceipt(bindings.receipt), job = parseProjectProcessingJob(bindings.job);
      if (!isProfileReceipt(receipt) || !isProfileJob(job)) throw new Error("Not a native profile receipt");
      const bytes = new Uint8Array(readFileSync(join(root,"result.json"))), zipBytes = new Uint8Array(readFileSync(join(root,"export.zip")));
      const admitted = await readProtectedProfile(bytes,job,receipt);
      expect(admitted.verdict).toBe("passed");expect(admitted.physicsReplayed).toBe(false);
      expect(admitted.models.length).toBe(key.endsWith("ERT")?1:2);
      expect((await verifyProfileBundle(new Blob([zipBytes]),job,receipt)).result).toEqual(admitted.result);
      await expect(readProtectedProfile(bytes,{...job,request_sha256:"0".repeat(64)},receipt)).rejects.toThrow();
      await expect(readProtectedProfile(bytes,job,{...receipt,raw_sha256:"0".repeat(64)})).rejects.toThrow();
      await expect(readProtectedProfile(bytes,{...job,request:{...job.request,profile_child_sha256:"0".repeat(64)}},receipt)).rejects.toThrow();
      const changed = new Uint8Array(bytes);changed[changed.length-2]^=1;
      await expect(readProtectedProfile(changed,job,receipt)).rejects.toThrow();
      const members = unzipSync(zipBytes), manifest = JSON.parse(new TextDecoder().decode(members["manifest.json"]));
      manifest.units.position="ft";members["manifest.json"]=new TextEncoder().encode(JSON.stringify(manifest));
      await expect(verifyProfileBundle(new Blob([zipSync(members,{level:0})]),job,receipt)).rejects.toThrow();
      members["original.ohm"]=new Uint8Array([1]);
      await expect(verifyProfileBundle(new Blob([zipSync(members,{level:0})]),job,receipt)).rejects.toThrow();
    });
  }
});
