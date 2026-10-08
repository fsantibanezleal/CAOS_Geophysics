/** Explicit external actual installed queue bytes, not native replay or browser QA. */
import { readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { describe,expect,it } from "vitest";
import { readProtectedWaveform,waveformResultBytes } from "../api/waveform-linux-receipt";
import { parseWaveformDataset,verifyWaveformZip,decodeWaveformArray,type WaveformJob } from "../api/waveform-contracts";
import { parseProjectProcessingJob } from "../api/processing-contracts";

const root=process.env.M08_ACTUAL_CAPTURE;
describe.skipIf(!root)("actual installed waveform historical pair and sealed ZIP",()=>{
  it("retains exact authenticated original bytes and verifies every scientific member",async()=>{
    const job=parseProjectProcessingJob(JSON.parse(await readFile(resolve(root!,"job.json"),"utf8")));
    expect(job.method_id).toBe("seismic.waveform-qc-classical/v1");
    const dataset=parseWaveformDataset(JSON.parse(await readFile(resolve(root!,"dataset.json"),"utf8")));
    const raw=new Uint8Array(await readFile(resolve(root!,"result.json")));
    const result=await readProtectedWaveform(raw,job as WaveformJob,dataset);
    expect(result.resources.memory_kind).toBe("linux_cgroup_charge");
    expect(waveformResultBytes(result)).toEqual(raw);
    const zip=new Uint8Array(await readFile(resolve(root!,"../export-nominal1.zip")));
    const files=await verifyWaveformZip(new Blob([zip.buffer]),result);
    expect(Object.keys(files).sort()).toEqual(result.members.map(m=>m.name).sort());
    for(const descriptor of result.calculation.array_descriptors){
      const array=decodeWaveformArray(files[`c0${descriptor.channel_index}-${descriptor.name}.bin`],descriptor);
      expect(array.length).toBe(descriptor.shape.reduce((a,b)=>a*b,1));
    }
    expect(JSON.stringify(result)).not.toContain("linux_execution");
  });
});
