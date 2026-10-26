/** Owner/project-bound same-origin calls; no device paths or solver callbacks. */
import { ApiClient } from '../../api/client';
import { object,parseStart,parseJob,parseResult,uuid,hash, type SurveyStart,type SurveyJob,type FileIdentity } from './contract';
import { parseRegistry,registryReader } from './registry';
import {parseAssetHeader,parseAssetReceipt,parseDatasetRequest,parseDatasetReceipt,type AssetHeader,type DatasetRequest} from './intakeContract';

const path = (project: string) => `/api/projects/${uuid(project)}/magnetic-line-surveys/jobs`;
const same = (left: string,right: string) => { if (left !== right) throw new Error('Survey identity mismatch'); };
export class MagneticLineSurveyApi {
  constructor(private readonly transport: ApiClient) {}
  private async csrf(signal?: AbortSignal) {
    const body = await this.transport.requestJson('/api/auth/csrf',object,{signal});
    if (typeof body.csrf_token !== 'string' || !body.csrf_token) throw new Error('CSRF token missing');
    return body.csrf_token;
  }
  private bind(job: SurveyJob,project: string,id?: string) {
    same(job.project_id,project);
    if (id) same(job.job_id,id);
    return job;
  }
  async upload(project:string,file:File,header:AssetHeader) {
    const declared=parseAssetHeader(header);
    if(file.size!==declared.source.expected_bytes||file.name!==declared.filename)throw new Error('Selected original identity mismatch');
    // Shared upload does not promise cancellation. Await actual custody receipt.
    const receipt=await this.transport.requestUpload(`/api/projects/${uuid(project)}/magnetic-line-surveys/assets`,
      file,declared.mime,JSON.stringify(declared),parseAssetReceipt,await this.csrf());
    same(receipt.role,declared.role);same(receipt.sha256,declared.source.expected_sha256);
    if(receipt.bytes!==file.size)throw new Error('Original upload byte mismatch');
    return receipt;
  }
  async createDataset(project:string,request:DatasetRequest,signal?:AbortSignal) {
    return this.transport.requestJson(`/api/projects/${uuid(project)}/magnetic-line-surveys/datasets`,parseDatasetReceipt,
      {method:'POST',csrfToken:await this.csrf(signal),body:parseDatasetRequest(request),signal});
  }
  async start(project: string,request: SurveyStart,signal?: AbortSignal) {
    const body = parseStart(request);
    const job = this.bind(await this.transport.requestJson(path(project),parseJob,
      {method:'POST',csrfToken:await this.csrf(signal),body,signal}),project);
    same(job.dataset_id,body.dataset_id);
    return job;
  }
  async job(project: string,id: string,signal?: AbortSignal) {
    return this.bind(await this.transport.requestJson(`${path(project)}/${uuid(id)}`,parseJob,{signal}),project,id);
  }
  async cancel(project: string,id: string,signal?: AbortSignal) {
    return this.bind(await this.transport.requestJson(`${path(project)}/${uuid(id)}/cancel`,parseJob,
      {method:'POST',csrfToken:await this.csrf(signal),signal}),project,id);
  }
  async result(project: string,job: SurveyJob,signal?: AbortSignal) {
    this.bind(job,project);
    if (job.state !== 'succeeded' || !job.result_sha256) throw new Error('No completed execution result');
    if(!job.result_bytes || job.result_bytes>2097152) throw new Error('Invalid result byte receipt');
    const bytes=await this.reader(project,job)({name:'result.json',bytes:job.result_bytes,sha256:job.result_sha256},signal??new AbortController().signal);
    const result=parseResult(JSON.parse(new TextDecoder('utf-8',{fatal:true}).decode(bytes)));
    same(result.run_id,job.job_id);
    return result;
  }
  reader(project:string,job:SurveyJob) {
    this.bind(job,project);
    return registryReader(job,async(offset,signal)=>this.transport.requestJson(
      `${path(project)}/${uuid(job.job_id)}/members`,parseRegistry,{signal,query:new URLSearchParams({offset:String(offset)})}),
      (entry,signal)=>this.member(project,job,entry.member_id,entry,signal));
  }
  async export(project: string,id: string,scope: 'private'|'public',signal?: AbortSignal) {
    if (scope !== 'private' && scope !== 'public') throw new Error('Invalid export scope');
    // The exact persisted export/download projection is an integration seam;
    // do not cast an arbitrary response as an available scientific replay.
    return this.transport.requestJson(`${path(project)}/${uuid(id)}/export`,object,
      {method:'POST',csrfToken:await this.csrf(signal),body:{schema:'m03-owner-export/1',scope},signal});
  }
  async member(project: string,job: SurveyJob,memberId: string,identity: FileIdentity,signal?: AbortSignal) {
    this.bind(job,project);
    if (job.state !== 'succeeded' || identity.bytes < 1 || identity.bytes > 8388608 || !Number.isSafeInteger(identity.bytes)) throw new Error('Invalid member receipt');
    hash(identity.sha256);
    // memberId comes from the durable owner registry, never a filename guessed
    // as a UUID or an arbitrary URL. The server rechecks all four identities.
    const blob = await this.transport.requestBlob(`${path(project)}/${uuid(job.job_id)}/members/${uuid(memberId)}`,{signal});
    if (blob.size !== identity.bytes) throw new Error('Member byte receipt mismatch');
    const bytes = await blob.arrayBuffer();
    const digest = [...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))].map(v=>v.toString(16).padStart(2,'0')).join('');
    if (digest !== identity.sha256) throw new Error('Member hash receipt mismatch');
    return new Uint8Array(bytes);
  }
}
